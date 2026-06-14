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
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="nl-NL"
        )
        
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
        
        try:
            print("1. Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="networkidle", timeout=45000)
            time.sleep(3)
            
            print("1b. Controleren op cookie-pop-up...")
            cookie_button = page.locator('button:has-text("Akkoord"), button:has-text("Accepteren"), button:has-text("Accept"), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll').first
            try:
                if cookie_button.is_visible(timeout=5000):
                    print("Cookie-pop-up gevonden, we klikken op akkoord...")
                    cookie_button.click()
                    time.sleep(4) # Geef de iPhone-simulator de tijd om in te laden na de cookies
            except:
                print("Geen actieve cookieknop gevonden.")

            # --- CLAUDE'S EXTRA VERZOEK: SCREENSHOT VÓÓR HET INLOGGEN ---
            try:
                page.screenshot(path="voor_inloggen.png", full_page=True)
                print("📸 Screenshot VÓÓR inloggen opgeslagen als 'voor_inloggen.png'")
            except Exception as e_img:
                print(f"Kon screenshot vooraf niet maken: {e_img}")

            print("2. Inloggegevens invullen BINNEN de iframe (Claude's methode)...")
            # We richten ons specifiek op de eerste beschikbare iframe op de pagina
            frame = page.frame_locator('iframe').first
            
            email_field = frame.locator('input[type="email"], input[type="text"], input[name*="username"]').first
            password_field = frame.locator('input[type="password"]').first
            
            # Wacht tot het e-mailveld IN de iframe zichtbaar wordt
            email_field.wait_for(state="visible", timeout=20000)
            
            print("Velden gevonden in de iframe! Gegevens invoeren...")
            email_field.fill(SCORITO_USERNAME)
            password_field.fill(SCORITO_PASSWORD)
            time.sleep(1)
            
            print("3. Klikken op de inlogknop binnen de iframe...")
            inlog_knop = frame.locator('button[type="submit"], button:has-text("Inloggen"), .login-button').first
            inlog_knop.click()
            
            print("4. Wachten op succesvolle login (navigatie naar apps)...")
            page.wait_for_url("**/apps/**", timeout=30000)
            print("Inloggen geslaagd!")
            time.sleep(2)
            
            print("5. Navigeren naar de juiste poule-ranking...")
            page.goto(POULE_URL, wait_until="networkidle")
            time.sleep(5)
            
            # Screenshot als het gelukt is om de stand te laden
            try:
                page.screenshot(path="success_screenshot.png", full_page=True)
                print("📸 Stand-scherm vastgelegd als success_screenshot.png")
            except:
                pass
            
            print("6. Data verzamelen uit de pagina...")
            stand_data = []
            
            # We scannen breed alle rijen in de ranking tabel (zowel op pagina als in eventuele frames)
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
                print("⚠️ Waarschuwing: Pagina geladen, maar kon geen rijen omzetten naar JSON.")

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
