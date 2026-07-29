import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re

# --- ZÁKLADNÍ NASTAVENÍ ---
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
                if not nadpis: continue
                nazev = nadpis.text.strip()
                odkaz = "https://auto.bazos.cz" + nadpis['href']
                
                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""
                cena_cista = ''.join(filter(str.isdigit, cena))
                if cena_cista and int(cena_cista) < MIN_CENA: continue
                
                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                if "karoq" in nazev.lower() and je_to_auto(nazev):
                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek})
        except Exception: pass
        time.sleep(1)
    return auta

# --- 2. SAUTO (Opravené obrázky pomocí Regexu) ---
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
                    odkaz = f"https://www.sauto.cz/osobni/detail/skoda/karoq/{seo_name}/{item_id}" if seo_name and item_id else "https://www.sauto.cz"

                    # SUPER-OPRAVA OBRÁZKŮ SAUTA: Převedeme data na text a vylovíme první reálnou URL adresu
                    obrazek = "https://via.placeholder.com/150?text=Sauto"
                    item_str = json.dumps(item)
                    match = re.search(r'(https?://[^\s"\'\\]+sdn\.cz[^\s"\'\\]+)', item_str)
                    if match:
                        obrazek = match.group(1).replace('\\/', '/')
                        # Nahradíme zástupné znaky pro šířku a výšku pevnými čísly, aby se fotka načetla!
                        obrazek = obrazek.replace('{width}', '400').replace('{height}', '300').replace('{ext}', 'jpg')

                    if je_to_auto(nazev):
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
        except Exception: pass
        time.sleep(1)
    return auta

# --- 3. AAA AUTO (Lovec odkazů) ---
def stahni_aaaauto_karoq():
    print("Stahuji AAA Auto...")
    auta = []
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    try:
        url = "https://www.aaaauto.cz/ojete-vozy/skoda/karoq"
        odpoved = requests.get('http://api.scraperapi.com', params={'api_key': api_key, 'url': url, 'render': 'true'}, timeout=60)
        soup = BeautifulSoup(odpoved.text, 'html.parser')
        
        # Ignorujeme strukturu a hledáme rovnou odkazy na detail Karoqa
        odkazy = soup.find_all('a', href=lambda h: h and '/cz/skoda/karoq/' in h.lower())
        zpracovano = set()
        
        for a in odkazy:
            try:
                href = a.get('href', '')
                odkaz = "https://www.aaaauto.cz" + href if href.startswith('/') else href
                if odkaz in zpracovano: continue
                zpracovano.add(odkaz)
                
                # Jdeme nahoru pro kontejner auta
                rodic = a.find_parent('div', class_=lambda x: x and ('car' in x.lower() or 'box' in x.lower() or 'card' in x.lower()))
                if not rodic: continue
                
                nadpis = rodic.find(['h2', 'h3'])
                nazev = nadpis.text.strip() if nadpis else "Škoda Karoq"
                
                cena_text = ""
                for t in rodic.find_all(string=True):
                    if "Kč" in t or "CZK" in t:
                        cena_text = t.strip()
                        break
                cena_cista = ''.join(filter(str.isdigit, cena_text))
                if not cena_cista or int(cena_cista) < MIN_CENA: continue
                
                img = rodic.find('img')
                obrazek = img.get('data-src', img.get('src', 'https://via.placeholder.com/150?text=AAA')) if img else 'https://via.placeholder.com/150?text=AAA'
                
                if je_to_auto(nazev):
                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "AAA Auto", "odkaz": odkaz, "obrazek": obrazek})
            except Exception: continue
    except Exception as e: print(f"Chyba AAA: {e}")
    return auta

# --- 4. TIPCARS (Lovec odkazů) ---
def stahni_tipcars_karoq():
    print("Stahuji Tipcars...")
    auta = []
    try:
        odpoved = requests.get("https://www.tipcars.com/skoda-karoq/", headers=HLAVICKY, timeout=15)
        soup = BeautifulSoup(odpoved.text, 'html.parser')
        
        # Hledáme odkazy, které končí dlouhým číslem (ID inzerátu na Tipcars)
        odkazy = soup.find_all('a', href=lambda h: h and 'skoda-karoq' in h.lower() and re.search(r'-\d{6,}', h))
        zpracovano = set()
        
        for a in odkazy:
            try:
                href = a.get('href', '')
                odkaz = "https://www.tipcars.com" + href if href.startswith('/') else href
                if odkaz in zpracovano: continue
                zpracovano.add(odkaz)
                
                rodic = a.find_parent(['div', 'article'])
                if not rodic: continue
                
                nazev = a.text.strip()
                if len(nazev) < 5: 
                    nadpis = rodic.find(['h2', 'h3', 'a'])
                    nazev = nadpis.text.strip() if nadpis else "Škoda Karoq"
                    
                cena_text = ""
                for t in rodic.find_all(string=True):
                    if "Kč" in t:
                        cena_text = t.strip()
                        break
                cena_cista = ''.join(filter(str.isdigit, cena_text))
                if not cena_cista or int(cena_cista) < MIN_CENA: continue
                
                img = rodic.find('img')
                obrazek = "https://via.placeholder.com/150?text=Tipcars"
                if img:
                    obrazek = img.get('data-src', img.get('src', obrazek))
                    if obrazek.startswith('//'): obrazek = "https:" + obrazek
                    
                if je_to_auto(nazev):
                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Tipcars", "odkaz": odkaz, "obrazek": obrazek})
            except Exception: continue
    except Exception as e: print(f"Chyba Tipcars: {e}")
    return auta

# --- HLAVNÍ FUNKCE AGREGÁTORU ---
def spust_agregatory():
    print("Začínám masivní agregaci...")
    vsechna_auta = []
    
    auta_bazos = stahni_bazos_karoq()
    print(f"📊 VÝSLEDEK BAZOŠ: {len(auta_bazos)} aut")
    vsechna_auta.extend(auta_bazos)
    
    auta_sauto = stahni_sauto_karoq()
    print(f"📊 VÝSLEDEK SAUTO: {len(auta_sauto)} aut")
    vsechna_auta.extend(auta_sauto)
    
    auta_aaa = stahni_aaaauto_karoq()
    print(f"📊 VÝSLEDEK AAA AUTO: {len(auta_aaa)} aut")
    vsechna_auta.extend(auta_aaa)
    
    auta_tipcars = stahni_tipcars_karoq()
    print(f"📊 VÝSLEDEK TIPCARS: {len(auta_tipcars)} aut")
    vsechna_auta.extend(auta_tipcars)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Našli jsme celkem {len(vsechna_auta)} inzerátů z celé ČR.")

if __name__ == "__main__":
    spust_agregatory()
