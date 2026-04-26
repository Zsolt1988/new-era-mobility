import sys
import json
import re
import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def clean_value(val):
    if not val: return ""
    return val.strip().replace("\u2013", "-").replace("\u00a0", " ")

def parse_car_details(text):
    car_data = {
        "title": "Unbekanntes Fahrzeug",
        "carBrand": "",
        "carModel": "",
        "price": "N/A",
        "price_status": "unknown",
        "specs": {},
        "features": {
            "Interieur & Komfort": [],
            "Technologie & Assistenz": [],
            "Sicherheit": [],
            "Exterieur": [],
            "Weitere Merkmale": []
        },
        "schäden": []
    }

    # Format Detection
    is_expertise = "Expertise" in text[:500] or "TÜV SÜD Auto Partner" in text
    is_zustand = "Zustandsbericht" in text[:500] or "Fahrzeugdetails" in text[:500]
    
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 1. Extract Title
    manufacturer = ""
    model = ""
    
    # Try to find explicit labels first
    for i, line in enumerate(lines[:40]):
        if line.startswith("Hersteller:"):
            manufacturer = line.replace("Hersteller:", "").split("Modell:")[0].strip()
            if "Modell:" in line:
                model = line.split("Modell:")[1].strip()
        elif "Hersteller" in line and not manufacturer:
            m_match = re.search(r'Hersteller[:\s]+([A-Za-z]+)', line)
            if m_match:
                manufacturer = m_match.group(1).strip()
        
        if "Modell" in line and not model:
            m_match = re.search(r'Modell[:\s]+([A-Za-z0-9\-\s]+)', line)
            if m_match:
                model = m_match.group(1).strip()

    if is_expertise:
        if not model:
            for i, line in enumerate(lines):
                if line.startswith("Hersteller / Typ / Modell"):
                    if i + 1 < len(lines):
                        model = lines[i + 1]
                    break
    elif is_zustand:
        title_parts = []
        for line in lines:
            if line.startswith("Kennzeichen") and "Modell" in line:
                parts = line.split("Modell")
                if len(parts) > 1:
                    title_parts.append(parts[1].strip())
            elif "Edition" in line and len(line) < 30:
                title_parts.append(line.strip())
        if title_parts:
            model = " ".join(title_parts)
    
    if manufacturer and model:
        # Clean up if model already contains manufacturer
        if manufacturer.lower() in model.lower():
            car_data["title"] = model
        else:
            car_data["title"] = f"{manufacturer} {model}"
    elif model:
        car_data["title"] = model
    
    if car_data["title"] == "Unbekanntes Fahrzeug" or not car_data["carBrand"]:
        # Fallback Title & Brand Search
        brands = ["Porsche", "Volkswagen", "VW", "Audi", "BMW", "Mercedes", "BYD", "Tesla", "Renault", "Ford", "Opel", "Skoda", "Seat", "Hyundai", "Kia", "Toyota", "Fiat", "Mazda", "Volvo", "Cupra"]
        blacklist = ["EuroShop", "nvk", "Seite", "Protokoll", "Expertise", "Zustandsbericht"]
        
        found_brand = ""
        for line in lines[:60]:
            # Always look for brand names even in "blacklisted" lines
            for b in brands:
                if f" {b.lower()} " in f" {line.lower()} " or line.lower().startswith(b.lower()) or f"-{b.lower()}" in line.lower():
                    found_brand = b
                    break
            
            if found_brand:
                car_data["carBrand"] = found_brand
                if car_data["title"] == "Unbekanntes Fahrzeug" and not any(bl.lower() in line.lower() for bl in blacklist):
                    car_data["title"] = line
                if car_data["carBrand"]: break

    # Look for Ausstattungsvariante (Execution)
    variant_match = re.search(r'Ausstattungsvariante\s+([A-Za-z0-9\-\s]+?)(?:\n|$)', text, re.IGNORECASE)
    if variant_match:
        variant = variant_match.group(1).strip()
        car_data["carExecution"] = variant

    # Assemble Final Title if still unknown
    if car_data["title"] == "Unbekanntes Fahrzeug" and car_data["carBrand"]:
        car_data["title"] = car_data["carBrand"]
        if car_data.get("carExecution"):
            car_data["title"] += " " + car_data["carExecution"]
    elif car_data.get("carExecution") and car_data["carExecution"].lower() not in car_data["title"].lower():
        # Append execution if not already in title
        car_data["title"] = f"{car_data['title']} {car_data['carExecution']}"

    # 2. Extract Price (Look for Wiederbeschaffungswert or standard price)
    price_match = re.search(r'(?:Wiederbeschaffungswert|Brutto-Kaufpreis|Netto-Kaufpreis)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)', text, re.IGNORECASE)
    if not price_match:
        price_match = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)', text)
    if price_match:
        price_str = price_match.group(1)
        car_data["price"] = price_str.split(',')[0].replace('.', '')
        
        context = text[max(0, price_match.start()-50) : min(len(text), price_match.end()+50)].lower()
        if "brutto" in context:
            car_data["price_status"] = "brutto"
        elif "netto" in context:
            car_data["price_status"] = "netto"

    # 3. Extract Technical Specs
    spec_patterns = {
        "Kilometerstand": r'(?:Kilometerstand|Laufleistung|mstand|Kilometer|KM-Stand|KM).*?([\d\s.]+)\s*km',
        "Erstzulassung": r'(?:Erstzulassung|EZ)[\s:]*(\d{2}/\d{2,4,4}|\d{4}|\d{2}\.\d{2}\.\d{4})',
        "Kraftstoff": r'\b(?:Kraftstoffart\s*/\s*Zylinder|Kraftstoffart|Kraftstoff|Carburant)\b[\s:]*([A-Za-z\-/\.\s]+?)(?:/|$|\n|\s\b(?:Heckantrieb|Frontantrieb|Allrad|Ausstattungsvariante)\b)',
        "Leistung": r'\b(?:Leistung\s*/\s*Hubraum|Leistung|Power|Edition)\b[\s:]*([\d,./\s]+(?:kW|kw|PS))',
        "Getriebe": r'\b(?:Getriebe|Schaltung)\b[\w\s/]*\b(Automatik|Schaltgetriebe|Manuell|Doppelkupplungsgetriebe)\b',
        "Hubraum": r'\b(?:Hubraum)\b[\s:]*([\d.\s]+)\s*(?:ccm|cm3)',
        "Außenfarbe": r'(?:Farbe\s*\(Allgemein\)|Farbe\s*/\s*Farbcode|Außenfarbe|Lackierung|Farbe)[\s:]*(?!Farbe\b)([A-Za-zäöüÄÖÜß\s/]+?)(?:\n|Laufleistung|Hubraum|$)',
        "Antrieb": r'\b(?:Antriebsart|Antrieb)\b[\s:]*([A-Za-z\-/\s]+?)(?:\n|Ausstattungsvariante|$)',
    }

    for label, pattern in spec_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = clean_value(match.group(1))
            val = re.sub(r'\s+', ' ', val)  # clean up inner spaces
            # clean up dots for mileage
            if label == "Kilometerstand":
                val = val.replace('.', '')
                car_data["carMileage"] = val + " km"
            elif label == "Erstzulassung":
                car_data["carRegistration"] = val
            elif label == "Außenfarbe":
                car_data["carColor"] = val
            elif label == "Kraftstoff":
                car_data["carFuel"] = val
            
            car_data["specs"][label] = val

    # Backup Fuel Detection for BEV
    if "Batterie Kauf/Eigentum" in text or "Batteriekapazität" in text:
        car_data["carFuel"] = "Elektro"
        car_data["specs"]["Kraftstoff"] = "Elektro"
    
    # Execution Fallback
    if not car_data.get("carExecution") and "Ausstattungsvariante" in car_data["specs"]:
        car_data["carExecution"] = car_data["specs"]["Ausstattungsvariante"]

    # 4. Extract Features
    categories = {
        "Interieur & Komfort": ["Klima", "Sitzheizung", "Leder", "Multifunktionslenkrad", "Navigationssystem", "Sitz", "Fensterheber", "Zentralverriegelung", "Armlehne", "Panoramadach"],
        "Technologie & Assistenz": ["Tempomat", "Einparkhilfe", "PDC", "Rückfahrkamera", "Bordcomputer", "DAB", "Bluetooth", "USB", "Freisprecheinrichtung", "Spurhalteassistent", "ACC", "Sensor"],
        "Sicherheit": ["ABS", "ESP", "Airbag", "Wegfahrsperre", "Notbremsassistent", "Regensensor", "Reifendruck", "ISOFIX"],
        "Exterieur": ["Alufelgen", "LED", "Xenon", "Schiebedach", "Dachreling", "Anhängerkupplung", "Metallic", "Scheinwerfer"]
    }

    garbage_keywords = ["Abbildung", "Besichtigungsort", "Seite", "FIN:", "Protokollnummer", "Zustandsbericht", "Fahrzeugdetails", "Auftragsdaten", "Datum der", "Bewertung", "Lagerplatz", "Fahrzeugausstattung", "Lose Teile", "Reifen", "BriefNr", "HSN/TSN", "Abgasnorm", "zul. Gesamtgewicht", "Leergewicht", "Bordmappe", "Betriebsanleitung", "Schlüssel", "Page ", "--- Page", "Bauteil ", "Position ", "Beschreibun ", "Intensität ", "Reparaturmethode ", "Gebrauchsspur ", "Außenschäden", "Innenschäden"]

    feature_lines = re.findall(r'(?:^|\n|[\u2022*-])\s*([A-ZÄÖÜ][^.\n:]{3,80})(?=\n|[\u2022*-]|$)', text)
    
    for feat in feature_lines:
        feat = feat.strip()
        if len(feat) < 4 or len(feat) > 100: continue
        if any(gk in feat for gk in garbage_keywords): continue
        if re.search(r'\d{2}\.\d{2}\.\d{4}', feat): continue # skip dates
        
        assigned = False
        for cat_name, keywords in categories.items():
            if any(kw.lower() in feat.lower() for kw in keywords):
                if feat not in car_data["features"][cat_name]:
                    car_data["features"][cat_name].append(feat)
                assigned = True
                break
        
        if not assigned:
            if feat not in car_data["features"]["Weitere Merkmale"]:
                car_data["features"]["Weitere Merkmale"].append(feat)

    car_data["features"] = {k: v for k, v in car_data["features"].items() if v}

    # 5. Extract Schäden (Damages)
    # Case A: Vertical blocks (Zustandsbericht)
    damage_matches = re.finditer(r'Bauteil\s+([A-Za-zäöüÄÖÜß\s]+)\nPosition\s+([A-Za-zäöüÄÖÜß\s\-]*)\n(?:Beschreibun\s*g|Beschreibung)\s+([A-Za-zäöüÄÖÜß\s\-]+?)(?=\n(?:Intensität|Reparatur|Bauteil|Innenschäden|Sonstiges|$))', text, re.DOTALL)
    for match in damage_matches:
        bauteil = match.group(1).strip()
        position = match.group(2).strip()
        beschreibung = match.group(3).strip()
        car_data["schäden"].append({
            "Bauteil": bauteil,
            "Position": position,
            "Beschreibung": beschreibung
        })

    # Case B: Tabular damage check for Expertise format (Wertmindernde Faktoren / Gebrauchsspuren)
    if is_expertise:
        # Find tables
        tables = re.findall(r'(?:Wertmindernde Faktoren|Gebrauchsspuren)\s*\nNr\.\s+Bauteilgruppe\s+Beschreibung\s*\n(.*?)(?=\n\n|\n[A-Z][a-z]+|$)', text, re.DOTALL)
        for table_content in tables:
            rows = re.findall(r'(\d+)\s+([A-Za-zäöüÄÖÜß\s/]+)\s+([^\n]+)', table_content)
            for nr, bauteil, desc in rows:
                car_data["schäden"].append({
                    "Bauteil": bauteil.strip(),
                    "Beschreibung": desc.strip()
                })

    # Case C: Single line damage mentions
    damage_lines = re.findall(r'(?:Beschädigung\s*\d+:\s*|Nachlackierung\s*\d+:\s*)([^\n]+)', text)
    for dmg in damage_lines:
        # Clean up if it's a long line with labels
        clean_dmg = re.split(r'\s-\s[A-Z]', dmg)[0].strip()
        car_data["schäden"].append({"Beschreibung": clean_dmg})

    # Deduplicate Schäden dictionaries
    unique_schäden = []
    seen_desc = set()
    for s in car_data["schäden"]:
        desc = s.get("Beschreibung", "")
        if desc and desc not in seen_desc:
            seen_desc.add(desc)
            unique_schäden.append(s)
    car_data["schäden"] = unique_schäden

    return car_data

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf.py <path_to_pdf>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        sys.exit(1)
        
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        print("Error: Could not extract text from PDF.")
        sys.exit(1)
        
    structured_data = parse_car_details(raw_text)
    
    result = {
        "source": pdf_path,
        "cars": [structured_data],
        "extraction_status": "success",
        "method": "pdf_extraction"
    }
    
    with open("extracted_cars.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
        
    print(json.dumps(result, indent=4, ensure_ascii=False))
