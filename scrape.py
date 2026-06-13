import os
import json
import time
from playwright.sync_api import sync_playwright

SCORITO_USERNAME = os.environ.get("SCORITO_USER")
SCORITO_PASSWORD = os.environ.get("SCORITO_PASS")
# Jouw poule staat vast op regel 8
POULE_URL = "https://www.scorito.com/apps/league/index.html?subleagueid=1036045" 

def scrape_scorito():
    if not SCORITO_USERNAME or not SCORITO_PASSWORD:
        print("❌ FOUT: GitHub Secrets (SCORITO_USER of SCORITO_PASS) zijn niet ingesteld of leeg!")
        return

    with sync_playwright() as p:
        # We dwingen een grote desktop browser af en schakelen de mobiele emulatie uit
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="nl-NL",
            is_mobile=False,
            has_touch=False
        )
        page = context.new_page()
        
        try:
            print("1. Navigeren naar Scorito inlogpagina...")
            page.goto("https://www.scorito.com/account/login", wait_until="networkidle")
            time.sleep(3)
            
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
            # We zoeken breed naar invoervelden, mocht hij onverhoopt toch de app tonen
            email_field = page.locator('input[type="email"], input[name*="mail"], input[type="text"]').first
            password_field = page.locator('input[type="password"]').first
            
            email_field.wait_for(state="visible", timeout=15000)
            email_field.fill(SCORITO_USERNAME)
            password_field.fill(SCORITO_PASSWORD)
            
            print("3. Klikken op de inlogknop...")
            inlog_knop = page.locator('button[type="submit"], button:has-text("Inloggen"), .login-button').first
            inlog_knop.click()
            
            print("4. Wachten op het dashboard...")
            page.wait_for_url("**/apps/**", timeout=25000)
            
            print("5. Succesvol ingelogd! Navigeren naar poule...")
            page.goto(POULE_URL, wait_until="networkidle")
            time.sleep(5) # Geef de app in het telefoonscherm de tijd om op te starten
            
            print("6. Stand-data lokaliseren...")
            stand_data = []
            
            # Strategie 1: De tabel die we op je screenshot zien uitlezen (divs in plaats van tr/td)
            # We zoeken naar elementen die de tekst bevatten, of we pakken de hoofdcontainer
            page.wait_for_selector("body", timeout=10000)
            
            # We trekken alle tekst uit de pagina om te kijken of we de namen zien
            page_text = page.content()
            
            # We zoeken naar de list-items of divs die de namen bevatten
            # Omdat de stand in een mobiele lijst staat, zoeken we naar tekstblokken met getallen en namen
            items = page.locator('div[class*="item"], div[class*="row"], tr').all()
            
            print(f"Systeemelementen gevonden om te scannen: {len(items)}")
            
            # Alternatieve robuuste methode: We pakken de ruwe tekst als we de tabel niet direct als HTML kunnen ontleden
            # Voor nu proberen we de structuur te ontleden via algemene tekstregels
            lines = page.locator('div').all_inner_texts()
            
            # Filter de regels om een mooie JSON op te bouwen
            clean_rows = []
            for line in lines:
                if line and "\n" in line:
                    parts = line.split("\n")
                    # Een geldige rij heeft vaak: positie, naam, punten (bijv: ["31", "Johan", "90", "90"])
                    if len(parts) >= 3 and parts[0].isdigit():
                        pos = parts[0]
                        naam = parts[1]
                        punten = parts[2]
                        # Voorkom dubbele invoer
                        if {"positie": pos, "naam": naam, "punten": punten} not in clean_rows:
                            clean_rows.append({"positie": pos, "naam": naam, "punten": punten})
            
            if clean_rows:
                stand_data = clean_rows
            else:
                # Fallback: Mocht de desktopversie wél geladen zijn, lees de normale tabel uit
                rows = page.query_selector_all("table tr")
                for row in rows:
                    cells = row.query_selector_all("td")
                    if len(cells) >= 3:
                        stand_data.append({
                            "positie": cells[0].inner_text().strip(),
                            "naam": cells[1].inner_text().strip(),
                            "punten": cells[2].inner_text().strip()
                        })

            if stand_data:
                # Sorteer even netjes op positie
                with open("stand.json", "w", encoding="utf-8") as f:
                    json.dump(stand_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Stand succesvol opgeslagen! {len(stand_data)} deelnemers verwerkt.")
            else:
                print("⚠️ Waarschuwing: Kon de stand niet direct uit de mobiele interface trekken.")
                # We forceren een fout zodat we de screenshot kunnen bekijken om de exacte HTML-tags te zien
                raise Exception("Tabel-structuur niet herkend.")

        except Exception as e:
            print(f"\n❌ ER IS IETS MISGEGAAN TIJDENS HET SCRAPEN: {e}")
            try:
                page.screenshot(path="error_screenshot.png", full_page=True)
                print("📸 Screenshot succesvol opgeslagen!")
            except:
                pass
            raise e
            
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_scorito()
