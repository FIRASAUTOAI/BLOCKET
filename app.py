# FIRASAUTOAI - Automatiskt bilfyndsverktyg för Blocket med smart sökning, extern värdering och fyndarkiv

from flask import Flask, render_template, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
import re
import time
from difflib import SequenceMatcher

app = Flask(__name__)
app.secret_key = 'superhemligt_losen'

TELEGRAM_BOT_TOKEN = '7548627749:AAHuRgWJLgwh-Yk-PJHFAmRhmCfKfY0hAow'
TELEGRAM_CHAT_ID = '7819614595'

fyndarkiv = []
from datetime import datetime

fyndarkiv = []
testade_annons_ids = set()  # Nollställs vid varje körning

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form['username'] == 'firas' and request.form['password'] == 'autoai123':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return "Fel användarnamn eller lösenord. <a href='/'>Försök igen</a>."
    return '''<html><head><title>Login - FIRASAUTOAI</title></head><body>
        <h2>Logga in</h2><form method="post">
        Användarnamn: <input type="text" name="username"><br>
        Lösenord: <input type="password" name="password"><br>
        <input type="submit" value="Logga in"></form></body></html>'''

@app.route("/home")
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return '''<html><head><title>FIRASAUTOAI</title></head><body>
        <h2>Sök Blocket-fynd</h2>
        <form action="/search" method="post">
        Märke: <input type="text" name="brand"><br>
        Modell: <input type="text" name="model"><br>
        Maxpris: <input type="number" name="max_price"><br>
        Max mil: <input type="number" name="max_mileage"><br>
        Från årsmodell: <input type="number" name="min_year"><br>
        Nuvarande miltal: <input type="number" name="current_mileage"><br>
        Nuvarande årsmodell: <input type="number" name="current_year"><br>
        Nyckelord (komma-separerade): <input type="text" name="keywords" value="volvo,bmw,audi,vw,mercedes,mazda,toyota,skoda,peugeot"><br>
        <input type="submit" value="Sök"></form>
        <h3><a href="/fynd">📦 Visa fyndarkiv</a></h3></body></html>'''

@app.route("/fynd")
def visa_fyndarkiv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return '<br>'.join(fyndarkiv) or "Inga fynd har loggats än."

def likhet(a, b):
    return SequenceMatcher(None, a, b).ratio()

def skicka_telegram(meddelande):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": meddelande}
    requests.post(url, data=data)

@app.route("/search", methods=["POST"])
def search():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    session['custom_keywords'] = request.form.get('keywords', '')
    return redirect(url_for('autobot'))

@app.route("/autobot")
def autobot():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        min_margin = 15000
        result_count = 0
        testade_count = 0

        for page in range(1, 51):
            url = f"https://www.blocket.se/bilar/start?page={page}"
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            all_links = soup.find_all("a", href=True)
            listings = [a for a in all_links if "/annons/" in a["href"]]

            for listing in listings:
                testade_count += 1
                href = listing.get("href")
                title = listing.text.lower()
                annons_url = "https://www.blocket.se" + href
                if annons_url in testade_annons_ids:
                    continue
                testade_annons_ids.add(annons_url)
                annons_response = requests.get(annons_url, headers=headers)
                annons_soup = BeautifulSoup(annons_response.text, 'html.parser')

                pris_text = annons_soup.get_text()
                pris_match = re.search(r'(\d{2,3}[ \d]{0,3}) ?kr', pris_text)
                if not pris_match:
                    continue
                try:
                    match_price = int(re.sub(r'[^0-9]', '', pris_match.group(1)))
                except:
                    continue

                regnummer_match = re.search(r'([A-Z]{3}\d{3})', pris_text)

                nyckelord = session.get('custom_keywords', '').lower().split(',') if session.get('custom_keywords') else [
    "volvo", "bmw", "audi", "vw", "volkswagen", "mercedes", "mazda", "toyota", "skoda", "peugeot", "citroen", "ford", "nissan", "kia", "hyundai", "renault", "honda", "opel", "seat", "fiat", "subaru", "suzuki", "chevrolet", "jeep", "dacia", "lexus", "tesla",
    "v40", "v50", "v60", "v70", "s60", "s80", "golf", "passat", "a1", "a3", "a4", "a5", "a6", "d2", "d3", "d4", "d5", "tdi", "tsi", "tce"
]
                huvudtitel = title.split()
                sökfras = " ".join(huvudtitel)

                värde = None
                
                if not värde:
                    referens_url = f"https://www.blocket.se/annonser/hela_sverige/fordon/bilar?q={'+'.join(huvudtitel)}&f=dealer"
                    print(f'[DEBUG] Sökfras: {sökfras}')
                    print(f'[DEBUG] Referens-URL: {referens_url}')
                    ref_response = requests.get(referens_url, headers=headers)
                    ref_soup = BeautifulSoup(ref_response.text, 'html.parser')
                    ref_listings = ref_soup.find_all("div", class_=re.compile("Price"))

                    prices = []
                    for item in ref_listings:
                        try:
                            price = int(re.sub(r'[^0-9]', '', item.text))
                            prices.append(price)
                            if len(prices) >= 7:
                                break
                        except:
                            continue
                    if prices:
                        print(f'[DEBUG] Referenspriser: {prices}')
                        värde = sum(prices) // len(prices)
                    else:
                        print('[DEBUG] Inga referenspriser hittades – använder fallbackvärde 0')
                        värde = 0

                if värde > 0 and värde - match_price >= min_margin:
                    from datetime import datetime
                    datum = datetime.now().strftime('%Y-%m-%d %H:%M')
                    resultat = f"""💰 Fynd hittat!
{sökfras}
Pris: {match_price} kr
Marknadsvärde: {värde} kr
Marginal: +{värde - match_price} kr
{annons_url}
⏰ {datum}"""
                    fyndarkiv.append(f'<a href="{annons_url}" target="_blank">{resultat.replace(chr(10), "<br>")}</a>')
                    skicka_telegram(resultat)
                    result_count += 1
                time.sleep(0.3)
            time.sleep(0.5)

        if result_count == 0:
            skicka_telegram("Inga nya fynd denna gång.")

        skicka_telegram(f"✅ Autobot färdig. {result_count} fynd hittade efter att ha analyserat {testade_count} annonser.")
        return "Autobot kördes utan fel."
    except Exception as e:
        return f"Fel: {str(e)}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
