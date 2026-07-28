import requests
from bs4 import BeautifulSoup
import json
import time

# --- HLAVNÍ NASTAVENÍ ---
HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def stahni_bazos_karoq():
    print("Stahuji Bazoš...")
    nalezena_auta = []
    stranky_offset = [0, 20] # Pro ukázku zkráceno na 2 stránky
    
    for offset in stranky_offset:
        if offset == 0:
            url = "https://auto.bazos.cz/skoda/?hledat=karoq"
        else:
            url = f"https://auto.bazos.cz/skoda/{offset}/?hledat=karoq"
            
        odpoved = requests.get(url, headers=HLAVICKY)
        if odpoved.status_code != 200: continue
            
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
                obrazek_url = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150"
                
                if "karoq" in nazev.lower():
                    nalezena_auta.append({
                        "znacka": "Škoda", "model": nazev, "cena": cena,
                        "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek_url
                    })
            except Exception:
                continue
        time.sleep(1)
        
    return nalezena_auta

def stahni_sauto_karoq():
    print("Stahuji Sauto (Příprava)...")
    nalezena_auta = []
    
    # SEM PŘIJDE KÓD PRO SAUTO API
    # Příklad toho, jak by to vypadalo (zatím jen vymyšlené auto):
    nalezena_auta.append({
        "znacka": "Škoda",
        "model": "Škoda Karoq 2.0 TDI (Zkušební Sauto)",
        "cena": "450 000 Kč",
        "zdroj": "Sauto.cz",
        "odkaz": "#",
        "obrazek": "https://via.placeholder.com/150?text=Sauto+Fotka"
    })
    
    return nalezena_auta

# --- HLAVNÍ FUNKCE, KTERÁ TO VŠECHNO SPOJÍ ---
def spust_agregatory():
    vsechna_auta = []
    
    # 1. Spustíme Bazoš a přidáme ho na hromadu
    auta_bazos = stahni_bazos_karoq()
    vsechna_auta.extend(auta_bazos)
    
    # 2. Spustíme Sauto a přidáme ho na hromadu
    auta_sauto = stahni_sauto_karoq()
    vsechna_auta.extend(auta_sauto)
    
    # 3. Všechno společně uložíme pro náš web!
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Celkem staženo {len(vsechna_auta)} inzerátů ze všech zdrojů.")

if __name__ == "__main__":
    spust_agregatory()
