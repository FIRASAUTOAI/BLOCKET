# FIRASAUTOAI - Automatiskt bilfyndsverktyg för Blocket med marginalfilter och lösenordsskydd

from flask import Flask, render_template, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
import re
import time

app = Flask(__name__)
app.secret_key = 'superhemligt_losen'  # Ändra detta till ett starkt lösenord

# Inloggning
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

@app.route("/search", methods=["POST"])
def search():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        brand = request.form.get("brand", "").lower()
        model = request.form.get("model", "").lower()
        max_price = int(request.form.get("max_price") or 0)
        max_mileage = int(request.form.get("max_mileage") or 999999)
        min_year = int(request.form.get("min_year") or 0)
        current_mileage = int(request.form.get("current_mileage") or 0)
        current_year = int(request.form.get("current_year") or 0)
        min_margin = 25000

        headers = {"User-Agent": "Mozilla/5.0"}

        url = "https://www.blocket.se/annonser/hela_sverige/fordon/bilar"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.find_all("a", class_="Link-sc-__sc-1s9xv6a-0")

        results = []
        for listing in listings:
            href = listing.get("href")
            title = listing.text.lower()
            if href and "/annons/" in href and brand in title and model in title:
                annons_url = "https://www.blocket.se" + href

                referens_url = f"https://www.blocket.se/annonser/hela_sverige/fordon/bilar?q={brand}+{model}&pe=2"
                ref_response = requests.get(referens_url, headers=headers)
                ref_soup = BeautifulSoup(ref_response.text, 'html.parser')
                ref_listings = ref_soup.find_all("div", class_=re.compile("Price__StyledPrice-sc-__sc-1g0n27r-0"))

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
                    marginal = avg_price - max_price
                    if marginal >= min_margin:
                        results.append(f"{annons_url} - 💰 Marginal: +{marginal} kr (Ref: {avg_price} kr)")

                time.sleep(1)

        return '''<html><head><title>Resultat</title></head><body>
            <h3>Matchande annonser:</h3>
            <ul>
            ''' + ''.join([f'<li><a href="{r.split(" - ")[0]}" target="_blank">{r}</a></li>' for r in results]) + '''
            </ul>
            <a href="/home">Tillbaka</a>
        </body></html>'''

    except Exception as e:
        return f"<h2>Fel uppstod:</h2><pre>{str(e)}</pre>"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)

