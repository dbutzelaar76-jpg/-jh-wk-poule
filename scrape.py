import os
import json
import time
import requests

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")

# We trekken de poule-ID en turnooi-ID uit je originele URL om de rechtstreekse datastream aan te spreken
# Origineel: https://www.scorito.com/footballtournament/ranking/301/1036045
TOURNAMENT_ID = 301
POOL_ID = 1036045

def scrape_scorito_via_api():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld!")
        return

    print("1. Inloggen via de Scorito API...")
    session = requests.Session()
    
    api_url = "https://api.scorito.com/v1/login"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.scorito.com",
        "Referer": "https://www.scorito.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    payload = {
        "username": SCORITO_USERNAME,
        "password": SCORITO_PASSWORD
    }
    
    try:
        response = session.post(api_url, json=payload, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Hoofd-API gaf status {response.status_code}, we proberen de auth-fallback...")
            fallback_url = "https://authentication.scorito.com/api/v1/login"
            response = session.post(fallback_url, json=payload, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"❌ API Authenticatie mislukt (Status {response.status_code}).")
            return

        print("✅ API Login succesvol! Sessie is actief.")
        
        print("2. Stand-gegevens rechtstreeks opvragen bij de Scorito dataserver...")
        # Dit is de directe endpoint waar Scorito de ranking-data ophaalt voor jouw poule
        ranking_url = f"https://api.scorito.com/v1/footballtournament/ranking/{TOURNAMENT_ID}/{POOL_ID}"
        
        # We updaten de headers zodat de server ziet dat we netjes geautoriseerd zijn
        headers["Referer"] = f"https://www.scorito.com/footballtournament/ranking/{TOURNAMENT_ID}/{POOL_ID}"
        
        ranking_response = session.get(ranking_url, headers=headers, timeout=15)
        
        # Mocht de specifieke endpoint net een andere structuur vereisen, proberen we de algemene pool-ranking fallback
        if ranking_response.status_code != 200:
            print("Primaire ranking-endpoint niet bereikbaar, we proberen de algemene ranking-resource...")
            fallback_ranking_url = f"https://api.scorito.com/v1/poule/{POOL_ID}/ranking"
            ranking_response = session.get(fallback_ranking_url, headers=headers, timeout=15)

        if ranking_response.status_code == 200:
            raw_data = ranking_response.json()
            stand_data = []
            
            print("3. Data succesvol ontvangen! Structuur parsen...")
            
            # Scorito levert de ranking vaak aan in een 'ranking' of 'content' array
            items = raw_data.get("ranking", raw_data.get("content", raw_data.get("results", [])))
            
            # Als de root een lijst is, pakken we die direct
            if isinstance(raw_data, list):
                items = raw_data
                
            if not items and "data" in raw_data:
                items = raw_data["data"].get("ranking", [])

            for item in items:
                # We vangen flexibel de meest voorkomende datavelden van de Scorito API op
                naam = item.get("username", item.get("name", item.get("playerName", "Onbekend")))
                pos = item.get("position", item.get("rank", item.get("currentPosition", "-")))
                punten = item.get("points", item.get("totalPoints", item.get("score", 0)))
                
                stand_data.append({
                    "positie": str(pos),
                    "naam": str(naam),
                    "punten": str(punten)
                })

            # Mocht de JSON-structuur complexer zijn, slaan we als ultieme redding de ruwe data op
            if not stand_data and items:
                print("Lijst gevonden maar velden wijken af. We slaan de ruwe objecten op.")
                stand_data = items

            if stand_data:
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump(stand_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Stand succesvol opgeslagen! {len(stand_data)} deelnemers verwerkt.")
            else:
                print("⚠️ Server gaf antwoord, maar de JSON-structuur bevatte geen bekende klassement-lijst.")
                # Schrijf de ruwe response weg om te kunnen zien wat Scorito teruggeeft
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, indent=4)
        else:
            print(f"❌ Kon de stand niet ophalen van de API. Statuscode: {ranking_response.status_code}")
            print("Response:", ranking_response.text)

    except Exception as e:
        print(f"❌ Fout tijdens het API-scrapen: {e}")

if __name__ == "__main__":
    scrape_scorito_via_api()
