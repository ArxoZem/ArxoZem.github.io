import requests
from bs4 import BeautifulSoup
import json
import time

HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# ČERNÁ LISTINA: Pokud inzerát obsahuje některé z těchto slov, robot ho přeskočí
ZAKAZANA_SLOVA = [
    "alu kola", "litá kola", "disky", "elektrony", "pneumatiky", "pneu",
    "sada kol", "zimní sada", "letní sada", "plecháče", "poklice",
    "náhradní díly", "rozprodám", "nárazník", "světlo", "střešní nosič",
    "příčníky", "koberce", "havarované"
]

# Funkce, která zkontroluje, jestli je to opravdu auto
def je_to_auto(nazev):
    nazev_malym = nazev.lower()
    for slovo in ZAKAZANA_SLOVA:
        if slovo in nazev_malym:
            return False # Našli jsme zakázané slovo, není to auto
    return True # Nic zakázaného tam není, bereme to!

def stahni_bazos_karoq():
    print("Stahuji Bazoš a filtruji doplňky...")
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
                cena = cena_blok.text.strip() if cena_blok else "Dohodou"
                
                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                # ZDE KONTROLUJEME: Musí to mít v názvu karoq A ZÁROVEŇ to projít naší čistkou
                if "karoq" in nazev.lower() and je_to_auto(nazev):
                    auta.append({
                        "znacka": "Škoda", "model": nazev, "cena": cena, 
                        "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek
                    })
        except Exception:
            pass
            
        time.sleep(1)
        
    return auta

def stahni_aaaauto_karoq():
    print("Stahuji AAA Auto...")
    auta = []
    url = "https://www.aaaauto.cz/skoda/karoq/"
    
    try:
        odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            inzeraty = soup.find_all('div', class_='carCard')
            if not inzeraty:
                inzeraty = soup.find_all('div', class_='car-box')
            
            for inzerat in inzeraty:
                try:
                    nazev_tag = inzerat.find(['h2', 'h3'])
                    nazev = nazev_tag.text.strip() if nazev_tag else "Škoda Karoq"
                    
                    odkaz_tag = inzerat.find('a')
                    odkaz = odkaz_tag['href'] if odkaz_tag else url
                    if not odkaz.startswith('http'):
                        odkaz = "https://www.aaaauto.cz" + odkaz
                        
                    cena_tag = inzerat.find(class_='price')
                    cena = cena_tag.text.strip() if cena_tag else "Cena na webu"
                    
                    obrazek_tag = inzerat.find('img')
                    obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=AAA+Auto"
                    
                    # I AAA Auto pro jistotu proženeme filtrem
                    if je_to_auto(nazev):
                        auta.append({
                            "znacka": "Škoda", "model": nazev, "cena": cena, 
                            "zdroj": "AAA Auto", "odkaz": odkaz, "obrazek": obrazek
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"AAA Auto se nepodařilo načíst: {e}")
        
    return auta

def spust_agregatory():
    print("Začínám sběr čistých dat...")
    vsechna_auta = []
    
    auta_bazos = stahni_bazos_karoq()
    vsechna_auta.extend(auta_bazos)
    
    auta_aaa = stahni_aaaauto_karoq()
    vsechna_auta.extend(auta_aaa)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Našli jsme {len(vsechna_auta)} čistých inzerátů bez zbytečností.")

if __name__ == "__main__":
    spust_agregatory()
