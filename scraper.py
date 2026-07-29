import requests
from bs4 import BeautifulSoup
import json
import time
import os

HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

MIN_CENA = 150000
ZAKAZANA_SLOVA = ["havarované", "rozprodám", "náhradní díly"]

def je_to_auto(nazev):
    nazev_malym = nazev.lower()
    for slovo in ZAKAZANA_SLOVA:
        if slovo in nazev_malym:
            return False
    return True

# --- 1. BAZOŠ ---
def stahni_bazos_karoq():
    print("Stahuji Bazoš...")
    auta = []
    for offset in range(0, 200, 20):
        url = "https://auto.bazos.cz/skoda/?hledat=karoq" if offset == 0 else f"https://auto.bazos.cz/skoda/{offset}/?hledat=karoq"
        try:
            odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
            if odpoved.status_code != 200: continue
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            inzeraty = soup.find_all('div', class_='inzeraty')
            for inzerat in inzeraty:
                nadpis = inzerat.find('h2', class_='nadpis').find('a')
                nazev = nadpis.text.strip()
                odkaz = "https://auto.bazos.cz" + nadpis['href']
                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""
                cena_cista = ''.join(filter(str.isdigit, cena))
                if cena_cista and int(cena_cista) < MIN_CENA: continue
                obrazek = inzerat.find('img')['src'] if inzerat.find('img') else "https://via.placeholder.com/150?text=Bez+fotky"
                if "karoq" in nazev.lower() and je_to_auto(nazev):
                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek})
        except Exception: pass
        time.sleep(1)
    return auta

# --- 2. SAUTO ---
def stahni_sauto_karoq():
    print("Stahuji Sauto.cz...")
    auta = []
    api_url = "https://www.sauto.cz/api/v1/items/search"
    for offset in [0, 20, 40]:
        parametry = {"manufacturer_model_seo": "skoda|karoq", "limit": 20, "offset": offset}
        try:
            odpoved = requests.get(api_url, params=parametry, headers=HLAVICKY, timeout=10)
            if odpoved.status_code != 200: continue
            inzeraty = odpoved.json().get('results', [])
            for item in inzeraty:
                try:
                    nazev = item.get('name', 'Škoda Karoq')
                    cena_int = item.get('price', 0)
                    if cena_int < MIN_CENA: continue
                    cena_text = f"{cena_int:,} Kč".replace(',', ' ')
                    
                    item_id = item.get('id', '')
                    seo_name = item.get('seoName', item.get('seo_name', ''))
                    if seo_name and item_id:
                        odkaz = f"https://www.sauto.cz/osobni/detail/skoda/karoq/{seo_name}/{item_id}"
                    else:
                        odkaz = f"https://www.sauto.cz/osobni/detail/{item_id}" if item_id else "https://www.sauto.cz"

                    obrazek = "https://via.placeholder.com/150?text=Sauto"
                    fotky = item.get('images', [])
                    if fotky and len(fotky) > 0:
                        prvni = fotky[0]
                        if isinstance(prvni, dict): obrazek = prvni.get('url', prvni.get('path', obrazek))
                        elif isinstance(prvni, str): obrazek = prvni

                    if je_to_auto(nazev):
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
        except Exception: pass
        time.sleep(1)
    return auta

# --- 3. TIPCARS (Přímé API napojení podle tvého screenshotu) ---
def stahni_tipcars_karoq():
    print("Stahuji Tipcars přes API...")
    auta = []
    # Využijeme typový filtr, který jsi našel v Network panelu (např. typ pro Karoq / osobní vozy)
    api_url = "https://www.tipcars.com/api/search" # nebo obdobný endpoint podle detailu
    
    # Zkusíme dotaz přímo na jejich vyhledávací API s parametry pro Karoq
    parametry = {
        "q": "karoq",
        "limit": 50
    }
    
    tipcars_hlavicky = {
        "accept": "application/json",
        "referrer": "https://www.tipcars.com/skoda-karoq/",
        "User-Agent": HLAVICKY["User-Agent"]
    }
    
    try:
        # Alternativně se můžeme napojit na konkrétní filtr, pokud jej prohlížeč vrací jako JSON
        odpoved = requests.get("https://www.tipcars.com/api/list", params={"type": "34770"}, headers=tipcars_hlavicky, timeout=10)
        if odpoved.status_code != 200:
            # Záložní pokus na hlavní vyhledávání
            odpoved = requests.get("https://www.tipcars.com/api/search", params={"q": "karoq"}, headers=tipcars_hlavicky, timeout=10)
            
        if odpoved.status_code == 200 and "application/json" in odpoved.headers.get("Content-Type", ""):
            data = odpoved.json()
            inzeraty = data.get('items', data.get('results', data.get('cars', [])))
            if isinstance(data, list): inzeraty = data
            
            for item in inzeraty:
                try:
                    nazev = item.get('name', item.get('title', 'Škoda Karoq'))
                    if "karoq" not in nazev.lower(): continue
                    
                    cena_int = item.get('price', item.get('priceVat', 0))
                    if cena_int and int(cena_int) < MIN_CENA: continue
                    cena_text = f"{int(cena_int):,} Kč".replace(',', ' ') if cena_int else "Cena na dotaz"
                    
                    url_auta = item.get('url', item.get('link', ''))
                    odkaz = f"https://www.tipcars.com{url_auta}" if url_auta.startswith('/') else (url_auta if url_auta else "https://www.tipcars.com/skoda-karoq/")
                    
                    obrazek = item.get('image', item.get('photo', 'https://via.placeholder.com/150?text=Tipcars'))
                    
                    if je_to_auto(nazev):
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Tipcars", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
    except Exception as e:
        print(f"Chyba Tipcars API: {e}")
        
    return auta

# --- HLAVNÍ FUNKCE AGREGÁTORU ---
def spust_agregatory():
    print("Začínám masivní agregaci...")
    vsechna_auta = []
    
    auta_bazos = stahni_bazos_karoq()
    print(f"📊 VÝSLEDEK BAZOŠ: {len(auta_bazos)} aut")
    vsechna_auta.extend(auta_bazos)
    
    auta_sauto = stahni_sauto_karoq()
    print(f}📊 VÝSLEDEK SAUTO: {len(auta_sauto)} aut")
    vsechna_auta.extend(auta_sauto)
    
    auta_tipcars = stahni_tipcars_karoq()
    print(f"📊 VÝSLEDEK TIPCARS: {len(auta_tipcars)} aut")
    vsechna_auta.extend(auta_tipcars)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Našli jsme celkem {len(vsechna_auta)} inzerátů z celé ČR.")

if __name__ == "__main__":
    spust_agregatory()
