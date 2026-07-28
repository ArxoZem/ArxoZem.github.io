import requests
from bs4 import BeautifulSoup
import json
import time
import os

# --- ZÁKLADNÍ NASTAVENÍ ---
HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

# --- 1. BAZOŠ (Bez ScraperAPI - napřímo) ---
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
                nadpis_blok = inzerat.find('h2', class_='nadpis').find('a')
                nazev = nadpis_blok.text.strip()
                odkaz = "https://auto.bazos.cz" + nadpis_blok['href']
                
                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""
                
                cena_cista = ''.join(filter(str.isdigit, cena))
                if cena_cista and int(cena_cista) < MIN_CENA: continue
                
                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                if "karoq" in nazev.lower() and je_to_auto(nazev):
                    auta.append({
                        "znacka": "Škoda", "model": nazev, "cena": cena, 
                        "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek
                    })
        except Exception:
            pass
        time.sleep(1)
    return auta

# --- 2. SAUTO (Přes ScraperAPI) ---
def stahni_sauto_karoq():
    print("Stahuji Sauto.cz přes maskovanou proxy...")
    auta = []
    cilova_url = "https://www.sauto.cz/osobni/hledani/skoda/karoq"
    
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    parametry = {'api_key': api_key, 'url': cilova_url, 'render': 'true'}
    
    try:
        odpoved = requests.get('http://api.scraperapi.com', params=parametry, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            odkazy = soup.find_all('a', href=lambda href: href and "detail/skoda/karoq" in href.lower())
            
            zpracovano = set()
            for odkaz_tag in odkazy:
                odkaz = odkaz_tag['href']
                if not odkaz.startswith('http'): odkaz = "https://www.sauto.cz" + odkaz
                if odkaz in zpracovano: continue
                zpracovano.add(odkaz)
                
                try:
                    rodic = odkaz_tag.find_parent('div')
                    if not rodic: continue
                    
                    obrazek_tag = rodic.find('img')
                    obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Sauto"
                    nazev = odkaz_tag.text.strip() or "Škoda Karoq"
                    
                    cena_text = ""
                    for text in rodic.find_all(string=True):
                        if "Kč" in text:
                            cena_text = text.strip()
                            break
                            
                    cena_cista = ''.join(filter(str.isdigit, cena_text))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                    
                    if je_to_auto(nazev):
                        auta.append({
                            "znacka": "Škoda", "model": nazev, "cena": cena_text or "Cena na webu", 
                            "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"Sauto se přes proxy nepodařilo načíst: {e}")
    return auta

# --- 3. AUTO ESA (Přes ScraperAPI) ---
def stahni_esa_karoq():
    print("Stahuji Auto ESA přes maskovanou proxy...")
    auta = []
    cilova_url = "https://www.autoesa.cz/skoda/karoq"
    
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    parametry = {'api_key': api_key, 'url': cilova_url, 'render': 'true'}
    
    try:
        odpoved = requests.get('http://api.scraperapi.com', params=parametry, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            odkazy = soup.find_all('a', href=lambda href: href and "/skoda/karoq/" in href.lower())
            
            zpracovano = set()
            for odkaz_tag in odkazy:
                odkaz = odkaz_tag['href']
                if not odkaz.startswith('http'): odkaz = "https://www.autoesa.cz" + odkaz
                if odkaz in zpracovano: continue
                zpracovano.add(odkaz)
                
                try:
                    rodic = odkaz_tag.find_parent('div')
                    if not rodic: continue
                    nazev = odkaz_tag.text.strip() or "Škoda Karoq"
                    
                    obrazek_tag = rodic.find('img')
                    obrazek = "https://via.placeholder.com/150?text=Auto+ESA"
                    if obrazek_tag: obrazek = obrazek_tag.get('data-src') or obrazek_tag.get('src') or obrazek
                    
                    cena_text = ""
                    for text in rodic.find_all(string=True):
                        if "Kč" in text:
                            cena_text = text.strip()
                            break
                            
                    cena_cista = ''.join(filter(str.isdigit, cena_text))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                    
                    if je_to_auto(nazev):
                        auta.append({
                            "znacka": "Škoda", "model": nazev, "cena": cena_text or "Cena na webu", 
                            "zdroj": "Auto ESA", "odkaz": odkaz, "obrazek": obrazek
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"Auto ESA se přes proxy nepodařilo načíst: {e}")
    return auta

# --- 4. AAA AUTO (Přes ScraperAPI) ---
def stahni_aaaauto_karoq():
    print("Stahuji AAA Auto přes maskovanou proxy...")
    auta = []
    cilova_url = "https://www.aaaauto.cz/skoda/karoq/"
    
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key: return auta
    parametry = {'api_key': api_key, 'url': cilova_url, 'render': 'true'}
    
    try:
        odpoved = requests.get('http://api.scraperapi.com', params=parametry, timeout=60)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            inzeraty = soup.find_all('div', class_='carCard')
            if not inzeraty: inzeraty = soup.find_all('div', class_='car-box')
            
            for inzerat in inzeraty:
                try:
                    nazev_tag = inzerat.find(['h2', 'h3'])
                    nazev = nazev_tag.text.strip() if nazev_tag else "Škoda Karoq"
                    
                    odkaz_tag = inzerat.find('a')
                    odkaz = odkaz_tag['href'] if odkaz_tag else cilova_url
                    if not odkaz.startswith('http'): odkaz = "https://www.aaaauto.cz" + odkaz
                        
                    cena_tag = inzerat.find(class_='price')
                    cena = cena_tag.text.strip() if cena_tag else ""
                    
                    cena_cista = ''.join(filter(str.isdigit, cena))
                    if cena_cista and int(cena_cista) < MIN_CENA: continue
                        
                    obrazek_tag = inzerat.find('img')
                    obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=AAA+Auto"
                    
                    if je_to_auto(nazev):
                        auta.append({
                            "znacka": "Škoda", "model": nazev, "cena": cena, 
                            "zdroj": "AAA Auto", "odkaz": odkaz, "obrazek": obrazek
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"AAA Auto se přes proxy nepodařilo načíst: {e}")
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
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Našli jsme celkem {len(vsechna_auta)} inzerátů z celé ČR.")

if __name__ == "__main__":
    spust_agregatory()
