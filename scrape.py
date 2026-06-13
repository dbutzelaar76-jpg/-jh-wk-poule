import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
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
            email_field = page.locator('input[type="email"], input[name*="username"], input[name*="mail"]').first
            password_field = page.locator('input[type="password"]').first
            
            email_field.wait_for(state="visible", timeout=15000)
            email_field.fill(SCORITO_USERNAME)
            password_field.fill(SCORITO_PASSWORD)
            
            print("3. Klikken op de inlogknop...")
            inlog_knop = page.locator('button[type="submit"], button:has-text("Inloggen"), .login-button').first
            inlog_knop.click()
            
            print("4. Wachten op succesvolle login...")
            page.wait_for_url("**/apps/**", timeout=25000)
            print("Inloggen geslaagd!")
            
            print("5. Navigeren naar de juiste poule-ranking...")
            page.goto(POULE_URL, wait_until="domcontentloaded")
            
            print("6. Wachten tot de asynchrone data (de ranking) geladen is...")
            # We wachten op de specifieke ranking/stand-elementen uit de React-app
            page.wait_for_selector('[class*="ranking"], [class*="list"], table tr', timeout=20000)
            time.sleep(6) # Extra ademruimte voor de trage JavaScript-inladen
            
            # --- CLAUDE'S TIP: Maak een screenshot bij succes ---
            try:
                page.screenshot(path="success_screenshot.png", full_page=True)
                print("📸 Succes-screenshot opgeslagen als 'success_screenshot.png'!")
            except Exception as e_img:
                print(f"Kon geen succes-screenshot maken: {e_img}")

            print("7. Data verzamelen uit de pagina...")
            stand_data = []
            
            # We pakken breed alle elementen die eruitzien als een rij in de ranking
            rows = page.locator('[class*="row"], [class*="item"], tr').all()
            print(f"Systeemelementen gevonden om te scannen: {len(rows)}")
            
            # We lezen de inner teksten uit om de namen en punten te filteren
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text and "\n" in text:
                        parts = text.split("\n")
                        # Controleren of de rij begint met een positie-getal (bijv: 31 \n Johan \n 90)
                        if len(parts) >= 3 and parts[0].replace('.', '').isdigit():
                            pos = parts[0].replace('.', '')
                            naam = parts[1]
                            punten = parts[2]
                            
                            # Voorkom dubbele regels in onze JSON
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
                print("⚠️ Waarschuwing: Pagina geladen, maar kon geen data uit de elementen persen.")

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
