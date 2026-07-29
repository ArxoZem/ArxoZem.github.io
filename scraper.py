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

# --- 1. BAZOŠ (Funguje skvěle) ---
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

# --- 2. SAUTO (API + Opravené obrázky) ---
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

                    # Oprava obrázků: Sauto je ukládá do _links -> gallery
                    obrazek = "https://via.placeholder.com/150?text=Sauto"
                    if '_links' in item and 'gallery' in item['_links'] and len(item['_links']['gallery']) > 0:
                        obrazek = item['_links']['gallery'][0].get('href', obrazek)
                    elif 'images' in item and len(item['images']) > 0:
                        prvni = item['images'][0]
                        obrazek = prvni.get('url', prvni.get('path', obrazek)) if isinstance(prvni, dict) else prvni

                    if obrazek.startswith('//'):
                        obrazek = 'https:' + obrazek

                    if je_to_auto(nazev):
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
        except Exception: pass
        time.sleep(1)
    return auta

# --- 3. AAA AUTO (Přes ScraperAPI s renderováním) ---
def stahni_aaaauto_karoq():
    print("Stahuji AAA Auto...")
    auta = []
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: 
        print("Chybí SCRAPER_API_KEY!")
        return auta
        
    url = "https://www.aaaauto.cz/ojete-vozy/skoda/karoq"
    try:
        odpoved = requests.get('http://api.scraperapi.com', params={'api_key': api_key, 'url': url, 'render': 'true'}, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            # Hledáme všechny možné verze kontejnerů pro inzeráty v AAA
            inzeraty = soup.select('.carCard, .car-box, .vehicle-card')
            
            for inzerat in inzeraty:
                try:
                    nadpis = inzerat.find(['h2', 'h3'])
                    if not nadpis: continue
                    nazev = nadpis.text.strip()
                    
                    odkaz_tag = inzerat.find('a', href=True)
                    odkaz = "https://www.aaaauto.cz" + odkaz_tag['href'] if odkaz_tag and odkaz_tag['href'].startswith('/') else (odkaz_tag['href'] if odkaz_tag else url)
                    
                    cena_tag = inzerat.select_one('.price, .car-price, strong')
                    cena = cena_tag.text.strip() if cena_tag else ""
                    cena_cista = ''.join(filter(str.isdigit, cena))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                    
                    img_tag = inzerat.find('img')
                    obrazek = "https://via.placeholder.com/150?text=AAA+Auto"
                    if img_tag:
                        obrazek = img_tag.get('src', img_tag.get('data-src', obrazek))
                        
                    if je_to_auto(nazev) and "karoq" in nazev.lower():
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "AAA Auto", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
    except Exception as e:
        print(f"Chyba AAA Auto: {e}")
    return auta

# --- 4. TIPCARS (Napřímo - HTML Scrape) ---
def stahni_tipcars_karoq():
    print("Stahuji Tipcars...")
    auta = []
    url = "https://www.tipcars.com/skoda-karoq/"
    try:
        # Tipcars většinou pustí normální dotaz
        odpoved = requests.get(url, headers=HLAVICKY, timeout=15)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            # Různé varianty CSS tříd Tipcars
            inzeraty = soup.select('div.inzerat, div.card, article.item')
            
            for inzerat in inzeraty:
                try:
                    nadpis = inzerat.select_one('.title, h2, h3, a.inzerat-link')
                    if not nadpis: continue
                    nazev = nadpis.text.strip()
                    
                    odkaz_tag = inzerat.find('a', href=True)
                    odkaz = "https://www.tipcars.com" + odkaz_tag['href'] if odkaz_tag and odkaz_tag['href'].startswith('/') else (odkaz_tag['href'] if odkaz_tag else url)
                    
                    cena_tag = inzerat.select_one('.price, .fs-price, .cena')
                    cena = cena_tag.text.strip() if cena_tag else ""
                    cena_cista = ''.join(filter(str.isdigit, cena))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                    
                    img_tag = inzerat.find('img')
                    obrazek = "https://via.placeholder.com/150?text=Tipcars"
                    if img_tag:
                        obrazek = img_tag.get('data-src', img_tag.get('src', obrazek))
                        if obrazek.startswith('//'): obrazek = 'https:' + obrazek
                        
                    if je_to_auto(nazev) and "karoq" in nazev.lower():
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Tipcars", "odkaz": odkaz, "obrazek": obrazek})
                except Exception: continue
    except Exception as e:
        print(f"Chyba Tipcars: {e}")
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
