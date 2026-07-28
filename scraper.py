import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def stahni_realna_auta():
    print("Startuji bota a připojuji se na Bazoš...")
    
    # URL, kterou chceme prohledávat (můžeš změnit na jakoukoliv sekci na Bazoši)
    url = "https://auto.bazos.cz/skoda/"
    
    # Maskování - bez tohoto nás Bazoš okamžitě zablokuje
    hlavicky = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "cs,en-US;q=0.7,en;q=0.3"
    }
    
    # 1. Stažení stránky
    odpoved = requests.get(url, headers=hlavicky)
    
    if odpoved.status_code != 200:
        print(f"Chyba! Bazoš nás odmítl. Kód chyby: {odpoved.status_code}")
        return
        
    print("Stránka stažena, jdu hledat inzeráty...")
    
    # 2. Zpracování HTML
    soup = BeautifulSoup(odpoved.text, 'html.parser')
    
    # Bazoš balí každý inzerát do <div> s třídou "inzeraty"
    inzeraty = soup.find_all('div', class_='inzeraty')
    
    nalezena_auta = []
    
    for inzerat in inzeraty:
        try:
            # Hledání nadpisu a odkazu
            nadpis_blok = inzerat.find('h2', class_='nadpis').find('a')
            nazev = nadpis_blok.text.strip()
            # Bazoš má odkazy relativní (např. /inzerat/123), musíme přidat doménu
            odkaz = "https://auto.bazos.cz" + nadpis_blok['href']
            
            # Hledání ceny
            cena_blok = inzerat.find('div', class_='cena')
            cena = cena_blok.text.strip() if cena_blok else "Dohodou"
            
            # Vložení do seznamu
            nalezena_auta.append({
                "znacka": "Škoda", # Zde zatím dáváme natvrdo Škoda, protože jsme v té sekci
                "model": nazev,
                "cena": cena,
                "zdroj": "Bazoš.cz",
                "odkaz": odkaz
            })
        except Exception as e:
            # Pokud se něco u konkrétního inzerátu pokazí (např. chybí cena), ignorujeme ho
            continue

    # Vezmeme jen prvních 20 inzerátů, ať web není přehlcený
    nalezena_auta = nalezena_auta[:20]

    # 3. Uložení výsledku
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(nalezena_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Mise splněna! Úspěšně staženo a uloženo {len(nalezena_auta)} reálných inzerátů.")

if __name__ == "__main__":
    stahni_realna_auta()
