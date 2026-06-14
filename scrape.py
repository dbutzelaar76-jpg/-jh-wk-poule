import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
POULE_URL = "https://www.scorito.com/footballtournament/ranking/301/1036045" 

def login_via_api():
    print("1. Inlogtokens opvragen via de Scorito API...")
    session = requests.Session()
    
    # Dit is het authenticatie-eindpunt dat door de mobiele apps en platformen wordt gebruikt
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
        
        # Als de specifieke mobiele API niet reageert, proberen we de universele login fallback
        if response.status_code != 200:
            print(f"Mobiele API gaf status {response.status_code}, we proberen de web-auth-fallback...")
            fallback_url = "https://authentication.scorito.com/api/v1/login"
            response = session.post(fallback_url, json=payload, headers=headers, timeout=15)

        if response.status_code == 200:
            print("✅ API Login succesvol! Sessie-cookies zijn binnengehaald.")
            # Haal de cookies uit de succesvolle requests-sessie
            cookies = []
            for cookie in session.cookies:
                cookies.append({
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain if cookie.domain.startswith('.') else f".{cookie.domain}",
                    "path": cookie.path,
                    "expires": cookie.expires if cookie.expires else int(time.time() + 86400),
                    "httpOnly": cookie.has_nonstandard_attr('HttpOnly'),
                    "secure": cookie.secure
                })
            return cookies
        else:
            print(f"❌ API Authenticatie geweigerd (Status {response.status_code}).")
            print("Server response:", response.text)
            return None
    except Exception as e:
        print(f"❌ Fout tijdens API-verzoek: {e}")
        return None

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld!")
        return

    # Eerst de cookies via de achterdeur ophalen
    auth_cookies = login_via_api()
    
    with sync_playwright() as p:
        print("2. Opstarten browser om direct naar de poule te springen...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            if auth_cookies:
                print("3. Inlogcookies rechtstreeks in de browser injecteren...")
                context.add_cookies(auth_cookies)
                print("Cookies succesvol toegevoegd. De browser is nu direct ingelogd!")
            else:
                print("⚠️ Geen API-cookies verkregen. We proberen de pagina kaal te openen...")

            print("4. Direct navigeren naar de Poule Ranking...")
            page.goto(POULE_URL, wait_until="networkidle", timeout=60000)
            time.sleep(5) # Rustig de stand laten renderen op het scherm

            # Maak een screenshot ter controle
            page.screenshot(path="success_screenshot.png", full_page=True)
            print("📸 Stand-scherm vastgelegd als success_screenshot.png")
            
            print("5. Data verzamelen uit de pagina...")
            stand_data = []
            
            # Selecteer alle potentiële tabelrijen of lijstitems
            rows = page.locator('[class*="row"], [class*="item"], tr').all()
            print(f"Aantal potentiële datarijen gedetecteerd: {len(rows)}")
            
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text and "\n" in text:
                        parts = text.split("\n")
                        if len(parts) >= 3 and parts[0].replace('.', '').isdigit():
                            pos = parts[0].replace('.', '')
                            naam = parts[1]
                            punten = parts[2]
                            
                            if {"positie": pos, "naam": naam, "punten": punten} not in stand_data:
                                stand_data.append({
                                    "positie": pos,
                                    "naam": naam,
                                    "punten": punten
                                })
                except:
                    continue

            if stand_data:
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump(stand_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Stand succesvol opgeslagen! {len(stand_data)} deelnemers verwerkt.")
            else:
                print("⚠️ Waarschuwing: Pagina geopend, maar kon geen tabelrijen omzetten naar JSON.")

        except Exception as e:
            print(f"\n❌ ER IS IETS MISGEGAAN TIJDENS HET SCRAPEN: {e}")
            try:
                page.screenshot(path="error_screenshot.png", full_page=True)
                print("📸 Fout-screenshot succesvol opgeslagen!")
            except:
                pass
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
