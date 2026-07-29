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

MIN_NAJEZD = 0
MAX_NAJEZD = 100000
POVOLENE_ROKY = ["2022", "2023", "2024"]

# 1. KATASTROFY (Vyřadí inzerát, ať je to napsané KDEKOLIV)
ZAKAZANA_SLOVA_KATASTROFA = [
    "havarované", "rozprodám", "náhradní díly", "poškozené", "kroupy", 
    "tdi", "nafta", "diesel"
]

# 2. NÁHRADNÍ DÍLY (Hledáme JEN V NADPISU)
ZAKAZANA_SLOVA_DILY = [
    "nárazník", "blatník", "světlo", "světla", "světlomet", "maska", "masky", 
    "zrcátko", "kryt", "kryty", "příčníky", "koberečky", "koberce", "poloosa", 
    "trysky", "klakson", "jednotek", "motor", "sada", "dveře", "kapota", 
    "čerpadlo", "převodovka"
]

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
    return re.findall(r'(202[2-4])', text)

def hloubkova_kontrola(nazev, cely_text):
    nazev_malym = nazev.lower()
    text_malym = cely_text.lower()
    
    # KONTROLA NADPISU: Musí to být reálně Karoq (žádná Ateca!)
    if "karoq" not in nazev_malym:
        return False, "Není to Karoq (nenalezeno v nadpisu)"
        
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

# --- 1. BAZOŠ ---
def stahni_bazos_karoq():
    print("Stahuji Bazoš...")
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

                if zahozeno_predfiltrem: continue

                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""

                time.sleep(1.0) 
                try:
                    detail_odpoved = requests.get(odkaz, headers=HLAVICKY, timeout=10)
                    detail_soup = BeautifulSoup(detail_odpoved.text, 'html.parser')
                    hlavni_text = detail_soup.find('div', class_='popisdetail')
                    cely_text_inzeratu = hlavni_text.text if hlavni_text else ""
                    
                    komplet_data = nazev + " \n " + cely_text_inzeratu
                    prosel, duvod = hloubkova_kontrola(nazev, komplet_data)
                    
                    if not prosel: 
                        print(f"❌ Bazoš: '{nazev}' -> {duvod}")
                        continue
                        
                except Exception: continue

                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek})
                print(f"✅ BINGO BAZOŠ: {nazev}")
        except Exception: pass
    return auta

# --- 2. SAUTO ---
def stahni_sauto_karoq():
    print("Stahuji Sauto.cz...")
    auta = []
    api_url = "https://www.sauto.cz/api/v1/items/search"
    
    for offset in [0, 20, 40, 60, 80]: 
        parametry = {"manufacturer_model_seo": "skoda|karoq", "limit": 20, "offset": offset}
        try:
            odpoved = requests.get(api_url, params=parametry, headers=HLAVICKY, timeout=10)
            if odpoved.status_code != 200: continue
            inzeraty = odpoved.json().get('results', [])
            
            for item in inzeraty:
                try:
                    nazev = item.get('name', 'Škoda Karoq')
                    cena_int = item.get('price', 0)
                    if cena_int < MIN_CENA or cena_int > MAX_CENA: continue
                    cena_text = f"{cena_int:,} Kč".replace(',', ' ')
                    
                    item_id = item.get('id', '')
                    seo_name = item.get('seoName', item.get('seo_name', ''))
                    
                    # OPRAVA ODKAZU: Pokud chybí seo_name, vytvoříme bezpečnou zkrácenou URL
                    if seo_name and item_id:
                        odkaz = f"https://www.sauto.cz/osobni/detail/skoda/karoq/{seo_name}/{item_id}"
                    else:
                        odkaz = f"https://www.sauto.cz/osobni/detail/skoda/karoq/{item_id}" if item_id else "https://www.sauto.cz"

                    # Převod celé datové sady Sauta na text pro náš přísný filtr
                    item_str = json.dumps(item)
                    
                    prosel, duvod = hloubkova_kontrola(nazev, nazev + " " + item_str)
                    if not prosel:
                        print(f"❌ Sauto: '{nazev}' -> {duvod}")
                        continue

                    # Získání obrázku ze Sauta
                    obrazek = "https://via.placeholder.com/150?text=Sauto"
                    match = re.search(r'(https?://[^\s"\'\\]+sdn\.cz[^\s"\'\\]+)', item_str)
                    if match:
                        obrazek = match.group(1).replace('\\/', '/').replace('{width}', '400').replace('{height}', '300').replace('{ext}', 'jpg')

                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek})
                    print(f"✅ BINGO SAUTO: {nazev}")
                except Exception: continue
        except Exception: pass
        time.sleep(1.0)
    return auta

# --- 3. TIPCARS ---
def stahni_tipcars_karoq():
    print("Stahuji Tipcars...")
    auta = []
    try:
        odpoved = requests.get("https://www.tipcars.com/skoda-karoq/", headers=HLAVICKY, timeout=15)
        soup = BeautifulSoup(odpoved.text, 'html.parser')
        
        odkazy = soup.find_all('a', href=lambda h: h and 'skoda-karoq' in h.lower() and re.search(r'-\d{6,}', h))
        zpracovano = set()
        
        for a in odkazy:
            try:
                href = a.get('href', '')
                odkaz = "https://www.tipcars.com" + href if href.startswith('/') else href
                if odkaz in zpracovano: continue
                zpracovano.add(odkaz)
                
                rodic = a.find_parent(['div', 'article'])
                if not rodic: continue
                
                nazev = a.text.strip()
                if len(nazev) < 5: 
                    nadpis = rodic.find(['h2', 'h3', 'a'])
                    nazev = nadpis.text.strip() if nadpis else "Škoda Karoq"
                    
                text_karty = rodic.text
                
                prosel, duvod = hloubkova_kontrola(nazev, nazev + " " + text_karty)
                if not prosel:
                    print(f"❌ Tipcars: '{nazev}' -> {duvod}")
                    continue
                
                cena_text = ""
                for t in rodic.find_all(string=True):
                    if "Kč" in t:
                        cena_text = t.strip()
                        break
                
                img = rodic.find('img')
                obrazek = "https://via.placeholder.com/150?text=Tipcars"
                if img:
                    for attr in ['data-original', 'data-src', 'data-lazy', 'src']:
                        if img.get(attr) and 'placeholder' not in img.get(attr) and 'blank' not in img.get(attr):
                            obrazek = img.get(attr)
                            break
                    if obrazek.startswith('//'): obrazek = "https:" + obrazek
                    elif obrazek.startswith('/'): obrazek = "https://www.tipcars.com" + obrazek
                    
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Tipcars", "odkaz": odkaz, "obrazek": obrazek})
                print(f"✅ BINGO TIPCARS: {nazev}")
            except Exception: continue
    except Exception as e: print(f"Chyba Tipcars: {e}")
    return auta

# --- HLAVNÍ FUNKCE AGREGÁTORU ---
def spust_agregatory():
    print("Začínám přísnou filtraci (Karoq 1.5 TSI Vysoká výbava, 2022-2024, 25k-60k km)...")
    vsechna_auta = []
    
    vsechna_auta.extend(stahni_bazos_karoq())
    vsechna_auta.extend(stahni_sauto_karoq())
    vsechna_auta.extend(stahni_tipcars_karoq())
    
    print(f"\n📊 FINÁLNÍ VÝSLEDEK: Našli jsme celkem {len(vsechna_auta)} dokonalých aut.")
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    spust_agregatory()
