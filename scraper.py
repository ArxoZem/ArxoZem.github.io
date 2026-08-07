import requests
from bs4 import BeautifulSoup
import json
import time
import re
import random

# ==========================================
# --- ⚙️ KONFIGURACE (KAROQ & ENYAQ) ---
# ==========================================
MIN_CENA_KC = 80000  # Vše pod 80000 Kč letí do koše (odstraní to kola, kabely atd.)

ZAKAZANA_SLOVA_DILY = [
    "alu", "kola", "kolo", "disk", "disky", "pneu", "pneumatiky", "poklice",
    "nárazník", "blatník", "světlo", "světla", "světlomet", "maska", "masky", 
    "zrcátko", "kryt", "kryty", "příčníky", "koberečky", "koberce", "poloosa", 
    "trysky", "klakson", "jednotek", "sada", "dveře", "kapota", "čerpadlo", "převodovka",
    "nabíječka", "kabel", "wallbox"
]

HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def vyhledej_rok(text):
    return re.findall(r'(202[2-6])', text)

def je_to_top_stav_karoq(nazev, cely_text):
    text_malym = cely_text.lower()
    ma_motor = ("1.5" in text_malym or "1,5" in text_malym) and "tsi" in text_malym
    if not ma_motor: return False

    roky = vyhledej_rok(cely_text)
    if not roky: return False

    return True

def vycisti_obrazek(odkaz_na_obrazek):
    if not odkaz_na_obrazek:
        return "https://via.placeholder.com/400x300?text=Bez+fotky+(Bazoš)"
        
    odkaz_malym = odkaz_na_obrazek.lower()
    
    if 'placeholder' in odkaz_malym or 'avatar' in odkaz_malym or 'logo' in odkaz_malym or 'data:image' in odkaz_malym or '1x1' in odkaz_malym or 'icon' in odkaz_malym:
        return "https://via.placeholder.com/400x300?text=Foto+nedostupne+(Bazoš)"
    
    if odkaz_na_obrazek.startswith('//'):
        return "https:" + odkaz_na_obrazek
        
    return odkaz_na_obrazek

# --- BAZOŠ (Karoq & Enyaq s ochranou proti dílům a levnostem) ---
def stahni_bazos_auta():
    print("⏳ Stahuji Bazoš (Karoq & Enyaq)...")
    auta = []
    
    hledane_terminy = ["karoq", "enyaq"]
    
    for termin in hledane_terminy:
        # Vytvoříme si seznam stránek
        stranky = list(range(0, 140, 20))
        # NÁHODNĚ PROHÁZÍME STRÁNKY
        random.shuffle(stranky)
        
        for offset in stranky: 
            url = f"https://auto.bazos.cz/skoda/?hledat={termin}" if offset == 0 else f"https://auto.bazos.cz/skoda/{offset}/?hledat={termin}"
            try:
                odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
                if odpoved.status_code != 200: continue
                soup = BeautifulSoup(odpoved.text, 'html.parser')
                inzeraty = soup.find_all('div', class_='inzeraty')
                
                for inzerat in inzeraty:
                    try:
                        nadpis = inzerat.find('h2', class_='nadpis').find('a')
                        if not nadpis: continue
                        nazev = nadpis.text.strip()
                        nazev_malym = nazev.lower()
                        
                        if termin not in nazev_malym: continue
                        
                        # FILTR 1: Zakázaná slova
                        je_dil = any(dil in nazev_malym for dil in ZAKAZANA_SLOVA_DILY)
                        if je_dil and "tsi" not in nazev_malym and "tdi" not in nazev_malym and "ev" not in nazev_malym: continue

                        # FILTR 2: Cena pod 100 000 Kč
                        cena_blok = inzerat.find('div', class_='inzeratycena')
                        cena_text = cena_blok.text.strip() if cena_blok else ""
                        
                        ciste_cislo = ''.join(filter(str.isdigit, cena_text))
                        if ciste_cislo:
                            cena_int = int(ciste_cislo)
                            # Pokud je v CZK a stojí pod 100 000, nebo v EUR a stojí pod cca 4 000, VYHODIT
                            if "€" not in cena_text and cena_int < MIN_CENA_KC: continue
                            if "€" in cena_text and cena_int < (MIN_CENA_KC / 25): continue

                        odkaz = "https://auto.bazos.cz" + nadpis['href']

                        top_stav = False
                        
                        # ENYAQ vs KAROQ logika
                        if "enyaq" in nazev_malym:
                            # Enyaqy se objeví na hlavní stránce, ale ne v TOP výběru
                            top_stav = False
                        else:
                            # Karoq musíme zkontrolovat
                            try:
                                time.sleep(0.1) 
                                det = requests.get(odkaz, headers=HLAVICKY, timeout=4)
                                det_soup = BeautifulSoup(det.text, 'html.parser')
                                popis = det_soup.find('div', class_='popisdetail')
                                popis_text = popis.text if popis else ""
                                top_stav = je_to_top_stav_karoq(nazev, nazev + " " + popis_text)
                            except: pass

                        img_tag = inzerat.find('img')
                        obrazek_url = img_tag.get('src', img_tag.get('data-src', '')) if img_tag else ""
                        obrazek = vycisti_obrazek(obrazek_url)
                        
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
                    except: continue
            except: pass
            
        print(f"✅ Stažen model {termin.capitalize()} z Bazoše.")
        
    return auta

# --- HLAVNÍ FUNKCE ---
def spust_agregatory():
    print("==================================================")
    print("🚀 SPOUŠTÍM STAHOVÁNÍ KAROQŮ A ENYAQŮ Z BAZOŠE 🚀")
    print("==================================================")
    
    vsechna_auta = stahni_bazos_auta()
    
    # 🎲 EXTRÉMNÍ PROHÁZENÍ - Enyaqy a Karoqy budou dokonale namixované na hlavní obrazovce
    random.shuffle(vsechna_auta)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print("==================================================")
    print(f"🎉 HOTOVO! Celkem uloženo {len(vsechna_auta)} proházených aut do data.json.")
    print("==================================================")

if __name__ == "__main__":
    spust_agregatory()
