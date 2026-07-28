import requests
from bs4 import BeautifulSoup
import json
import time

# Společné hlavičky pro oklamání ochran
HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def stahni_bazos_karoq():
    print("Stahuji Bazoš (Prohledávám 10 stránek)...")
    auta = []
    
    # Range (0, 200, 20) znamená: 0, 20, 40, 60... až do 180 (10 stránek = cca 200 inzerátů)
    for offset in range(0, 200, 20):
        url = "https://auto.bazos.cz/skoda/?hledat=karoq" if offset == 0 else f"https://auto.bazos.cz/skoda/{offset}/?hledat=karoq"
        print(f" -> Bazoš: Stránka {offset//20 + 1}/10")
        
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
                
                if "karoq" in nazev.lower():
                    auta.append({
                        "znacka": "Škoda", "model": nazev, "cena": cena, 
                        "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek
                    })
        except Exception:
            pass # Pokud jeden inzerát selže, jdeme na další
            
        time.sleep(1) # Počkáme 1s proti blokaci
        
    return auta

def stahni_aaaauto_karoq():
    print("Stahuji AAA Auto...")
    auta = []
    # Odkaz přímo na kategorii Karoqů
    url = "https://www.aaaauto.cz/skoda/karoq/"
    
    try:
        odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
        if odpoved.status_code == 200:
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            
            # AAA Auto často balí inzeráty do těchto tříd
            inzeraty = soup.find_all('div', class_='carCard')
            if not inzeraty: # Fallback, kdyby změnili design
                inzeraty = soup.find_all('div', class_='car-box')
            
            for inzerat in inzeraty:
                try:
                    # Nadpis
                    nazev_tag = inzerat.find(['h2', 'h3'])
                    nazev = nazev_tag.text.strip() if nazev_tag else "Škoda Karoq"
                    
                    # Odkaz
                    odkaz_tag = inzerat.find('a')
                    odkaz = odkaz_tag['href'] if odkaz_tag else url
                    if not odkaz.startswith('http'):
                        odkaz = "https://www.aaaauto.cz" + odkaz
                        
                    # Cena
                    cena_tag = inzerat.find(class_='price')
                    cena = cena_tag.text.strip() if cena_tag else "Cena na webu"
                    
                    # Fotka
                    obrazek_tag = inzerat.find('img')
                    obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=AAA+Auto"
                    
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
    print("Začínám velký sběr dat...")
    vsechna_auta = []
    
    # Spustíme a nabalíme Bazoš
    auta_bazos = stahni_bazos_karoq()
    vsechna_auta.extend(auta_bazos)
    print(f"Z Bazoše získáno: {len(auta_bazos)} aut.")
    
    # Spustíme a nabalíme AAA Auto
    auta_aaa = stahni_aaaauto_karoq()
    vsechna_auta.extend(auta_aaa)
    print(f"Z AAA Auto získáno: {len(auta_aaa)} aut.")
    
    # Vše uložíme do JSONu pro tvou stránku
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Mise splněna! Nalezeno celkem masivních {len(vsechna_auta)} inzerátů.")

if __name__ == "__main__":
    spust_agregatory()
