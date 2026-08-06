import requests
from bs4 import BeautifulSoup
import json
import time
import re
import random

# ==========================================
# --- ⚙️ KONFIGURACE (KAROQ & ENYAQ) ---
# ==========================================
MIN_CENA = 100000 
MAX_CENA = 3000000  

# Masivní filtr pro vyřazení dílů a příslušenství u obou modelů
ZAKAZANA_SLOVA_DILY = [
    "alu", "kola", "kolo", "disk", "disky", "pneu", "pneumatiky", "poklice",
    "nárazník", "blatník", "světlo", "světla", "světlomet", "maska", "masky", 
    "zrcátko", "kryt", "kryty", "příčníky", "koberečky", "koberce", "poloosa", 
    "trysky", "klakson", "jednotek", "sada", "dveře", "kapota", "čerpadlo", "převodovka"
]

HLAVICKY = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def vyhledej_rok(text):
    return re.findall(r'(202[2-4])', text)

def je_to_top_stav_karoq(nazev, cely_text):
    text_malym = cely_text.lower()
    ma_motor = ("1.5" in text_malym or "1,5" in text_malym) and "tsi" in text_malym
    if not ma_motor: return False

    roky = vyhledej_rok(cely_text)
    if not roky: return False

    return True

def vycisti_obrazek(odkaz_na_obrazek, zdroj):
    if not odkaz_na_obrazek:
        return f"https://via.placeholder.com/400x300?text=Bez+fotky+({zdroj})"
        
    odkaz_malym = odkaz_na_obrazek.lower()
    
    if 'placeholder' in odkaz_malym or 'avatar' in odkaz_malym or 'logo' in odkaz_malym or 'data:image' in odkaz_malym or '1x1' in odkaz_malym or 'icon' in odkaz_malym:
        return f"https://via.placeholder.com/400x300?text=Foto+nedostupne+({zdroj})"
    
    if odkaz_na_obrazek.startswith('//'):
        return "https:" + odkaz_na_obrazek
    if odkaz_na_obrazek.startswith('/'):
        if zdroj == "Tipcars": return "https://www.tipcars.com" + odkaz_na_obrazek
        if zdroj == "Sauto": return "https://www.sauto.cz" + odkaz_na_obrazek
        
    return odkaz_na_obrazek

# --- 1. BAZOŠ (Karoq & Enyaq s ochranou proti dílům) ---
def stahni_bazos_auta():
    print("⏳ Stahuji Bazoš (Karoq & Enyaq)...")
    auta = []
    
    hledane_terminy = ["karoq", "enyaq"]
    
    for termin in hledane_terminy:
        stranky = list(range(0, 100, 20))
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
                        
                        # Kontrola zakázaných dílů v nadpisu (vyhodí kola, nárazníky atd.)
                        je_dil = any(dil in nazev_malym for dil in ZAKAZANA_SLOVA_DILY)
                        if je_dil and "tsi" not in nazev_malym and "tdi" not in nazev_malym and "ev" not in nazev_malym: continue

                        odkaz = "https://auto.bazos.cz" + nadpis['href']
                        cena_blok = inzerat.find('div', class_='inzeratycena')
                        cena = cena_blok.text.strip() if cena_blok else ""

                        top_stav = False
                        try:
                            time.sleep(0.2) 
                            det = requests.get(odkaz, headers=HLAVICKY, timeout=4)
                            det_soup = BeautifulSoup(det.text, 'html.parser')
                            popis = det_soup.find('div', class_='popisdetail')
                            popis_text = popis.text if popis else ""
                            
                            if "karoq" in nazev_malym:
                                top_stav = je_to_top_stav_karoq(nazev, nazev + " " + popis_text)
                        except: pass

                        img_tag = inzerat.find('img')
                        obrazek_url = img_tag.get('src', img_tag.get('data-src', '')) if img_tag else ""
                        obrazek = vycisti_obrazek(obrazek_url, "Bazoš")
                        
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
                    except: continue
            except: pass
            
    random.shuffle(auta)
    print(f"✅ Bazoš úspěšně stažen a promíchán. Nalezeno inzerátů: {len(auta)}")
    return auta

