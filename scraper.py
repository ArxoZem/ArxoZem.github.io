import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def stahni_realna_auta():
    print("Startuji bota a připojuji se na Bazoš...")
    
    url = "https://auto.bazos.cz/skoda/"
    
    hlavicky = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "cs,en-US;q=0.7,en;q=0.3"
    }
    
    odpoved = requests.get(url, headers=hlavicky)
    
    if odpoved.status_code != 200:
        print(f"Chyba! Bazoš nás odmítl. Kód chyby: {odpoved.status_code}")
        return
        
    print("Stránka stažena, jdu hledat inzeráty...")
    
    soup = BeautifulSoup(odpoved.text, 'html.parser')
    inzeraty = soup.find_all('div', class_='inzeraty')
    
    nalezena_auta = []
    
    for inzerat in inzeraty:
        try:
            # Nadpis a odkaz
            nadpis_blok = inzerat.find('h2', class_='nadpis').find('a')
            nazev = nadpis_blok.text.strip()
            odkaz = "https://auto.bazos.cz" + nadpis_blok['href']
            
            # Cena
            cena_blok = inzerat.find('div', class_='cena')
            cena = cena_blok.text.strip() if cena_blok else "Dohodou"
            
            # NOVÉ: Fotka
            obrazek_tag = inzerat.find('img')
            # Pokud auto nemá fotku, dáme tam zástupný obrázek
            obrazek_url = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
            
            nalezena_auta.append({
                "znacka": "Škoda",
                "model": nazev,
                "cena": cena,
                "zdroj": "Bazoš.cz",
                "odkaz": odkaz,
                "obrazek": obrazek_url # Ukládáme fotku do dat
            })
        except Exception as e:
            continue

    nalezena_auta = nalezena_auta[:20]

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(nalezena_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Uloženo {len(nalezena_auta)} inzerátů i s fotkami.")

if __name__ == "__main__":
    stahni_realna_auta()
