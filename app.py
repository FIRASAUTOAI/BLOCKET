# FIRASAUTOAI - Automatiskt bilfyndsverktyg för Blocket med smart sökning och marginalfilter

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

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form['username'] == 'firas' and request.form['password'] == 'autoai123':
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            return "Fel användarnamn eller lösenord. <a href='/'>Försök igen</a>."
    return '''
    <html>
    <head><title>Login - FIRASAUTOAI</title></head>
    <body>
        <h2>Logga in</h2>
        <form method="post">
            Användarnamn: <input type="text" name="username"><br>
            Lösenord: <input type="password" name="password"><br>
            <input type="submit" value="Logga in">
        </form>
    </body>
    </html>
    '''

@app.route("/home")
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return '''
    <html>
    <head><title>FIRASAUTOAI</title></head>
    <body>
        <h2>Sök Blocket-fynd</h2>
        <form action="/search" method="post">
            Märke: <input type="text" name="brand"><br>
            Modell: <input type="text" name="model"><br>
            Maxpris: <input type="number" name="max_price"><br>
            Max mil: <input type="number" name="max_mileage"><br>
            Från årsmodell: <input type="number" name="min_year"><br>
            Nuvarande miltal: <input type="number" name="current_mileage"><br>
            Nuvarande årsmodell: <input type="number" name="current_year"><br>
            <input type="submit" value="Sök">
        </form>
    </body>
    </html>
    '''

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
    return redirect(url_for('autobot'))

@app.route("/autobot")
def autobot():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://www.blocket.se/annonser/hela_sverige/fordon/bilar"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all("a", class_="Link-sc-__sc-1s9xv6a-0")

        min_margin = 20000
        result_count = 0

        for listing in listings:
            href = listing.get("href")
            title = listing.text.lower()
            if href and "/annons/" in href:
                annons_url = "https://www.blocket.se" + href
                annons_response = requests.get(annons_url, headers=headers)
                annons_soup = BeautifulSoup(annons_response.text, 'html.parser')
                pris_tag = annons_soup.find("div", class_=re.compile("Price__StyledPrice"))
                if not pris_tag:
                    continue
                try:
                    match_price = int(re.sub(r'[^0-9]', '', pris_tag.text))
                except:
                    continue

                referens_url = "https://www.blocket.se/annonser/hela_sverige/fordon/bilar?pe=2"
                ref_response = requests.get(referens_url, headers=headers)
                ref_soup = BeautifulSoup(ref_response.text, 'html.parser')
                ref_listings = ref_soup.find_all("div", class_=re.compile("Price__StyledPrice"))

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
                    avg_price = sum(prices) // len(prices)
                    marginal = avg_price - match_price
                    if marginal >= min_margin:
                        resultat = f"💰 Fynd hittat!\n{title}\nPris: {match_price} kr\nRef: {avg_price} kr\nMarginal: +{marginal} kr\n{annons_url}"
                        skicka_telegram(resultat)
                        result_count += 1

                time.sleep(1)

        if result_count == 0:
            skicka_telegram("Inga nya fynd denna gång.")

        return "Autobot kördes utan fel."
    except Exception as e:
        return f"Fel: {str(e)}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
