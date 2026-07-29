import requests
from bs4 import BeautifulSoup
import json
import time
import os

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

# --- 3. AUTO ESA ---
def stahni_esa_karoq():
    print("Stahuji Auto ESA...")
    auta = []
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    try:
        odpoved = requests.get('http://api.scraperapi.com', params={'api_key': api_key, 'url': "https://www.autoesa.cz/skoda/karoq", 'render': 'true'}, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            # Hledáme bloky inzerátů nebo odkazy obsahující karoq
            karty = soup.find_all(['div', 'article'], class_=lambda x: x and ('car' in x.lower() or 'item' in x.lower() or 'box' in x.lower()))
            if not karty:
                karty = soup.find_all('a', href=lambda href: href and "/skoda/karoq/" in href.lower())
            
            for karta in karty:
                try:
                    if karta.name == 'a':
                        odkaz_tag = karta
                        rodic = karta.find_parent('div') or karta
                    else:
                        odkaz_tag = karta.find('a', href=lambda href: href and "karoq" in href.lower())
                        rodic = karta
                        
                    if not odkaz_tag: continue
                    odkaz = odkaz_tag.get('href', '')
                    if not odkaz.startswith('http'): odkaz = "https://www.autoesa.cz" + odkaz
                    
                    nadpis_tag = rodic.find(['h2', 'h3', 'span'])
                    nazev = nadpis_tag.text.strip() if nadpis_tag else "Škoda Karoq"
                    
                    cena_text = next((t.strip() for t in rodic.find_all(string=True) if "Kč" in t), "Cena na dotaz")
                    cena_cista = ''.join(filter(str.isdigit, cena_text))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                    
                    img_tag = rodic.find('img')
                    obrazek = "https://via.placeholder.com/150?text=Auto+ESA"
                    if img_tag:
                        obrazek = img_tag.get('data-src') or img_tag.get('src') or obrazek

                    if je_to_auto(nazev):
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Auto ESA", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
    except Exception as e: print(f"Chyba ESA: {e}")
    return auta

# --- 4. AAA AUTO ---
def stahni_aaaauto_karoq():
    print("Stahuji AAA Auto...")
    auta = []
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    try:
        odpoved = requests.get('http://api.scraperapi.com', params={'api_key': api_key, 'url': "https://www.aaaauto.cz/skoda/karoq/", 'render': 'true'}, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            inzeraty = soup.find_all('div', class_=lambda x: x and ('car' in x.lower() or 'card' in x.lower() or 'box' in x.lower()))
            for inzerat in inzeraty:
                try:
                    nadpis_tag = inzerat.find(['h2', 'h3', 'a'])
                    if not nadpis_tag: continue
                    nazev = nadpis_tag.text.strip() if nadpis_tag.text.strip() else "Škoda Karoq"
                    
                    odkaz_tag = inzerat.find('a')
                    odkaz = odkaz_tag['href'] if odkaz_tag else "https://www.aaaauto.cz/skoda/karoq/"
                    if not odkaz.startswith('http'): odkaz = "https://www.aaaauto.cz" + odkaz
                    
                    cena_tag = inzerat.find(class_=lambda x: x and 'price' in x.lower())
                    cena_text = cena_tag.text.strip() if cena_tag else "Cena na dotaz"
                    cena_cista = ''.join(filter(str.isdigit, cena_text))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                    
                    img_tag = inzerat.find('img')
                    obrazek = img_tag.get('src') if img_tag else "https://via.placeholder.com/150?text=AAA+Auto"

                    if je_to_auto(nazev):
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "AAA Auto", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
    except Exception as e: print(f"Chyba AAA: {e}")
    return auta

# --- 5. TIPCARS ---
def stahni_tipcars_karoq():
    print("Stahuji Tipcars...")
    auta = []
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    try:
        odpoved = requests.get('http://api.scraperapi.com', params={'api_key': api_key, 'url': "https://www.tipcars.com/skoda-karoq/", 'render': 'true'}, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            inzeraty = soup.find_all(['article', 'div'], class_=lambda x: x and ('item' in x.lower() or 'car' in x.lower() or 'box' in x.lower()))
            if not inzeraty:
                inzeraty = soup.find_all('a', href=lambda href: href and "-".isdigit() and "karoq" in href.lower())

            for inzerat in inzeraty:
                try:
                    if inzerat.name == 'a':
                        odkaz_tag = inzerat
                        rodic = inzerat.parent
                    else:
                        odkaz_tag = inzerat.find('a', href=True)
                        rodic = inzerat

                    if not odkaz_tag: continue
                    odkaz = odkaz_tag.get('href', '')
                    if not odkaz.startswith('http'): odkaz = "https://www.tipcars.com" + odkaz

                    nadpis_tag = rodic.find(['h2', 'h3', 'a'])
                    nazev = nadpis_tag.text.strip() if nadpis_tag else "Škoda Karoq"

                    cena_text = next((t.strip() for t in rodic.find_all(string=True) if "Kč" in t), "Cena na dotaz")
                    cena_cista = ''.join(filter(str.isdigit, cena_text))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue

                    img_tag = rodic.find('img')
                    obrazek = "https://via.placeholder.com/150?text=Tipcars"
                    if img_tag:
                        obrazek = img_tag.get('data-src') or img_tag.get('src') or obrazek

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
    
    auta_esa = stahni_esa_karoq()
    print(f"📊 VÝSLEDEK AUTO ESA: {len(auta_esa)} aut")
    vsechna_auta.extend(auta_esa)
    
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
