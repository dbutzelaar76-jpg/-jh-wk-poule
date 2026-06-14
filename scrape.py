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
        print("1. Starten van de gecamoufleerde browseromgeving...")
        user_data_dir = "/tmp/playwright_user_data"
        
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="nl-NL",
            timezone_id="Europe/Amsterdam",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            print("2. Navigeren naar de Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="domcontentloaded", timeout=45000)
            time.sleep(4)
            
            print("3. Controleren op cookie-pop-up...")
            cookie_button = page.locator('button:has-text("Akkoord"), button:has-text("Accepteren"), button:has-text("Accept"), #CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll').first
            try:
                if cookie_button.is_visible(timeout=5000):
                    print("Cookie-pop-up gevonden, we klikken op akkoord...")
                    cookie_button.click()
                    print("Wachten tot de iframe-omgeving achter de pop-up warmdraait...")
                    time.sleep(6)
            except:
                print("Geen cookieknop gedetecteerd of nodig.")

            try:
                page.screenshot(path="voor_inloggen.png", full_page=True)
                print("📸 Schermvlak vooraf opgeslagen als 'voor_inloggen.png'")
            except:
                pass

            print("4. Zoeken naar de inlogvelden (Zowel hoofdscherm als Iframe)...")
            email_field = None
            password_field = None
            target_context = page

            # We controleren eerst of er stiekem iframes zijn geladen na de cookie-akkoord
            if len(page.frames) > 1:
                print(f"Iframe gedetecteerd ({len(page.frames)} frames actief). We switchen naar de juiste context...")
                for frame in page.frames:
                    if "scorito" in frame.url or "account" in frame.url or "app" in frame.url:
                        target_context = frame
                        print(f"🎯 Inlog-iframe geïdentificeerd: {frame.url}")
                        break
                if target_context == page:
                    print("Geen specifieke URL-match, we gebruiken de eerste sub-frame.")
                    target_context = page.main_frame.child_frames[0] if page.main_frame.child_frames else page

            # Velden lokaliseren binnen de juiste context
            email_field = target_context.locator('input[type="email"], input[type="text"], [placeholder*="mail"], [placeholder*="Mail"]').first
            password_field = target_context.locator('input[type="password"], [placeholder*="achtwoord"], [placeholder*="assword"]').first

            print("5. Gegevens invoeren...")
            email_field.wait_for(state="attached", timeout=20000)
            email_field.fill(SCORITO_USERNAME)
            password_field.fill(SCORITO_PASSWORD)
            time.sleep(1)
            
            print("6. Klikken op de inlogknop...")
            inlog_knop = target_context.locator('button[type="submit"], button:has-text("Inloggen"), .login-button, [class*="submit"]').first
            inlog_knop.click()
            
            print("7. Wachten op succesvolle login...")
            page.wait_for_url("**/apps/**", timeout=35000)
            print("Inloggen geslaagd!")
            time.sleep(3)
            
            print("8. Navigeren naar de poule-ranking...")
            page.goto(POULE_URL, wait_until="networkidle")
            time.sleep(5)
            
            try:
                page.screenshot(path="success_screenshot.png", full_page=True)
                print("📸 Stand-scherm vastgelegd als success_screenshot.png")
            except:
                pass
            
            print("9. Data verzamelen uit de pagina...")
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
                print("⚠️ Waarschuwing: Tabel geladen, maar kon geen regels parsen naar JSON.")

        except Exception as e:
            print(f"\n❌ ER IS IETS MISGEGAAN TIJDENS HET SCRAPEN: {e}")
            try:
                page.screenshot(path="error_screenshot.png", full_page=True)
                print("📸 Fout-screenshot succesvol opgeslagen!")
            except:
                pass
            raise e
            
        finally:
            context.close()

if __name__ == "__main__":
    scrape_scorito()
