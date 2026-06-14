import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
# De directe ranking pagina
POULE_URL = "https://www.scorito.com/footballtournament/ranking/301/1036045"

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # We gebruiken een schone context
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            print("1. Rechtstreeks inloggen via de Scorito API (omzeilt het witte scherm)...")
            
            # We bootsen exact na wat de app doet als je op 'Inloggen' drukt
            login_url = "https://www.scorito.com/Public/api/v1/account/login"
            payload = {
                "username": SCORITO_USERNAME,
                "password": SCORITO_PASSWORD
            }
            
            # Voer het verzoek uit via de ingebouwde API-requestor van Playwright
            response = page.request.post(
                login_url,
                headers={"Content-Type": "application/json"},
                data=payload
            )
            
            if response.status == 200:
                print("✅ API Login succesvol! Cookies zijn gegenereerd.")
                # De cookies worden automatisch opgeslagen in deze browser-context
            else:
                print(f"❌ API Login geweigerd (Status {response.status}).")
                print("Antwoord van server:", response.text())
                raise Exception("Inloggen via API mislukt. Controleer je gebruikersnaam/wachtwoord.")

            print("2. Direct navigeren naar de Poule Ranking...")
            page.goto(POULE_URL, wait_until="commit")
            
            print("3. Wachten tot de stand-tabel op het scherm verschijnt...")
            # We wachten tot de rankingcontainer of tabel geladen is (max 25 seconden)
            page.wait_for_selector('[class*="ranking"], [class*="list"], table, .ranking-table', timeout=25000)
            time.sleep(5)  # Geef de namen even de tijd om asynchroon in te laden

            # Sla het resultaat op als screenshot om te controleren of de stand er staat
            page.screenshot(path="success_screenshot.png", full_page=True)
            print("📸 Stand-scherm succesvol vastgelegd als success_screenshot.png!")

            print("4. Data verzamelen uit de pagina...")
            stand_data = []
            
            # We zoeken naar alle elementen die de regels van de stand bevatten
            rows = page.locator('[class*="row"], [class*="item"], tr').all()
            print(f"Aantal potentiële regels gevonden: {len(rows)}")

            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text and "\n" in text:
                        parts = text.split("\n")
                        # Rij moet beginnen met een getal (positie) en minstens 3 delen bevatten
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
                print(f"🎉 HOERA! Stand succesvol opgeslagen! {len(stand_data)} deelnemers verwerkt.")
            else:
                print("⚠️ Waarschuwing: Pagina geopend, maar de tabelstructuur bevat geen leesbare tekst.")

        except Exception as e:
            print(f"\n❌ ER IS IETS MISGEGAAN TIJDENS HET SCRAPEN: {e}")
            try:
                page.screenshot(path="error_screenshot.png", full_page=True)
                print("📸 Fout-screenshot opgeslagen.")
            except:
                pass
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
