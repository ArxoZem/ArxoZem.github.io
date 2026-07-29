import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ==========================================
# --- ⚙️ KONFIGURAČNÍ BLOK ---
# ==========================================
MIN_CENA = 100000 
MAX_CENA = 1500000  
MIN_NAJEZD = 10000
MAX_NAJEZD = 100000
POVOLENE_ROKY = ["2022", "2023", "2024"]

ZAKAZANA_SLOVA_KATASTROFA = [
    "havarované", "rozprodám", "náhradní díly", "poškozené", "kroupy", 
    "tdi", "nafta", "diesel"
]
ZAKAZANA_SLOVA_DILY = [
    "nárazník", "blatník", "světlo", "světla", "světlomet", "maska", "masky", 
    "zrcátko", "kryt", "kryty", "příčníky", "koberečky", "koberce", "poloosa", 
    "trysky", "klakson", "jednotek", "motor", "sada", "dveře", "kapota", 
    "čerpadlo", "převodovka"
]

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
            if hodnota < 1000 and "tis" in text.lower(): hodnota *= 1000
            if hodnota > 1000: return hodnota
    return 0

def vyhledej_rok(text):
    return re.findall(r'(202[2-4])', text)

def hloubkova_kontrola(nazev, cely_text):
    nazev_malym = nazev.lower()
    text_malym = cely_text.lower()
    
    # TVRDÝ FILTR: "Karoq" musí být přímo v nadpisu, jinak to zablokujeme (konec falešných Octavií)
    if "karoq" not in nazev_malym:
        return False
        
    ma_vybavu = any(vybava in text_malym for vybava in VYSOKA_VYBAVA)
    ma_motor = ("1.5" in text_malym or "1,5" in text_malym) and "tsi" in text_malym
    
    if not ma_vybavu or not ma_motor: return False

    najezd = vyhledej_najezd(cely_text)
    if najezd == 0 or najezd < MIN_NAJEZD or najezd > MAX_NAJEZD: return False

    roky = vyhledej_rok(cely_text)
    if not roky: return False

    return True

# --- 1. BAZOŠ ---
def stahni_bazos_karoq():
    print("Stahuji Bazoš...")
    auta = []
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
                nazev_malym = nazev.lower()
                
                # Pokud to není karoq už v náhledu, zahoď to
                if "karoq" not in nazev_malym: continue
                
                zahozeno_predfiltrem = False
                for slovo in ZAKAZANA_SLOVA_KATASTROFA:
                    if slovo in nazev_malym: zahozeno_predfiltrem = True; break
                
                if not zahozeno_predfiltrem and "tsi" not in nazev_malym and "1.5" not in nazev_malym and "1,5" not in nazev_malym:
                    for slovo in ZAKAZANA_SLOVA_DILY:
                        if slovo in nazev_malym: zahozeno_predfiltrem = True; break

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
                    je_dokonaly = hloubkova_kontrola(nazev, komplet_data)
                except Exception: continue

                obrazek_tag = inzerat.find('img')
                obrazek = obrazek_tag['src'] if obrazek_tag else "https://via.placeholder.com/150?text=Bez+fotky"
                
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": je_dokonaly})
        except Exception: pass
    return auta

# --- 2. SAUTO ---
def stahni_sauto_karoq():
    print("Stahuji Sauto.cz...")
    auta = []
    api_url = "https://www.sauto.cz/api/v1/items/search"
    for offset in [0, 20, 40]: 
        parametry = {"manufacturer_model_seo": "skoda|karoq", "limit": 20, "offset": offset}
        try:
            odpoved = requests.get(api_url, params=parametry, headers=HLAVICKY, timeout=10)
            if odpoved.status_code != 200: continue
            inzeraty = odpoved.json().get('results', [])
            for item in inzeraty:
                try:
                    nazev = item.get('name', 'Škoda Karoq')
                    # Hned vyhodíme Octavie atd.
                    if "karoq" not in nazev.lower(): continue
                    
                    cena_int = item.get('price', 0)
                    if cena_int < MIN_CENA or cena_int > MAX_CENA: continue
                    cena_text = f"{cena_int:,} Kč".replace(',', ' ')
                    
                    item_id = item.get('id', '')
                    seo_name = item.get('seoName', item.get('seo_name', ''))
                    odkaz = f"https://www.sauto.cz/osobni/detail/skoda/karoq/{seo_name}/{item_id}" if seo_name and item_id else f"https://www.sauto.cz/osobni/detail/skoda/karoq/{item_id}"

                    item_str = json.dumps(item)
                    je_dokonaly = hloubkova_kontrola(nazev, nazev + " " + item_str)

                    # OPRAVA FOTEK SAUTO: Přeskakujeme loga autobazarů
                    obrazek = "https://via.placeholder.com/150?text=Sauto"
                    nalezene_url = re.findall(r'https?://[^\s"\'\\]+sdn\.cz[^\s"\'\\]+', item_str)
                    for url_img in nalezene_url:
                        url_img = url_img.replace('\\/', '/')
                        if 'logo' not in url_img.lower() and 'avatar' not in url_img.lower():
                            obrazek = url_img.replace('{width}', '400').replace('{height}', '300').replace('{ext}', 'jpg')
                            break # Vezmeme hned první fotku auta

                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": je_dokonaly})
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
                    
                if "karoq" not in nazev.lower(): continue
                
                text_karty = rodic.text
                je_dokonaly = hloubkova_kontrola(nazev, nazev + " " + text_karty)
                
                cena_text = ""
                for t in rodic.find_all(string=True):
                    if "Kč" in t: cena_text = t.strip(); break
                
                # OPRAVA FOTEK TIPCARS: Hledáme opravdovou fotku, ne ikonky
                obrazek = "https://via.placeholder.com/150?text=Tipcars"
                vsechny_obrazky = rodic.find_all('img')
                for img in vsechny_obrazky:
                    src = img.get('data-original') or img.get('data-src') or img.get('data-lazy') or img.get('src') or ""
                    if src and 'placeholder' not in src.lower() and 'logo' not in src.lower() and 'blank' not in src.lower() and 'icon' not in src.lower():
                        if src.startswith('//'): src = "https:" + src
                        elif src.startswith('/'): src = "https://www.tipcars.com" + src
                        obrazek = src
                        break
                    
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Tipcars", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": je_dokonaly})
            except Exception: continue
    except Exception: pass
    return auta

def spust_agregatory():
    print("Stahuji všechny Karoqy a značkuji ty dokonalé...")
    vsechna_auta = []
    vsechna_auta.extend(stahni_bazos_karoq())
    vsechna_auta.extend(stahni_sauto_karoq())
    vsechna_auta.extend(stahni_tipcars_karoq())
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
    print(f"Hotovo! Stáhnuto {len(vsechna_auta)} aut.")

if __name__ == "__main__":
    spust_agregatory()
