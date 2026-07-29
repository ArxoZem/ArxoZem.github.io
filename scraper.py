import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ==========================================
# --- ⚙️ PŘÍSNÝ KONFIGURAČNÍ BLOK ---
# ==========================================
# Cenu zatím neomezujeme, protože nás zajímají specifikace
MIN_CENA = 100000 
MAX_CENA = 1500000  

MIN_NAJEZD = 25000
MAX_NAJEZD = 60000
POVOLENE_ROKY = ["2022", "2023", "2024"]

ZAKAZANA_SLOVA = ["havarované", "rozprodám", "náhradní díly", "poškozené", "kroupy", "tdi", "nafta", "diesel"]
POZADOVANA_SLOVA = ["sportline", "sport line", "1.5", "1,5", "tsi"]
# ==========================================

HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def vyhledej_najezd(text):
    # Najde číslo následované 'km' (např. 35 000 km, 40000km, 35.000 km)
    shoda = re.search(r'(\d{1,3}(?:[ \.]\d{3})*|\d{4,6})\s*km', text, re.IGNORECASE)
    if shoda:
        ciste_cislo = ''.join(filter(str.isdigit, shoda.group(1)))
        return int(ciste_cislo) if ciste_cislo else 0
    return 0

def vyhledej_rok(text):
    # Najde roky jako 2022, 2023, 2024 v textu
    shody = re.findall(r'\b(202[2-4])\b', text)
    return shody # Vrátí seznam nalezených let

def hloubkova_kontrola(cely_text):
    text_malym = cely_text.lower()
    
    # 1. Musí to být Karoq
    if "karoq" not in text_malym:
        return False
        
    # 2. Kontrola zakázaných slov (nesmí to být nafta ani bouračka)
    for slovo in ZAKAZANA_SLOVA:
        if slovo in text_malym:
            return False
            
    # 3. Kontrola požadované výbavy a motoru
    # (Musí obsahovat Sportline A ZÁROVEŇ 1.5 A ZÁROVEŇ TSI)
    ma_sportline = "sportline" in text_malym or "sport line" in text_malym
    ma_motor = ("1.5" in text_malym or "1,5" in text_malym) and "tsi" in text_malym
    if not (ma_sportline and ma_motor):
        return False

    # 4. Kontrola nájezdu
    najezd = vyhledej_najezd(cely_text)
    if najezd == 0 or najezd < MIN_NAJEZD or najezd > MAX_NAJEZD:
        return False

    # 5. Kontrola roku výroby
    roky = vyhledej_rok(cely_text)
    if not roky:
        return False # Pokud nenajde rok v rozmezí 2022-2024, vyřadí ho

    return True

# --- 1. BAZOŠ (Hloubkový sken s přísným filtrem) ---
def stahni_bazos_karoq():
    print("Stahuji Bazoš (s hloubkovým čtením a přísným filtrem)...")
    auta = []
    
    # Prohledáme víc stran, protože většina aut filtrem neprojde
    for offset in range(0, 100, 20): 
        url = "https://auto.bazos.cz/skoda/?hledat=karoq" if offset == 0 else f"https://auto.bazos.cz/skoda/{offset}/?hledat=karoq"
        try:
            odpoved = requests.get(url, headers=HLAVICKY, timeout=10)
            if odpoved.status_code != 200: continue
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            inzeraty = soup.find_all('div', class_='inzeraty')
            
            for inzerat in inzeraty:
                nadpis = inzerat.find('h2', class_='nadpis').find('a')
                if not nadpis: continue
                nazev = nadpis.text.strip()
                odkaz = "https://auto.bazos.cz" + nadpis['href']
                
                # Pokud zjevně z nadpisu víme, že je to TDI, přeskočíme ho hned (ušetříme dotaz)
                if "tdi" in nazev.lower(): continue

                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""

                # --- OTEVŘENÍ DETAILU INZERÁTU ---
                time.sleep(1.5) # ZPŮSOBNÉ ČEKÁNÍ - Chrání před banem!
                try:
                    detail_odpoved = requests.get(odkaz, headers=HLAVICKY, timeout=10)
                    detail_soup = BeautifulSoup(detail_odpoved.text, 'html.parser')
                    hlavni_text = detail_soup.find('div', class_='popisdetail')
                    cely_text_inzeratu = hlavni_text.text if hlavni_text else ""
                    
                    # Spojíme název a popis do jednoho textu pro analýzu
                    komplet_data = nazev + " \n " + cely_text_inzeratu
                    
                    # PROHNÁNÍ PŘÍSNÝM FILTREM
                    if not hloubkova_kontrola(komplet_data): 
                        continue # Inzerát neprošel sítem, jdeme na další
                        
                except Exception as e:
                    print(f"Nepodařilo se otevřít detail Bazoše: {odkaz}")
                    continue

                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek})
                print(f"✅ NALEZEN SHODNÝ VŮZ: {nazev} ({cena})")
        except Exception: pass
    return auta

# --- HLAVNÍ FUNKCE AGREGÁTORU ---
def spust_agregatory():
    print("Začínám přísnou filtraci (pouze Bazoš, Karoq 1.5 TSI Sportline, 2022-2024, 25k-60k km)...")
    vsechna_auta = []
    
    auta_bazos = stahni_bazos_karoq()
    print(f"📊 VÝSLEDEK BAZOŠ: {len(auta_bazos)} ideálních aut")
    vsechna_auta.extend(auta_bazos)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Našli jsme celkem {len(vsechna_auta)} inzerátů, které 100% splňují požadavky.")

if __name__ == "__main__":
    spust_agregatory()
