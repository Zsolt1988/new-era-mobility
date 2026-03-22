import json
import csv
import os
import re

def derive_simple_color(color):
    if not color or color == "—": return "n.a."
    color = color.lower()
    mapping = {
        "schwarz": ["schwarz", "black", "obsidian", "nero", "midnight"],
        "weiß": ["weiß", "weiss", "white", "polar", "bianco", "snow"],
        "silber": ["silber", "silver", "metallic", "grey", "grau", "platinum"],
        "blau": ["blau", "blue", "indigo", "ocean", "deep sea"],
        "rot": ["rot", "red", "magma", "fire"],
        "grün": ["grün", "gruen", "green", "emerald", "sage"],
        "gelb": ["gelb", "yellow", "gold"],
    }
    for simple, keywords in mapping.items():
        if any(kw in color for kw in keywords):
            return simple.capitalize()
    return "Andere"

def export_to_csv(json_file, csv_output):
    if not os.path.exists(json_file):
        print(f"Error: {json_file} does not exist.")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Standard headers for "Aktive_Sammlung"
    headers = [
        "Nummer", "Fahrzeug-Link", "Bild_Gallery1", "Hersteller", "Modell", "Ausführung", "Kraftstoff", 
        "Getriebe", "PS", "KM Stand", "Erstzulassung", "Farbe", 
        "Farbe_Einfach", "Sofortkauf-Preis", "Link", "Baujahr"
    ]

    rows = []
    
    # Check if we have multiple cars or just one
    cars = data.get('cars', [])
    if not cars and 'title' in data: # Single car fallback
        cars = [data]

    for car in cars:
        # Extract and format fields
        hersteller = car.get('carBrand', 'n.a.')
        full_model = car.get('carModel', car.get('title', 'n.a.'))
        
        # Try to split Model and Ausführung (Execution)
        # Often "Seal EV Comfort" -> Model: Seal, Ausführung: Comfort
        modell = full_model
        ausfuehrung = car.get('carExecution', 'n.a.')
        if ausfuehrung == 'n.a.':
            # Simple heuristic: look for common execution keywords or the word after the model name
            # For BYD Seal, usually the word after 'Seal' is the execution
            parts = full_model.split(' ')
            if len(parts) > 2:
                modell = parts[0] + " " + parts[1] # e.g. "BYD Seal"
                ausfuehrung = " ".join(parts[2:])
            elif len(parts) > 1:
                modell = parts[0]
                ausfuehrung = parts[1]

        kraftstoff = car.get('carFuel', car.get('carFuelType', 'n.a.'))
        getriebe = car.get('carDrive', car.get('carTransmission', 'n.a.'))
        
        # Power conversion: kW to PS (e.g. 170 kW -> 231 PS)
        power_raw = car.get('carPower', '0')
        ps = "n.a."
        if power_raw:
            try:
                # If it's already a string with PS (e.g. "170 KW / 231 PS")
                ps_match = re.search(r'(\d+)\s*PS', str(car.get('specs', {}).get('Leistung', '')))
                if ps_match:
                    ps = ps_match.group(1)
                else:
                    kw = int(re.sub(r'[^\d]', '', str(power_raw)))
                    ps = str(round(kw * 1.36)) if kw > 0 else "n.a."
            except:
                ps = str(power_raw)

        km_stand = car.get('carMileage', '0')
        erstzulassung = car.get('carRegistration', 'n.a.')
        
        farbe = car.get('carColor', 'n.a.')
        farbe_einfach = derive_simple_color(farbe)
        
        # Price: remove non-numeric
        price_raw = car.get('carPrice', car.get('price', '0'))
        sofortkauf_preis = re.sub(r'[^\d]', '', str(price_raw)) if price_raw else "0"
        
        link = car.get('source', data.get('source', 'n.a.'))
        
        # Baujahr: usually last 4 digits of registration or year part
        baujahr = "n.a."
        if erstzulassung and erstzulassung != "n.a.":
            year_match = re.search(r'(?:19|20)\d{2}', erstzulassung)
            if year_match:
                baujahr = year_match.group(0)

        nummer = car.get('carNumber', '')
        fahrzeug_link = car.get('source', car.get('link', ''))

        rows.append({
            "Nummer": nummer,
            "Fahrzeug-Link": fahrzeug_link,
            "Bild_Gallery1": car.get('carImage', ''),
            "Hersteller": hersteller,
            "Modell": modell,
            "Ausführung": ausfuehrung,
            "Kraftstoff": kraftstoff,
            "Getriebe": getriebe,
            "PS": ps,
            "KM Stand": km_stand,
            "Erstzulassung": erstzulassung,
            "Farbe": farbe,
            "Farbe_Einfach": farbe_einfach,
            "Sofortkauf-Preis": sofortkauf_preis,
            "Link": link,
            "Baujahr": baujahr
        })

    with open(csv_output, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, delimiter=';') # Semicolon common in German locale CSV
        writer.writeheader()
        writer.writerows(rows)

    print(f"Successfully exported data to {csv_output}")

if __name__ == "__main__":
    export_to_csv('extracted_cars.json', 'aktive_sammlung.csv')
