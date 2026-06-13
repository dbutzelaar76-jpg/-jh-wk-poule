import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
# Zorg dat hier jouw échte subleague ID staat:
POULE_URL = "https://www.scorito.com/apps/league/index.html?subleagueid=123456" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld of leeg!")
        return

    with sync_playwright() as p:
        # We starten de browser op met een standaard schermgrootte
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        
        try:
            print("1. Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="networkidle")
            
            print("2. Inloggegevens invullen...")
            # We zoeken heel flexibel naar de velden, ongeacht hoe Scorito ze noemt
            page.locator('input[type="email"], input[name="username"], input[id*="username"]').first.fill(SCORITO_USERNAME)
            page.locator('input[type="password"], input[name="password"], input[id*="password"]').first.fill(SCORITO_PASSWORD)
            
            print("3. Klikken op de inlogknop...")
            # We zoeken naar de knop met de tekst 'Inloggen' of het type 'submit'
            inlog_knop = page.locator('button[type="submit"], button:has-text("Inloggen"), input[type="submit"]').first
            inlog_knop.click()
            
            print("4. Wachten op het dashboard (dit kan even duren)...")
            # We geven Scorito max 15 seconden om in te loggen en door te sturen naar de app-omgeving
            page.wait_for_url("**/apps/**", timeout=15000)
            
            print("5. Succesvol ingelogd! Navigeren naar poule...")
            page.goto(POULE_URL, wait_until="networkidle")
            
            print("6. Wachten tot de stand-tabel geladen is...")
            page.wait_for_selector("table, .league-table, [class*='table']", timeout=15000)
            time.sleep(3) # Extra ademruimte voor het inladen van de namen
            
            print("7. Data verzamelen...")
            stand_data = []
            rows = page.query_selector_all("table tr")
            
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) >= 3:
                    positie = cells[0].inner_text().strip()
                    naam = cells[1].inner_text().strip()
                    punten = cells[2].inner_text().strip()
                    
                    stand_data.append({
                        "positie": positie,
                        "naam": naam,
                        "punten": punten
                    })
            
            if stand_data:
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump(stand_data, f, indent=4, ensure_ascii=False)
                print("✅ Stand succesvol opgeslagen in stand.json!")
            else:
                print("⚠️ Waarschuwing: Tabel gevonden, maar geen rijen kunnen uitlezen.")

        except Exception as e:
            print(f"\n❌ ER IS IETS MISGEGAAN TIJDENS HET SCRAPEN:")
            print(f"Foutmelding: {e}")
            
            # We maken een screenshot zodat we kunnen zien of er een popup, captcha of foutmelding in beeld staat
            try:
                page.screenshot(path="error_screenshot.png")
                print("📸 Screenshot van de fout opgeslagen als 'error_screenshot.png'.")
            except:
                print("Kon geen screenshot maken.")
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
