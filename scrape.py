import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
POULE_URL = "https://www.scorito.com/apps/league/index.html?subleagueid=123456" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld of leeg!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # We zetten de taal op Nederlands, dat helpt bij het herkennen van de cookieknop
        context = browser.new_context(viewport={"width": 1280, "height": 720}, locale="nl-NL")
        page = context.new_page()
        
        try:
            print("1. Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="networkidle")
            
            # --- NIEUW: COOKIE POP-UP WEGKLIKKEN ---
            print("1b. Controleren op cookie-pop-up...")
            cookie_button = page.locator('button:has-text("Akkoord"), button:has-text("Accepteren"), button:has-text("Accept"), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll')
            
            if cookie_button.first.is_visible(timeout=5000):
                print("Cookie-pop-up gevonden, we klikken op akkoord...")
                cookie_button.first.click()
                time.sleep(1) # Halve seconde wachten tot de pop-up animatie weg is
            else:
                print("Geen cookie-pop-up in beeld, we gaan door.")
            # ---------------------------------------

            print("2. Inloggegevens invullen...")
            page.locator('input[type="email"], input[name="username"], input[id*="username"]').first.wait_for(state="visible", timeout=10000)
            page.locator('input[type="email"], input[name="username"], input[id*="username"]').first.fill(SCORITO_USERNAME)
            page.locator('input[type="password"], input[name="password"], input[id*="password"]').first.fill(SCORITO_PASSWORD)
            
            print("3. Klikken op de inlogknop...")
            inlog_knop = page.locator('button[type="submit"], button:has-text("Inloggen"), input[type="submit"]').first
            inlog_knop.click()
            
            print("4. Wachten op het dashboard...")
            page.wait_for_url("**/apps/**", timeout=20000)
            
            print("5. Succesvol ingelogd! Navigeren naar poule...")
            page.goto(POULE_URL, wait_until="networkidle")
            
            print("6. Wachten tot de stand-tabel geladen is...")
            page.wait_for_selector("table, .league-table, [class*='table']", timeout=15000)
            time.sleep(3)
            
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
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
