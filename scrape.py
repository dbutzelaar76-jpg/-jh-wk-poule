import os
import json
import requests

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")

TOURNAMENT_ID = 301
POOL_ID = 1036045

def debug_scorito_api():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld of leeg!")
        return

    print(f"DEBUG: Starten met gebruiker: {SCORITO_USERNAME[:3]}***")
    session = requests.Session()
    
    # We gebruiken exact de headers die de officiële Scorito web-app meestuurt
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.scorito.com",
        "Referer": "https://www.scorito.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    payload = {
        "username": SCORITO_USERNAME,
        "password": SCORITO_PASSWORD
    }
    
    # --- STAP 1: INLOGGEN ---
    print("\n--- STAP 1: Proberen in te loggen via API ---")
    login_url = "https://api.scorito.com/v1/login"
    try:
        response = session.post(login_url, json=payload, headers=headers, timeout=15)
        print(f"Login Statuscode: {response.status_code}")
        print(f"Login Response Tekst: {response.text[:500]}") # Print de eerste 500 tekens van het antwoord
        
        if response.status_code != 200:
            print("\nProberen via authenticatie-fallback URL...")
            fallback_url = "https://authentication.scorito.com/api/v1/login"
            response = session.post(fallback_url, json=payload, headers=headers, timeout=15)
            print(f"Fallback Login Statuscode: {response.status_code}")
            print(f"Fallback Login Response: {response.text[:500]}")

        if response.status_code != 200:
            print("❌ Inloggen is volledig mislukt op beide endpoints. Controleer eventueel je wachtwoord in GitHub Secrets.")
            return
            
    except Exception as e:
        print(f"❌ Crash tijdens inloggen: {e}")
        return

    # --- STAP 2: DATA OPHALEN ---
    print("\n--- STAP 2: Proberen stand op te halen ---")
    ranking_url = f"https://api.scorito.com/v1/footballtournament/ranking/{TOURNAMENT_ID}/{POOL_ID}"
    headers["Referer"] = f"https://www.scorito.com/footballtournament/ranking/{TOURNAMENT_ID}/{POOL_ID}"
    
    # Voeg eventuele autorisatie-tokens toe als Scorito die in de login-response heeft meegestuurd
    try:
        login_json = response.json()
        if "token" in login_json:
            headers["Authorization"] = f"Bearer {login_json['token']}"
            print("Token gevonden en toegevoegd aan Authorization header.")
    except:
        pass

    try:
        ranking_response = session.get(ranking_url, headers=headers, timeout=15)
        print(f"Ranking Statuscode: {ranking_response.status_code}")
        print(f"Ranking Response Tekst: {ranking_response.text[:1000]}") # Dit laat ons de echte JSON-structuur zien
        
        if ranking_response.status_code != 200:
            print("\nProberen via alternatieve poule-ranking route...")
            fallback_ranking_url = f"https://api.scorito.com/v1/poule/{POOL_ID}/ranking"
            ranking_response = session.get(fallback_ranking_url, headers=headers, timeout=15)
            print(f"Fallback Ranking Statuscode: {ranking_response.status_code}")
            print(f"Fallback Ranking Response: {ranking_response.text[:1000]}")

        if ranking_response.status_code == 200:
            # Als dit lukt, schrijven we de ruwe data direct onbewerkt weg naar stand.json
            raw_data = ranking_response.json()
            with open("stand.json", "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=4, ensure_ascii=False)
            print("✅ Ruwe data succesvol in stand.json gedumpt!")
        else:
            print("❌ Beide ranking-endpoints gaven geen 200 OK.")

    except Exception as e:
        print(f"❌ Crash tijdens ophalen ranking: {e}")

if __name__ == "__main__":
    debug_scorito_api()