# --- 2. SAUTO (Karoq & Enyaq) ---
def stahni_sauto_auta():
    print("⏳ Stahuji Sauto.cz (Karoq & Enyaq)...")
    auta = []
    
    urls = [
        "https://www.sauto.cz/osobni/hledani?q=skoda-karoq",
        "https://www.sauto.cz/osobni/hledani?q=skoda-enyaq"
    ]
    
    for url in urls:
        try:
            odpoved = requests.get(url, headers=HLAVICKY, timeout=15)
            if odpoved.status_code == 200:
                soup = BeautifulSoup(odpoved.text, 'html.parser')
                inzeraty = soup.select('div[class*="item"], article, div[class*="c-item"]')
                
                zpracovane_odkazy = set()
                for inzerat in inzeraty:
                    try:
                        odkaz_tag = inzerat.find('a', href=lambda h: h and '/osobni/detail/' in h)
                        if not odkaz_tag: continue
                        
                        odkaz = odkaz_tag['href']
                        if not odkaz.startswith('http'): odkaz = "https://www.sauto.cz" + odkaz
                        if odkaz in zpracovane_odkazy: continue
                        zpracovane_odkazy.add(odkaz)
                        
                        nadpis_tag = inzerat.find(['h2', 'h3', 'span'], class_=lambda c: c and 'title' in c.lower())
                        nazev = nadpis_tag.text.strip() if nadpis_tag else odkaz_tag.text.strip()
                        nazev_malym = nazev.lower()
                        
                        if not nazev or ("karoq" not in nazev_malym and "enyaq" not in nazev_malym): continue
                        
                        cena_tag = inzerat.find(string=re.compile(r'Kč'))
                        cena_text = cena_tag.strip() if cena_tag else "Cena na dotaz"
                        
                        top_stav = False
                        if "karoq" in nazev_malym:
                            top_stav = je_to_top_stav_karoq(nazev, nazev + " " + inzerat.text)
                        
                        img = inzerat.find('img')
                        obrazek_url = ""
                        if img:
                            obrazek_url = img.get('src') or img.get('data-src') or img.get('data-lazy') or ""
                        
                        obrazek = vycisti_obrazek(obrazek_url, "Sauto")
                        auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
                    except: continue
        except Exception as e:
            print(f"Chyba Sauto: {e}")
        
    print(f"✅ Sauto úspěšně staženo. Nalezeno inzerátů: {len(auta)}")
    return auta

# --- 3. TIPCARS (Karoq & Enyaq) ---
def stahni_tipcars_auta():
    print("⏳ Stahuji Tipcars (Karoq & Enyaq)...")
    auta = []
    
    url_list = ["https://www.tipcars.com/skoda-karoq/", "https://www.tipcars.com/skoda-enyaq/"]
    
    for url in url_list:
        try:
            odpoved = requests.get(url, headers=HLAVICKY, timeout=15)
            soup = BeautifulSoup(odpoved.text, 'html.parser')
            odkazy = soup.find_all('a', href=lambda h: h and ('skoda-karoq' in h.lower() or 'skoda-enyaq' in h.lower()) and re.search(r'-\d{6,}', h))
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
                        nazev = nadpis.text.strip() if nadpis else "Škoda Auto"
                        
                    nazev_malym = nazev.lower()
                    if "karoq" not in nazev_malym and "enyaq" not in nazev_malym: continue
                    
                    top_stav = False
                    if "karoq" in nazev_malym:
                        top_stav = je_to_top_stav_karoq(nazev, nazev + " " + rodic.text)
                    
                    cena_text = ""
                    for t in rodic.find_all(string=True):
                        if "Kč" in t: cena_text = t.strip(); break
                    
                    obrazek_url = ""
                    vsechny_obr = rodic.find_all('img')
                    for img in vsechny_obr:
                        src = img.get('data-original') or img.get('data-src') or img.get('src') or ""
                        if src and not src.endswith('.svg') and 'icon' not in src.lower() and 'logo' not in src.lower() and 'lazy' not in src.lower():
                            obrazek_url = src
                            break

                    obrazek = vycisti_obrazek(obrazek_url, "Tipcars")
                    auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Tipcars", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
                except: continue
        except: pass
    
    print(f"✅ Tipcars úspěšně stažen. Nalezeno inzerátů: {len(auta)}")
    return auta

# --- HLAVNÍ FUNKCE ---
def spust_agregatory():
    print("==================================================")
    print("🚀 SPOUŠTÍM STAHOVÁNÍ KAROQŮ A ENYAQŮ 🚀")
    print("==================================================")
    
    vsechna_auta = []
    
    vsechna_auta.extend(stahni_bazos_auta())
    vsechna_auta.extend(stahni_sauto_auta())
    vsechna_auta.extend(stahni_tipcars_auta())
    
    # 🎲 Náhodné proházení všech aut dohromady
    random.shuffle(vsechna_auta)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print("==================================================")
    print(f"🎉 HOTOVO! Celkem uloženo {len(vsechna_auta)} aut do data.json.")
    print("==================================================")

if __name__ == "__main__":
    spust_agregatory()
