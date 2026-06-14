import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
POULE_URL = "https://www.scorito.com/footballtournament/ranking/301/1036045" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets zijn niet ingesteld!")
        return

    with sync_playwright() as p:
        print("1. Starten van een zware desktop browseromgeving...")
        browser = p.chromium.launch(headless=True)
        
        # We zetten de browser op een stabiele desktop Windows-omgeving
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            print("2. Direct navigeren naar de Poule URL (om inlog-redirect te triggeren)...")
            page.goto(POULE_URL, wait_until="load", timeout=60000)
            time.sleep(5)
            
            print("3. Controleren op cookie-banner...")
            # We klikken de cookiebanner weg als die er staat
            try:
                cookie_btn = page.locator("button:has-text('Accepteren'), button:has-text('Akkoord'), #accept-choices").first
                if cookie_btn.is_visible(timeout=3000):
                    cookie_btn.click()
                    print("✅ Cookie-knop aangeklikt.")
                    time.sleep(3)
            except:
                print("Geen cookie-banner gedetecteerd of al verdwenen.")

            # Maak een screenshot om te zien waar we nu zijn beland
            page.screenshot(path="01_na_laden.png")

            print("4. Wachten tot de inlogvelden verschijnen...")
            # Scorito gebruikt dynamic rendering. We wachten tot er ergens een inputveld opduikt
            page.wait_for_selector("input", timeout=20000)
            
            inputs = page.locator("input").all()
            print(f"Aantal invoervelden gevonden op scherm: {len(inputs)}")
            
            email_ingevuld = False
            wachtwoord_ingevuld = False
            
            # We lopen door alle velden heen en vullen ze op basis van attributen in
            for field in inputs:
                input_type = field.get_attribute("type") or ""
                placeholder = field.get_attribute("placeholder") or ""
                name_attr = field.get_attribute("name") or ""
                
                if "email" in input_type or "text" in input_type or "username" in name_attr.lower() or "mail" in placeholder.lower():
                    if not email_ingevuld:
                        field.click()
                        field.fill(SCORITO_USERNAME)
                        email_ingevuld = True
                        print("✅ E-mailveld ingevuld.")
                elif "password" in input_type or "achtwoord" in placeholder.lower() or "password" in name_attr.lower():
                    if not wachtwoord_ingevuld:
                        field.click()
                        field.fill(SCORITO_PASSWORD)
                        wachtwoord_ingevuld = True
                        print("✅ Wachtwoordveld ingevuld.")

            # Ultieme nood-fallback als de automatische loop ze miste
            if not email_ingevuld:
                print("Invoervelden niet via loop herkend, we proberen directe selectors...")
                page.locator("input[type='email'], input[name='username']").first.fill(SCORITO_USERNAME)
                page.locator("input[type='password'], input[name='password']").first.fill(SCORITO_PASSWORD)
                print("✅ Fallback invoer uitgevoerd.")

            page.screenshot(path="02_velden_ingevuld.png")

            print("5. Inlogknop opzoeken en aanklikken...")
            # Zoek de knop die het formulier verzendt
            login_btn = page.locator("button[type='submit'], button:has-text('Inloggen'), .login-button").first
            login_btn.click()
            
            print("6. Wachten tot de stand-tabel in beeld komt...")
            # Omdat we gestart zijn vanaf de poule-URL, stuurt Scorito ons na inloggen direct hiernaartoe terug
            time.sleep(10) # Geef de single-page app de tijd om de ranglijst op te bouwen
            
            page.screenshot(path="03_stand_geladen.png")

            print("7. De stand uitlezen uit de pagina...")
            stand_data = []
            
            # Scorito's structuur: we zoeken naar tabelrijen of elementen met klassen zoals 'row' of 'item'
            elements = page.locator("tr, [class*='poule-ranking'], [class*='row']").all()
            
            for el in elements:
                try:
                    text = el.inner_text().strip()
                    if text and "\n" in text:
                        parts = text.split("\n")
                        # Controleren of de regel begint met een ranking-getal (bijv "1" of "1.")
                        if len(parts) >= 3 and parts[0].replace('.', '').strip().isdigit():
                            pos = parts[0].replace('.', '').strip()
                            naam = parts[1].strip()
                            punten = parts[2].strip()
                            
                            if not any(d['naam'] == naam for d in stand_data):
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
                print(f"✅ SUCCES: {len(stand_data)} deelnemers opgeslagen in stand.json!")
            else:
                print("⚠️ De pagina is geladen, maar er konden geen tabelrijen worden omgezet.")
                # We dumpen een stukje tekst als diagnose om te zien wat er wél staat
                body_text = page.locator("body").inner_text()[:1000]
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump({"error": "Tabel niet herkend", "preview": body_text}, f, indent=4)

        except Exception as e:
            print(f"❌ CRASH TIJDENS SCRAPEN: {e}")
            try:
                page.screenshot(path="04_crash_moment.png")
            except:
                pass
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
