import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
POULE_URL = "https://www.scorito.com/apps/league/index.html?subleagueid=1036045" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld of leeg!")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="nl-NL"
        )
        page = context.new_page()
        
        try:
            print("1. Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="domcontentloaded")
            time.sleep(3)
            
            print("1b. Controleren op cookie-pop-up...")
            cookie_selectors = [
                'button:has-text("Akkoord")', 
                'button:has-text("Accepteren")', 
                'button:has-text("Accept")', 
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'
            ]
            
            for selector in cookie_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        print(f"Cookieknop gevonden ({selector}), klikken...")
                        btn.click()
                        time.sleep(3)
                        break
                except:
                    continue

            print("2. Inloggegevens invullen...")
            email_field = None
            password_field = None
            
            locators_email = ['input[type="email"]', 'input[name*="mail"]', 'input[placeholder*="mail"]', 'input[placeholder*="username"]']
            for loc in locators_email:
                if page.locator(loc).first.is_visible(timeout=1000):
                    email_field = page.locator(loc).first
                    break
            
            if not email_field:
                print("Velden niet direct zichtbaar, zoeken in sub-frames...")
                for frame in page.frames:
                    for loc in locators_email:
                        try:
                            if frame.locator(loc).first.is_visible(timeout=1000):
                                email_field = frame.locator(loc).first
                                password_field = frame.locator('input[type="password"]').first
                                print("Inlogvelden succesvol gevonden in sub-frame!")
                                break
                        except:
                            continue
                    if email_field:
                        break

            if not email_field:
                print("Fallback: Velden dwingen op de hoofdpagina...")
                email_field = page.locator('input[type="email"], input[name*="username"]').first
                password_field = page.locator('input[type="password"]').first

            email_field.fill(SCORITO_USERNAME)
            if password_field:
                password_field.fill(SCORITO_PASSWORD)
            else:
                page.locator('input[type="password"]').first.fill(SCORITO_PASSWORD)
            
            print("3. Klikken op de inlogknop...")
            inlog_knop = page.locator('button[type="submit"], button:has-text("Inloggen"), button:has-text("Log in"), .login-button').first
            inlog_knop.click()
            
            print("4. Wachten op het dashboard...")
            page.wait_for_url("**/apps/**", timeout=25000)
            
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
                        "punten": points
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
            
            # --- GARANDEER SCREENSHOT BIJ CRASH ---
            try:
                page.screenshot(path="error_screenshot.png", full_page=True)
                print("📸 Screenshot succesvol opgeslagen als error_screenshot.png!")
            except Exception as img_err:
                print(f"Kon geen screenshot maken: {img_err}")
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
