import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ==========================================
# --- ⚙️ PŘÍSNÝ KONFIGURAČNÍ BLOK ---
# ==========================================
MIN_CENA = 100000 
MAX_CENA = 1500000  

MIN_NAJEZD = 25000
MAX_NAJEZD = 60000
POVOLENE_ROKY = ["2022", "2023", "2024"]

# 1. KATASTROFY (Vyřadí inzerát, ať je to napsané KDEKOLIV - v nadpisu i hluboko v textu)
ZAKAZANA_SLOVA_KATASTROFA = [
    "havarované", "rozprodám", "náhradní díly", "poškozené", "kroupy", 
    "tdi", "nafta", "diesel"
]

# 2. NÁHRADNÍ DÍLY (Hledáme JEN V NADPISU! Odstraněna slova pro kola/pneu)
ZAKAZANA_SLOVA_DILY = [
    "nárazník", "blatník", "světlo", "světla", "světlomet", "maska", "masky", 
    "zrcátko", "kryt", "kryty", "příčníky", "koberečky", "koberce", "poloosa", 
    "trysky", "klakson", "jednotek", "motor", "sada", "dveře", "kapota", 
    "čerpadlo", "převodovka"
]

# Modely s vysokou výbavou
VYSOKA_VYBAVA = ["sportline", "sport line", "sport-line", "style", "exclusive"]
# ==========================================

HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def vyhledej_najezd(text):
    shody = re.findall(r'(\d{1,3}(?:[ \.]\d{3})*|\d{4,6})\s*(?:km|tis)', text, re.IGNORECASE)
    shody_najeto = re.findall(r'najeto\s*[:\.]?\s*(\d{1,3}(?:[ \.]\d{3})*|\d{4,6})', text, re.IGNORECASE)
    
    vsechna_cisla = shody + shody_najeto
    for cislo_str in vsechna_cisla:
        ciste_cislo = ''.join(filter(str.isdigit, cislo_str))
        if ciste_cislo:
            hodnota = int(ciste_cislo)
            if hodnota < 1000 and "tis" in text.lower():
                hodnota *= 1000
            if hodnota > 1000:
                return hodnota
    return 0

def vyhledej_rok(text):
    shody = re.findall(r'(202[2-4])', text)
    return shody

def hloubkova_kontrola(cely_text):
    text_malym = cely_text.lower()
    
    if "karoq" not in text_malym:
        return False, "Není to Karoq"
        
    for slovo in ZAKAZANA_SLOVA_KATASTROFA:
        if slovo in text_malym:
            return False, f"Zakázané slovo v textu: {slovo}"
            
    ma_vybavu = any(vybava in text_malym for vybava in VYSOKA_VYBAVA)
    ma_motor = ("1.5" in text_malym or "1,5" in text_malym) and "tsi" in text_malym
    
    if not ma_vybavu:
        return False, "Chybí vysoká výbava (Sportline, Style...)"
    if not ma_motor:
        return False, "Chybí motor 1.5 TSI"

    najezd = vyhledej_najezd(cely_text)
    if najezd == 0:
        return False, "Nenalezen nájezd v textu"
    if najezd < MIN_NAJEZD or najezd > MAX_NAJEZD:
        return False, f"Nájezd mimo limit ({najezd} km)"

    roky = vyhledej_rok(cely_text)
    if not roky:
        return False, "Nenalezen rok 2022, 2023 nebo 2024"

    return True, "OK"

def stahni_bazos_karoq():
    print("Stahuji Bazoš a analyzuji texty inzerátů...")
    auta = []
    
    for offset in range(0, 300, 20): 
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
                
                nazev_malym = nazev.lower()
                zahozeno_predfiltrem = False
                
                for slovo in ZAKAZANA_SLOVA_KATASTROFA:
                    if slovo in nazev_malym:
                        zahozeno_predfiltrem = True
                        break
                
                if not zahozeno_predfiltrem and "tsi" not in nazev_malym and "1.5" not in nazev_malym and "1,5" not in nazev_malym:
                    for slovo in ZAKAZANA_SLOVA_DILY:
                        if slovo in nazev_malym:
                            zahozeno_predfiltrem = True
                            break

                if zahozeno_predfiltrem:
                    continue

                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""

                time.sleep(1.0) 
                try:
                    detail_odpoved = requests.get(odkaz, headers=HLAVICKY, timeout=10)
                    detail_soup = BeautifulSoup(detail_odpoved.text, 'html.parser')
                    hlavni_text = detail_soup.find('div', class_='popisdetail')
                    cely_text_inzeratu = hlavni_text.text if hlavni_text else ""
                    
                    komplet_data = nazev + " \n " + cely_text_inzeratu
                    
                    prosel, duvod = hloubkova_kontrola(komplet_data)
                    
                    if not prosel: 
                        print(f"❌ Zahozeno: '{nazev}' -> Důvod: {duvod}")
                        continue
                        
                except Exception as e:
                    print(f"Chyba při čtení detailu: {odkaz}")
                    continue

                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek})
                print(f"✅ BINGO! Přidávám perfektní auto: {nazev} ({cena})")
        except Exception: pass
    return auta

def spust_agregatory():
    print("Začínám přísnou filtraci (Bazoš: Karoq 1.5 TSI Vysoká výbava, 2022-2024, 25k-60k km)...")
    vsechna_auta = []
    
    auta_bazos = stahni_bazos_karoq()
    print(f"\n📊 FINÁLNÍ VÝSLEDEK: {len(auta_bazos)} dokonalých aut.")
    vsechna_auta.extend(auta_bazos)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    spust_agregatory()
