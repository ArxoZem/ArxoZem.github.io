import requests
from bs4 import BeautifulSoup
import json
import time

def stahni_realna_auta():
    print("Startuji bota pro vyhledávání Škoda Karoq...")
    
    hlavicky = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "cs,en-US;q=0.7,en;q=0.3"
    }
    
    nalezena_auta = []
    
    # Projdeme prvních 5 stránek inzerátů (posuny 0, 20, 40, 60, 80)
    stranky_offset = [0, 20, 40, 60, 80] 
    
    for offset in stranky_offset:
        # Přidali jsme parametr ?hledat=karoq přímo do adresy
        if offset == 0:
            url = "https://auto.bazos.cz/skoda/?hledat=karoq"
        else:
            url = f"https://auto.bazos.cz/skoda/{offset}/?hledat=karoq"
            
        print(f"Stahuji inzeráty z Bazoše (offset {offset})...")
        
        odpoved = requests.get(url, headers=hlavicky)
        
        if odpoved.status_code != 200:
            print(f"Chyba u {url}, přeskakuji...")
            continue
            
        soup = BeautifulSoup(odpoved.text, 'html.parser')
        inzeraty = soup.find_all('div', class_='inzeraty')
        
        for inzerat in inzeraty:
            try:
                nadpis_blok = inzerat.find('h2', class_='nadpis').find('a')
                nazev = nadpis_blok.text.strip()
                odkaz = "https://auto.bazos.cz" + nadpis_blok['href']
                
                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else "Dohodou"
                
                obrazek_tag = inzerat.find('img')
                obrazek_url = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                # POJISTKA: Uložíme jen to, co má v názvu "karoq" (ignorujeme vnucené reklamy)
                if "karoq" in nazev.lower():
                    nalezena_auta.append({
                        "znacka": "Škoda",
                        "model": nazev,
                        "cena": cena,
                        "zdroj": "Bazoš.cz",
                        "odkaz": odkaz,
                        "obrazek": obrazek_url
                    })
            except Exception as e:
                continue
                
        # Počkáme 1 sekundu proti blokaci
        time.sleep(1)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(nalezena_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Úspěšně staženo a uloženo {len(nalezena_auta)} inzerátů pro Škoda Karoq.")

if __name__ == "__main__":
    stahni_realna_auta()
