import os
import json
import time
from playwright.sync_api import sync_playwright

# Haal inloggegevens veilig op uit GitHub
SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")

# VERVANG HIERONDER DE 123456 DOOR JOUW EIGEN SUBLEAGUE ID:
POULE_URL = "https://www.scorito.com/apps/league/index.html?subleagueid=1036045" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print("Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="networkidle")
            
            print("Inloggegevens invullen...")
            page.locator('input[type="email"], input[name="username"]').fill(SCORITO_USERNAME)
            page.locator('input[type="password"]').fill(SCORITO_PASSWORD)
            
            print("Klikken op de inlogknop...")
            page.locator('button[type="submit"], button:has-text("Inloggen")').click()
            
            print("Wachten op het dashboard...")
            page.wait_for_url("**/apps/**", timeout=15000)
            
            print("Succesvol ingelogd! Navigeren naar poule...")
            page.goto(POULE_URL, wait_until="networkidle")
            
            print("Wachten tot de stand-tabel geladen is...")
            page.wait_for_selector("table, .league-table", timeout=15000)
            time.sleep(3)
            
            print("Data verzamelen...")
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
                print("Stand succesvol opgeslagen in stand.json!")
            else:
                print("Geen data gevonden in de tabel.")

        except Exception as e:
            print(f"\n❌ ER IS IETS MISGEGAAN:\n{e}")
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
