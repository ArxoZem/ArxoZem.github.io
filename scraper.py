import json
import requests
from datetime import datetime
# Pro skutečné scrapování bys zde použil knihovnu BeautifulSoup:
# from bs4 import BeautifulSoup

def stahni_auta():
    print("Spouštím robota...")
    
    # Zde bys normálně poslal požadavek na Bazoš (např. requests.get('https://auto.bazos.cz/'))
    # a pomocí BeautifulSoup z něj vyřezal data. 
    # Kvůli ochranám serverů si pro ukázku vygenerujeme vlastní aktualizovaná data,
    # abychom viděli, že automatizace (Action) funguje.
    
    cas_aktualizace = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    nalezena_auta = [
        {"znacka": "Škoda", "model": "Octavia RS", "cena": "350 000 Kč", "zdroj": "Robot", "odkaz": "#"},
        {"znacka": "BMW", "model": "M3", "cena": "850 000 Kč", "zdroj": f"Aktualizováno: {cas_aktualizace}", "odkaz": "#"}
    ]
    
    # Uložení do souboru data.json
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(nalezena_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Uloženo aut: {len(nalezena_auta)}")

if __name__ == "__main__":
    stahni_auta()
