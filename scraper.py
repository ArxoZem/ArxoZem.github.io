import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
import random

# ==========================================
# --- ⚙️ KONFIGURACE (VŠECHNY KAROQY) ---
# ==========================================
MIN_CENA = 100000 
MAX_CENA = 2000000  

ZAKAZANA_SLOVA_DILY = [
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

def je_to_top_stav(nazev, cely_text):
    text_malym = cely_text.lower()
    ma_motor = ("1.5" in text_malym or "1,5" in text_malym) and "tsi" in text_malym
    if not ma_motor: return False

    roky = vyhledej_rok(cely_text)
    if not roky: return False

    return True

def vycisti_obrazek(odkaz_na_obrazek, zdroj):
    """Tvrdý filtr pro záchranu funkčních obrázků"""
    if not odkaz_na_obrazek:
        return f"https://via.placeholder.com/400x300?text=Bez+fotky+({zdroj})"
        
    odkaz_malym = odkaz_na_obrazek.lower()
    
    # Vyřadíme všechny nesmysly, co weby podstrkávají místo skutečných fotek
    if 'placeholder' in odkaz_malym or 'avatar' in odkaz_malym or 'logo' in odkaz_malym or 'data:image' in odkaz_malym or '1x1' in odkaz_malym or 'icon' in odkaz_malym:
        return f"https://via.placeholder.com/400x300?text=Zablokovany+Obrazek+({zdroj})"
    
    # Oprava URL formátu
    if odkaz_na_obrazek.startswith('//'):
        return "https:" + odkaz_na_obrazek
    if odkaz_na_obrazek.startswith('/') and zdroj == "Tipcars":
        return "https://www.tipcars.com" + odkaz_na_obrazek
        
    return odkaz_na_obrazek

# --- 1. BAZOŠ ---
def stahni_bazos_karoq():
    print("⏳ Stahuji Bazoš (všechny Karoqy)...")
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
                nazev_malym = nazev.lower()
                
                if "karoq" not in nazev_malym: continue
                je_dil = any(dil in nazev_malym for dil in ZAKAZANA_SLOVA_DILY)
                if je_dil and "tsi" not in nazev_malym and "tdi" not in nazev_malym: continue

                odkaz = "https://auto.bazos.cz" + nadpis['href']
                cena_blok = inzerat.find('div', class_='inzeratycena')
                cena = cena_blok.text.strip() if cena_blok else ""

                top_stav = False
                try:
                    time.sleep(0.3) 
                    det = requests.get(odkaz, headers=HLAVICKY, timeout=5)
                    det_soup = BeautifulSoup(det.text, 'html.parser')
                    popis = det_soup.find('div', class_='popisdetail')
                    if popis:
                        top_stav = je_to_top_stav(nazev, nazev + " " + popis.text)
                except: pass

                # Spolehlivější načtení obrázku u Bazoše
                img_tag = inzerat.find('img')
                obrazek_url = img_tag.get('src', img_tag.get('data-src', '')) if img_tag else ""
                obrazek = vycisti_obrazek(obrazek_url, "Bazoš")
                
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena, "zdroj": "Bazoš.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
        except: pass
    
    print(f"✅ Bazoš úspěšně stažen. Nalezeno inzerátů: {len(auta)}")
    return auta

# --- 2. SAUTO ---
def stahni_sauto_karoq():
    print("⏳ Stahuji Sauto.cz (všechny Karoqy)...")
    auta = []
    api_url = "https://www.sauto.cz/api/v1/items/search"
    for offset in range(0, 100, 20): 
        parametry = {"manufacturer_model_seo": "skoda|karoq", "limit": 20, "offset": offset}
        try:
            odpoved = requests.get(api_url, params=parametry, headers=HLAVICKY, timeout=10)
            if odpoved.status_code != 200: continue
            inzeraty = odpoved.json().get('results', [])
            
            for item in inzeraty:
                nazev = item.get('name', 'Škoda Karoq')
                if "karoq" not in nazev.lower(): continue
                
                cena_int = item.get('price', 0)
                cena_text = f"{cena_int:,} Kč".replace(',', ' ')
                
                item_id = item.get('id', '')
                seo_name = item.get('seoName', item.get('seo_name', ''))
                odkaz = f"https://www.sauto.cz/osobni/detail/skoda/karoq/{seo_name}/{item_id}" if seo_name and item_id else f"https://www.sauto.cz/osobni/detail/{item_id}"

                item_str = json.dumps(item)
                top_stav = je_to_top_stav(nazev, nazev + " " + item_str)

                # SAUTO OBRÁZEK: Vytažení z pevných struktur API místo regexu
                obrazek_url = ""
                try:
                    if '_links' in item and 'gallery' in item['_links'] and len(item['_links']['gallery']) > 0:
                        obrazek_url = item['_links']['gallery'][0].get('href', '')
                        obrazek_url = obrazek_url.replace('{width}', '400').replace('{height}', '300').replace('{ext}', 'jpg')
                except: pass

                # Pokud selže, fallback na regex
                if not obrazek_url:
                    nalezene = re.findall(r'(//(?:[a-z0-9-]+\.)?sdn\.cz/d_[a-z0-9_]+/[a-zA-Z0-9_-]+\.(?:jpg|jpeg|png|webp))', item_str)
                    for img in nalezene:
                        if 'logo' not in img.lower() and 'avatar' not in img.lower():
                            obrazek_url = "https:" + img.replace('\\/', '/')
                            break
                
                obrazek = vycisti_obrazek(obrazek_url, "Sauto")
                auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Sauto.cz", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
        except: pass
        time.sleep(1.0)
        
    print(f"✅ Sauto úspěšně staženo. Nalezeno inzerátů: {len(auta)}")
    return auta

# --- 3. TIPCARS ---
def stahni_tipcars_karoq():
    print("⏳ Stahuji Tipcars (všechny Karoqy)...")
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
                
                top_stav = je_to_top_stav(nazev, nazev + " " + rodic.text)
                
                cena_text = ""
                for t in rodic.find_all(string=True):
                    if "Kč" in t: cena_text = t.strip(); break
                
                # TIPCARS OBRÁZEK: Hledáme v atributech data-original nebo data-src
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

# --- 4. MOBILE.DE ---
def stahni_mobile_de_karoq():
    print("⏳ Stahuji Mobile.de (všechny Karoqy)...")
    auta = []
    api_key = os.getenv('SCRAPER_API_KEY')
    if not api_key:
        print("⚠️ Mobile.de přeskočeno (chybí SCRAPER_API_KEY v Github Secrets).")
        return auta
        
    url = "https://suchen.mobile.de/fahrzeuge/search.html?dam=0&isSearchRequest=true&ms=22900%3A22%3A%3A%3A&ref=srpHead&s=Car&vc=Car"
    try:
        odpoved = requests.get('http://api.scraperapi.com', params={'api_key': api_key, 'url': url, 'render': 'true'}, timeout=60)
        soup = BeautifulSoup(odpoved.text, 'html.parser')
        
        inzeraty = soup.select('.list-entry, .cBox-body--resultitem')
        for inzerat in inzeraty:
            nadpis_element = inzerat.select_one('.h3, h3')
            if not nadpis_element: continue
            nazev = nadpis_element.text.strip()
            if "karoq" not in nazev.lower(): continue
            
            odkaz_tag = inzerat.find('a', href=True)
            if not odkaz_tag: continue
            odkaz = odkaz_tag['href']
            
            cena_element = inzerat.select_one('.price-block, .u-text-bold')
            cena_text = cena_element.text.strip() if cena_element else "Cena na dotaz"
            
            top_stav = je_to_top_stav(nazev, nazev + " " + inzerat.text)
            
            img = inzerat.find('img')
            obrazek_url = img.get('data-src') or img.get('src') if img else ""
            obrazek = vycisti_obrazek(obrazek_url, "Mobile.de")
            
            auta.append({"znacka": "Škoda", "model": nazev, "cena": cena_text, "zdroj": "Mobile.de", "odkaz": odkaz, "obrazek": obrazek, "dokonale_auto": top_stav})
    except Exception as e:
        print(f"Chyba při stahování Mobile.de: {e}")
        
    print(f"✅ Mobile.de úspěšně stažen. Nalezeno inzerátů: {len(auta)}")
    return auta

# --- HLAVNÍ FUNKCE ---
def spust_agregatory():
    print("==================================================")
    print("🚀 SPOUŠTÍM STAHOVÁNÍ KAROQŮ Z CELÉHO INTERNETU 🚀")
    print("==================================================")
    
    vsechna_auta = []
    
    vsechna_auta.extend(stahni_bazos_karoq())
    vsechna_auta.extend(stahni_sauto_karoq())
    vsechna_auta.extend(stahni_tipcars_karoq())
    vsechna_auta.extend(stahni_mobile_de_karoq())
    
    # 🎲 Náhodné proházení všech inzerátů (aby se zdroje pěkně namíchaly)
    random.shuffle(vsechna_auta)
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(vsechna_auta, f, ensure_ascii=False, indent=4)
        
    print("==================================================")
    print(f"🎉 HOTOVO! Celkem uloženo {len(vsechna_auta)} proházených inzerátů do data.json.")
    print("==================================================")

if __name__ == "__main__":
    spust_agregatory()
