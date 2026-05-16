import json
import os
import re
import time
from playwright.sync_api import sync_playwright

# Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_PATH = os.path.join(BASE_DIR, 'sold_archive.json')
COOKIE_PATH = os.path.join(BASE_DIR, 'bca_cookies.json')

def scrape_prices():
    if not os.path.exists(ARCHIVE_PATH):
        print("Archive not found.")
        return

    with open(ARCHIVE_PATH, 'r', encoding='utf-8') as f:
        archive = json.load(f)

    # Filter Fahrzeuge ohne Verkaufspreis
    cars_to_scrape = [c for c in archive if not c.get('verkaufspreis') or c.get('verkaufspreis') == 0]
    
    if not cars_to_scrape:
        print("Updated 0 prices. Alle Fahrzeuge haben bereits einen Preis.")
        return

    updated_count = 0
    
    with sync_playwright() as p:
        # Browser starten - Headless=False ist wichtig für den Login
        browser = p.chromium.launch(headless=False)
        
        # Kontext mit Cookies laden, falls vorhanden
        if os.path.exists(COOKIE_PATH):
            with open(COOKIE_PATH, 'r') as f:
                cookies = json.load(f)
            context = browser.new_context(storage_state={"cookies": cookies})
        else:
            context = browser.new_context()

        page = context.new_page()

        # Check ob wir eingeloggt sind
        print("Prüfe Login-Status...")
        page.goto("https://de.bca-europe.com/Buyer/Login")
        
        # Wenn wir nicht direkt zum Dashboard kommen, warten wir auf den Login
        if "Login" in page.url:
            print("Bitte logge dich jetzt manuell bei BCA ein...")
            print("Das Script wartet bis du eingeloggt bist (max. 5 Minuten)...")
            try:
                # Warten bis ein Element erscheint, das nur nach Login sichtbar ist (z.B. Abmelden-Link)
                page.wait_for_selector("text=Abmelden", timeout=300000) 
                print("Login erfolgreich!")
                # Speichere Session-Status
                state = context.storage_state()
                with open(COOKIE_PATH, 'w') as f:
                    json.dump(state['cookies'], f)
            except Exception as e:
                print("Login-Timeout oder Fehler. Breche ab.")
                browser.close()
                return

        for car in cars_to_scrape:
            link = car.get('Link')
            if not link: continue
            
            if not link.startswith('http'):
                link = "https://" + link
            
            try:
                print(f"Prüfe: {car.get('name', car.get('id'))} -> {link}")
                page.goto(link, timeout=30000)
                time.sleep(2) # Kurz warten für dynamische Inhalte
                
                # Wir suchen im gesamten Text der Seite nach Preis-Informationen
                body_text = page.inner_text("body")
                
                # Suche nach Mustern: "Netto", "Brutto", "Verkaufspreis", "Höchstgebot"
                # Wir suchen nach dem Betrag in der Nähe dieser Wörter
                
                found_price = 0
                
                # Regex für Euro-Beträge (z.B. 25.400,00 oder 25400)
                price_regex = r'(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*€'
                
                # Extrahiere alle Preis-Matches
                matches = re.finditer(price_regex, body_text)
                
                # Priorität: Wir suchen die Zeile, die "Netto" oder "Brutto" enthält
                lines = body_text.split('\n')
                for line in lines:
                    if "€" in line and any(k in line.lower() for k in ["höchstgebot", "verkaufspreis", "zuschlag", "preis"]):
                        p_match = re.search(price_regex, line)
                        if p_match:
                            val_str = p_match.group(1).replace('.', '').replace(',', '.')
                            val = float(val_str)
                            
                            # Wenn "Netto" in der Zeile steht, rechnen wir auf Brutto (+19% DE) hoch
                            # (Der User möchte den Brutto-Einkaufspreis als Basis)
                            if "netto" in line.lower():
                                print(f"Netto-Preis erkannt: {val} -> Rechne +19% MwSt")
                                val = val * 1.19
                            elif "brutto" in line.lower():
                                print(f"Brutto-Preis erkannt: {val}")
                            
                            found_price = val
                            break
                
                if found_price > 0:
                    car['verkaufspreis'] = round(found_price, 2)
                    updated_count += 1
                    print(f"-> Erfolg: {found_price} €")
                else:
                    print("-> Kein Preis auf der Seite gefunden.")
                    
            except Exception as e:
                print(f"Fehler bei ID {car['id']}: {e}")

        browser.close()

    # Ergebnisse speichern
    if updated_count > 0:
        with open(ARCHIVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(archive, f, indent=4, ensure_ascii=False)

    print(f"Updated {updated_count} prices.")

if __name__ == "__main__":
    scrape_prices()
