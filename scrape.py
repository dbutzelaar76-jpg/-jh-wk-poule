import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
# Claude's juiste, directe desktop-URL:
POULE_URL = "https://www.scorito.com/footballtournament/ranking/301/1036045" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld of leeg!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="nl-NL"
        )
        page = context.new_page()
        
        try:
            print("1. Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="domcontentloaded")
            time.sleep(2)
            
            print("1b. Controleren op cookie-pop-up...")
            cookie_button = page.locator('button:has-text("Akkoord"), button:has-text("Accepteren"), button:has-text("Accept"), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll').first
            try:
                if cookie_button.is_visible(timeout=3000):
                    print("Cookie-pop-up gevonden, we klikken op akkoord...")
                    cookie_button.click()
                    time.sleep(2)
            except:
                print("Geen cookie-pop-up geactiveerd.")

            print("2. Inloggegevens invullen...")
            # Nu we op de normale desktopsite zitten, kunnen we direct de standaard ID's/types pakken
            email_field = page.locator('input[type="email"], input[name*="username"], input[name*="mail"]').first
            password_field = page.locator('input[type="password"]').first
            
            email_field.wait_for(state="visible", timeout=15000)
            email_field.fill(SCORITO_USERNAME)
            password_field.fill(SCORITO_PASSWORD)
            
            print("3. Klikken op de inlogknop...")
            inlog_knop = page.locator('button[type="submit"], button:has-text("Inloggen"), .login-button').first
            inlog_knop.click()
            
            print("4. Wachten op succesvolle login (navigatie naar profiel/apps)...")
            # We wachten tot de URL verandert richting de Scorito app-omgeving
            page.wait_for_url("**/apps/**", timeout=25000)
            print("Inloggen geslaagd!")
            
            print("5. Navigeren naar de juiste poule-ranking...")
            page.goto(POULE_URL, wait_until="domcontentloaded")
            
            print("6. Wachten tot de stand-tabel én de asynchrone data geladen zijn...")
            # We wachten specifiek tot er een tabelrij (tr) verschijnt die data bevat
            # We geven Scorito maximaal 20 seconden om de data op te halen en te tonen
            page.wait_for_selector("table tbody tr, .ranking-table tr, [class*='table'] tr", timeout=20000)
            time.sleep(5) # Extra ademruimte om te zorgen dat écht alle namen er staan
            
            print("7. Data verzamelen uit de tabel...")
            stand_data = []
            
            # We zoeken naar alle rijen in de tabel
            rows = page.locator("table tr, .ranking-table tr, [class*='table'] tr").all()
            print(f"Aantal gevonden rijen in de tabel: {len(rows)}")
            
            for row in rows:
                try:
                    # Haal alle cellen/kolommen binnen deze rij op
                    cells = row.locator("td").all()
                    if len(cells) >= 3:
                        positie = cells[0].inner_text().strip()
                        naam = cells[1].inner_text().strip()
                        punten = cells[2].inner_text().strip()
                        
                        # Alleen toevoegen als het een geldige regel is (positie moet een getal zijn)
                        if positie.replace('.', '').isdigit() and naam:
                            stand_data.append({
                                "positie": positie.replace('.', ''),
                                "naam": naam,
                                "punten": punten
                            })
                except Exception:
                    continue

            if stand_data:
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump(stand_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Stand succesvol opgeslagen! {len(stand_data)} deelnemers verwerkt.")
            else:
                raise Exception("Tabel wel gevonden, maar kon geen geldige rijen met tekst ontleden.")

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
