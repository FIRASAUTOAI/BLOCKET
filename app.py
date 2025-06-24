# FIRASAUTOAI – Ren version utan realtidsutskrift, med Excel-export

import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
from datetime import datetime

fynd = []
ANTAL_SIDOR = 10  # 10 sidor x ~20 annonser = ca 200 annonser
REFERENS_PER = 3
PAUS_SEK = 1.5

start_tid = time.time()
antal_testade = 0

for page in range(1, ANTAL_SIDOR + 1):
    url = f"https://www.blocket.se/annonser/hela_sverige/fordon/bilar?page={page}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    länkar = soup.find_all("a", href=re.compile("/annons/"))
    print(f"🔄 Sida {page}: {len(länkar)} annonser hämtade")

    for länk in länkar:
        annons_url = "https://www.blocket.se" + länk["href"]
        annons_respons = requests.get(annons_url)
        annons_html = BeautifulSoup(annons_respons.text, 'html.parser')

        text = annons_html.get_text().lower()

        pris_match = re.search(r'(\d[\d\s]{2,10}) ?kr', text)
        mil_match = re.search(r'(\d[\d\s]{2,6}) ?mil', text)
        år_match = re.search(r'20\d{2}', text)
        title_tag = annons_html.find("title")
        title = title_tag.get_text().lower() if title_tag else ""

        try:
            pris = int(pris_match.group(1).replace(" ", "")) if pris_match else None
            mil = int(mil_match.group(1).replace(" ", "")) if mil_match else None
            år = int(år_match.group(0)) if år_match else None
        except:
            continue

        if not pris or not mil or not år:
            continue

        antal_testade += 1

        
        huvudtitel = title.split()
        sökfras = " ".join([ord for ord in huvudtitel if ord not in ["till", "salu", "euro", "nybesiktigad"]][:3])
        referens_url = f"https://www.blocket.se/annonser/hela_sverige/fordon/bilar?q={sökfras.replace(' ', '+')}"
        referens_response = requests.get(referens_url)
        referens_soup = BeautifulSoup(referens_response.text, 'html.parser')
        referens_annonser = referens_soup.find_all("a", href=re.compile("/annons/"))

        referenspriser = []
        for ref_länk in referens_annonser[:7]:
            ref_url = "https://www.blocket.se" + ref_länk["href"]
            ref_resp = requests.get(ref_url)
            ref_html = BeautifulSoup(ref_resp.text, 'html.parser')
            ref_text = ref_html.get_text().lower()
            ref_pris_match = re.search(r'(\d[\d\s]{2,10}) ?kr', ref_text)
            if ref_pris_match:
                try:
                    p = int(ref_pris_match.group(1).replace(" ", ""))
                    referenspriser.append(p)
                except:
                    continue

        if referenspriser:
            snittpris = sum(referenspriser) // len(referenspriser)
            marginal = snittpris - pris
            fynd.append((pris, mil, år, annons_url, marginal, snittpris))
            print(f"✅ {pris} kr | {mil} mil | {år} – Marginal: {marginal} kr (Snitt: {snittpris})
🔗 {annons_url}
")

    time.sleep(PAUS_SEK)

# 📋 Slutresultat
for f in fynd:
    print(f"✅ Pris: {f[0]} kr | Mil: {f[1]} | År: {f[2]} | Marginal: {f[4]} kr (Snittpris: {f[5]} kr)\n🔗 {f[3]}\n")

if not fynd:
    print("❌ Inga bilannonser hittades – eller inga jämförpriser kunde beräknas.")

slut_tid = time.time()
print("\n🔢 Statistik:")
print(f"🔎 Analyserade annonser: {antal_testade}")
print(f"💰 Fynd hittade: {len(fynd)}")
print(f"⏱️ Tid totalt: {round(slut_tid - start_tid, 1)} sekunder")

# 💾 Spara till Excel
if fynd:
    df = pd.DataFrame(fynd, columns=["Pris", "Mil", "År", "Länk", "Marginal", "Snittpris"])
    filename = f"fynd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df.to_excel(filename, index=False)
    print(f"📁 Excel-fil sparad: {filename}")
