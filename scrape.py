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
        
        # We starten een schone, realistische Chromium browser
        browser = p.chromium.launch(headless=True)
        
        # Cruciaal: We bootsen een exacte Windows 11 Desktop na om "witte schermen" (mobiele scripts) te blokkeren
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="nl-NL",
            timezone_id="Europe/Amsterdam"
        )
        
        page = context.new_page()
        
        try:
            print("2. Navigeren naar de Scorito inlogpagina...")
            # We wachten tot het netwerk minimaal 500ms volledig stil is (alles ingeladen)
            page.goto("https://www.scorito.com/account/login", wait_until="networkidle", timeout=60000)
            
            # Geef zware React-scripts de tijd om te spinnen
            print("Ademruimte geven voor het bouwen van de pagina...")
            time.sleep(8)
            
            print("3. Controleren op cookie-banner...")
            # Scorito blokkeert soms invoer als de cookie-overlay eroverheen staat
            for btn_text in ["Akkoord", "Accepteren", "Accept", "Alle toestaan"]:
                cookie_btn = page.get_by_role("button", name=btn_text, exact=False).first
                if cookie_btn.is_visible():
                    cookie_btn.click()
                    print(f"Cookie-knop '{btn_text}' aangeklikt.")
                    time.sleep(3)
                    break

            # Sla een controle-screenshot op om te zien of het witte scherm nu weg is
            page.screenshot(path="01_inlogscherm.png")
            
            print("4. Zoeken naar de invoervelden...")
            # We zoeken heel specifiek op invoervelden, ongeacht hun exacte ID's
            inputs = page.locator("input").all()
            print(f"Aantal invoervelden gevonden op scherm: {len(inputs)}")
            
            # We vullen de velden in op basis van hun type of positie
            email_ingevuld = False
            wachtwoord_ingevuld = False
            
            for field in inputs:
                input_type = field.get_attribute("type") or ""
                placeholder = field.get_attribute("placeholder") or ""
                
                if "email" in input_type or "text" in input_type or "mail" in placeholder.lower():
                    if not email_ingevuld:
                        field.fill(SCORITO_USERNAME)
                        email_ingevuld = True
                        print("✅ E-mailveld ingevuld.")
                elif "password" in input_type or "achtwoord" in placeholder.lower():
                    if not wachtwoord_ingevuld:
                        field.fill(SCORITO_PASSWORD)
                        wachtwoord_ingevuld = True
                        print("✅ Wachtwoordveld ingevuld.")

            # Ultieme fallback als de loop hierboven de velden niet kon matchen
            if not email_ingevuld:
                page.locator("input[type='email']").fill(SCORITO_USERNAME)
                page.locator("input[type='password']").fill(SCORITO_PASSWORD)
                print("Fallback invoer gebruikt.")

            time.sleep(1)
            page.screenshot(path="02_ingevuld.png")

            print("5. Klikken op de inlogknop...")
            # Zoek de hoofd-inlogknop
            login_btn = page.locator("button[type='submit'], button:has-text('Inloggen'), .login-button").first
            login_btn.click()
            
            print("6. Wachten op het dashboard...")
            # We wachten tot de URL verandert naar de applicatie-omgeving
            try:
                page.wait_for_url("**/apps/**", timeout=20000)
                print("Inloggen succesvol! Dashboard bereikt.")
            except:
                print("Waarschuwing: URL-wijziging niet gedetecteerd, we proberen toch door te gaan...")
            
            time.sleep(5)

            print("7. Direct doorschakelen naar de Poule Ranking...")
            page.goto(POULE_URL, wait_until="networkidle", timeout=60000)
            time.sleep(7) # Geef de tabel de tijd om in te laden
            
            page.screenshot(path="03_poule_stand.png")

            print("8. De stand uitlezen...")
            stand_data = []
            
            # We zoeken naar tabelrijen (Scorito gebruikt vaak 'tr' of div's met klasse 'row')
            rows = page.locator("tr, [class*='row'], [class*='item']").all()
            print(f"Aantal potentiële datarijen op het scherm: {len(rows)}")
            
            for row in rows:
                try:
                    text = row.inner_text().strip()
                    if text and "\n" in text:
                        parts = text.split("\n")
                        # Een geldige regel begint met een positiecijfer (bijv. "1." of "1")
                        if len(parts) >= 3 and parts[0].replace('.', '').strip().isdigit():
                            pos = parts[0].replace('.', '').strip()
                            naam = parts[1].strip()
                            punten = parts[2].strip()
                            
                            # Voorkom dubbele regels
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
                print("⚠️ Waarschuwing: Pagina geladen, maar de tabelstructuur kon niet worden uitgelezen.")
                # Als back-up slaan we de ruwe paginatekst op om te zien wat er staat
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump({"error": "Tabel niet gevonden", "html": page.content()[:2000]}, f)

        except Exception as e:
            print(f"❌ FOUT TIJDENS SCRAPEN: {e}")
            try:
                page.screenshot(path="04_error.png")
            except:
                pass
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
