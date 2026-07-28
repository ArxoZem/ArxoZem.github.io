import requests
from bs4 import BeautifulSoup
import json
import time

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

def stahni_sauto_karoq():
    print("Stahuji Sauto.cz...")
    auta = []
    url = "https://www.sauto.cz/osobni/hledani/skoda/karoq"
    
    try:
        odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            # Najdeme všechny odkazy, které vedou na detail Karoqu
            odkazy = soup.find_all('a', href=lambda href: href and "detail/skoda/karoq" in href.lower())
            
            zpracovano = set()
            for odkaz_tag in odkazy:
                odkaz = odkaz_tag['href']
                if not odkaz.startswith('http'):
                    odkaz = "https://www.sauto.cz" + odkaz
                    
                if odkaz in zpracovano: continue # Zamezení duplicit
                zpracovano.add(odkaz)
                
                try:
                    # Zkusíme z okolí odkazu vydolovat zbytek (obrázek, cenu)
                    rodic = odkaz_tag.find_parent('div')
                    if not rodic: continue
                    
                    obrazek_tag = rodic.find('img')
                    obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Sauto"
                    
                    nazev = odkaz_tag.text.strip() or "Škoda Karoq"
                    
                    # Hledáme text, který obsahuje Kč
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
        print("Sauto zablokovalo přístup nebo změnilo kód.")
        
    return auta

def stahni_esa_karoq():
    print("Stahuji Auto ESA...")
    auta = []
    url = "https://www.autoesa.cz/skoda/karoq"
    
    try:
        odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            
            # Auto ESA má inzeráty jako odkazy začínající modelem
            odkazy = soup.find_all('a', href=lambda href: href and "/skoda/karoq/" in href.lower())
            
            zpracovano = set()
            for odkaz_tag in odkazy:
                odkaz = odkaz_tag['href']
                if not odkaz.startswith('http'):
                    odkaz = "https://www.autoesa.cz" + odkaz
                    
                if odkaz in zpracovano: continue
                zpracovano.add(odkaz)
                
                try:
                    rodic = odkaz_tag.find_parent('div')
                    if not rodic: continue
                    
                    nazev = odkaz_tag.text.strip() or "Škoda Karoq"
                    
                    obrazek_tag = rodic.find('img')
                    # ESA často používá data-src pro líné načítání (lazy loading)
                    obrazek = "https://via.placeholder.com/150?text=Auto+ESA"
                    if obrazek_tag:
                        obrazek = obrazek_tag.get('data-src') or obrazek_tag.get('src') or obrazek
                    
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
        print("Auto ESA zablokovalo přístup nebo změnilo kód.")
        
    return auta

def spust_agregatory():
    print("Začínám masivní agregaci (Bazoš, Sauto, Auto ESA)...")
    vsechna_auta = []
    
    auta_bazos = stahni_bazos_karoq()
    vsechna_auta.extend(auta_bazos)
    
    auta_sauto = stahni_sauto_karoq()
    vsechna_auta.extend(auta_sauto)
    
    auta_esa = stahni_esa_karoq()
    vsechna_auta.extend(auta_esa)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Našli jsme celkem {len(vsechna_auta)} inzerátů.")

if __name__ == "__main__":
    spust_agregatory()
