import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
POULE_URL = "https://www.scorito.com/footballtournament/ranking/301/1036045" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld!")
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
            
            print("1b. Controleren op cookie-pop-up...")
            cookie_button = page.locator('button:has-text("Akkoord"), button:has-text("Accepteren"), button:has-text("Accept"), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll').first
            try:
                if cookie_button.is_visible(timeout=5000):
                    print("Cookie-pop-up gevonden, we klikken op akkoord...")
                    cookie_button.click()
                    time.sleep(5) 
            except:
                print("Geen actieve cookieknop gevonden.")

            print("2. Zoeken naar de juiste Scorito inlog-iframe...")
            # We wachten tot er een iframe op de pagina verschijnt
            page.wait_for_selector('iframe', timeout=20000)
            
            # We zoeken specifiek de iframe die de inlog-app bevat
            login_frame = None
            for frame in page.frames:
                if "scorito" in frame.url or "app" in frame.url or "account" in frame.url:
                    login_frame = frame
                    print(f"🎯 Juiste iframe gevonden! URL: {frame.url}")
                    break
            
            # Als hij hem niet via de URL herkent, pakken we de hoofd-iframe
            if not login_frame:
                print("Geen specifieke URL-match, we gebruiken de eerste beschikbare iframe.")
                login_frame = page.main_frame.child_frames[0] if page.main_frame.child_frames else page

            print("3. Inloggegevens invullen binnen de iframe...")
            # We zoeken de velden nu direct binnen de gevonden frame-context
            email_field = login_frame.locator('input[type="email"], input[type="text"], [placeholder*="mail"], [placeholder*="Mail"]').first
            password_field = login_frame.locator('input[type="password"], [placeholder*="achtwoord"], [placeholder*="assword"]').first
            
            # We wachten tot het e-mailveld daadwerkelijk geladen en klaar is in de iframe
            email_field.wait_for(state="attached", timeout=20000)
            
            email_field.fill(SCORITO_USERNAME)
            password_field.fill(SCORITO_PASSWORD)
            time.sleep(1)
            
            print("4. Klikken op de inlogknop binnen de iframe...")
            inlog_knop = login_frame.locator('button[type="submit"], button:has-text("Inloggen"), .login-button, [class*="submit"]').first
            inlog_knop.click()
            
            print("5. Wachten op succesvolle login en doorsturen naar apps...")
            page.wait_for_url("**/apps/**", timeout=35000)
            print("Inloggen geslaagd!")
            time.sleep(3)
            
            print("6. Navigeren naar de juiste poule-ranking...")
            page.goto(POULE_URL, wait_until="networkidle")
            time.sleep(5)
            
            try:
                page.screenshot(path="success_screenshot.png", full_page=True)
                print("📸 Stand-scherm vastgelegd als success_screenshot.png")
            except:
                pass
            
            print("7. Data verzamelen uit de pagina...")
            stand_data = []
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
