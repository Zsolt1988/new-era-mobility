import json
import sys
import os
import re
import urllib.request
from urllib.error import URLError, HTTPError

def extract_car_info(source):
    """
    Extracts car information from a URL or a local HTML file.
    """
    html_content = ""
    
    if os.path.exists(source):
        print(f"Reading from local file: {source}")
        with open(source, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
    else:
        print(f"Attempting to fetch URL: {source}")
        try:
            req = urllib.request.Request(
                source, 
                data=None, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            with urllib.request.urlopen(req) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
            print("Successfully fetched URL content.")
        except HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}")
            return {
                "source_url": source,
                "extraction_status": "error",
                "message": f"HTTP Error: {e.code}"
            }
        except URLError as e:
            print(f"URL Error: {e.reason}")
            return {
                "source_url": source,
                "extraction_status": "error",
                "message": f"Failed to reach server: {e.reason}"
            }
        except ValueError:
            return {
                "source_url": source,
                "extraction_status": "error",
                "message": "Invalid URL format. Please start with http:// or https://"
            }

def extract_audaris_info(html_content, source):
    """
    Attempts to extract data via Audaris API if the site is identified as Audaris.
    """
    # Detect Audaris internal number in URL (e.g., .../EG-GK999/)
    internal_number_match = re.search(r"/([^/]+)/?$", source)
    if not internal_number_match:
        return None
        
    internal_number = internal_number_match.group(1)
    
    # Default Ostermaier IDs (could be extracted from HTML if needed, but these are stable)
    client_id = "1841"
    website_id = "5f5b60b339214b195c6a612f"
    
    # Check if the site is indeed Ostermaier or has Audaris indicators
    if "ostermaier.de" in source or "audaris" in html_content:
        api_url = f"https://api.audaris.de/v1/clients/{client_id}/website-vehicles/{internal_number}?field=internalNumber&website={website_id}"
        print(f"Detected Audaris site. Fetching from API: {api_url}")
        
        try:
            req = urllib.request.Request(
                api_url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response:
                api_data = json.loads(response.read().decode('utf-8'))
                
            if "data" in api_data:
                car = api_data["data"]
                # Map to standard format
                car_data = {
                    "manufacturerName": car.get("manufacturerName"),
                    "modelName": car.get("modelName"),
                    "carTitle": car.get("title"),
                    "carPrice": car.get("price", {}).get("gross"),
                    "carMileage": car.get("mileage"),
                    "firstRegistration": car.get("registration"),
                    "carFuel": car.get("fuelTypeName"),
                    "carTransmission": car.get("transmissionType"),
                    "carPower": f"{car.get('powerKW')} kW ({car.get('powerPS')} PS)",
                    "title": f"{car.get('manufacturerName')} {car.get('modelName')} {car.get('title')}",
                    "price": str(car.get("price", {}).get("gross", "N/A")),
                    "price_status": "brutto",
                    "source": source
                }
                
                # Tech Specs
                specs = {
                    "Kilometerstand": f"{car.get('mileage')} km",
                    "Erstzulassung": car.get("registration"),
                    "Kraftstoff": car.get("fuelTypeName"),
                    "Getriebe": car.get("transmissionType"),
                    "Leistung": f"{car.get('powerPS')} PS",
                    "Farbe": car.get("exteriorColorName"),
                    "Polster": car.get("interiorColorName"),
                    "Interne Nummer": car.get("vehicleClientInternalNumber")
                }
                car_data["specs"] = specs
                
                # Features
                if "features" in car:
                    car_data["features"] = {"Ausstattung": [f.get("name") for f in car.get("features", [])]}
                
                # Highlights
                if "descriptionHTML" in car:
                    # Very basic highlight extraction from HTML if needed, or just use features
                    pass

                return car_data
        except Exception as e:
            print(f"Audaris API extraction failed: {e}")
            
    return None

def extract_car_info(source):
    """
    Extracts car information from a URL or a local HTML file.
    """
    html_content = ""
    
    if os.path.exists(source):
        print(f"Reading from local file: {source}")
        with open(source, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
    else:
        print(f"Attempting to fetch URL: {source}")
        try:
            req = urllib.request.Request(
                source, 
                data=None, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            with urllib.request.urlopen(req) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
            print("Successfully fetched URL content.")
        except HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason}")
            return {
                "source_url": source,
                "extraction_status": "error",
                "message": f"HTTP Error: {e.code}"
            }
        except URLError as e:
            print(f"URL Error: {e.reason}")
            return {
                "source_url": source,
                "extraction_status": "error",
                "message": f"Failed to reach server: {e.reason}"
            }
        except ValueError:
            return {
                "source_url": source,
                "extraction_status": "error",
                "message": "Invalid URL format. Please start with http:// or https://"
            }

    # 1. Try Audaris API first if applicable
    audaris_data = extract_audaris_info(html_content, source)
    if audaris_data:
        print("Successfully extracted data via Audaris API.")
        return {
            "source": source,
            "cars": [audaris_data],
            "extraction_status": "success",
            "method": "audaris_api"
        }

    # 2. Try to extract from window.dataLayer
    # Pattern looks for: car : { ... }
    data_layer_match = re.search(r"car\s*:\s*(\{.*?\})", html_content, re.DOTALL)
    
    if data_layer_match:
        try:
            # The JSON in the HTML might have single quotes or trailing commas, 
            # so we'll do some basic cleanup or just try to extract keys.
            json_text = data_layer_match.group(1)
            # Basic cleanup for JS object to JSON
            json_text = re.sub(r"(\w+)\s*:", r'"\1":', json_text) # keys to double quotes
            json_text = json_text.replace("'", '"') # single quotes to double quotes
            # Remove trailing commas before closing braces/brackets
            json_text = re.sub(r",\s*([}\]])", r"\1", json_text)
            
            car_data = json.loads(json_text)
            print("Successfully extracted data from dataLayer.")
            
            # --- Addition: Extract Specs from BoxText grid ---
            specs = {}
            # Find the gridContainer BoxText using the co2Data as a safe end-marker
            specs_match = re.search(r'<div class="gridContainer BoxText">(.*?)</div>\s*<div class="co2Data', html_content, re.DOTALL)
            if specs_match:
                section = specs_match.group(1)
                # Extract all items that look like <div class="item ">Value</div>
                items = re.findall(r'<div class="item\s*">([^<]+)</div>', section)
                # Items come in pairs: Label, Value
                for i in range(0, len(items) - 1, 2):
                    label = items[i].strip().replace(":", "")
                    value = items[i+1].strip()
                    if label and value:
                        specs[label] = value
            
            # --- Addition: Try to extract battery size or other tech details from script tags ---
            # Often found in "batterySize", "batteryCapacity", or description
            battery_match = re.search(r'"battery(?:Size|Capacity)"\s*:\s*(\d+(?:[.,]\d+)?)', html_content)
            if battery_match:
                specs["Batteriekapazität"] = battery_match.group(1) + " kWh"
            
            if specs:
                car_data["specs"] = specs
            
            # --- Addition: Extract Highlights ---
            highlights = []
            highlights_match = re.search(r'<div class="item highlights">.*?</i>(.*?)</div>', html_content, re.DOTALL)
            if highlights_match:
                content = highlights_match.group(1)
                # Split by <br /> and clean
                highlights = [h.strip() for h in re.split(r'<br\s*/?>', content) if h.strip()]
            if highlights:
                car_data["highlights"] = highlights

            # --- Addition: Extract CO2 details ---
            co2_match = re.search(r'<div class="co2Data co2DataDetails">(.*?)</div>', html_content, re.DOTALL)
            if co2_match:
                car_data["co2_details"] = co2_match.group(1).strip()

            # --- Addition: Extract Getriebe (Gearbox) ---
            gear_match = re.search(r'"transmissionType"\s*:\s*"([^"]+)"', html_content)
            if gear_match:
                car_data["carTransmission"] = gear_match.group(1)
            else:
                # Search for Getriebe label
                gear_label_match = re.search(r'>Getriebe<.*?<span>(.*?)</span>', html_content, re.DOTALL)
                if gear_label_match:
                    car_data["carTransmission"] = gear_label_match.group(1).strip()
            
            # --- Refined Feature Extraction ---
            features = {}
            # Use a more restrictive pattern for the category name: [^<]+
            feature_blocks = re.findall(r"<strong>([^<]*?):?</strong>\s*(?:<br />)?\s*<ul>(.*?)</ul>", html_content, re.DOTALL)
            for category, list_content in feature_blocks:
                category = category.strip()
                if not category or len(category) > 50: # Avoid catching large text as category
                    continue
                # Extract all <li> items
                items = re.findall(r"<li>(.*?)</li>", list_content)
                if items:
                    features[category] = [item.strip() for item in items]
            
            if features:
                car_data["features"] = features
            # --------------------------------------------------

            return {
                "source": source,
                "cars": [car_data],
                "extraction_status": "success",
                "method": "dataLayer"
            }
        except Exception as e:
            print(f"Failed to parse dataLayer JSON: {e}")

    # 3. Fallback: Manual extraction using regex for key fields
    print("Attempting fallback manual extraction...")
    
    # Pre-clean HTML Content
    clean_html = html_content.replace("&nbsp;", " ").replace("&euro;", "€")
    
    # Extract Title/Brand/Model
    # Try H1 first as it's usually the prominent car name
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", clean_html, re.IGNORECASE | re.DOTALL)
    if h1_match:
        title = re.sub(r"<[^>]+>", " ", h1_match.group(1)).strip()
        # Remove extra whitespace
        title = re.sub(r"\s+", " ", title)
    else:
        title_match = re.search(r"<title>(.*?)</title>", clean_html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Unknown Car"
    
    # If title still feels generic (like "Angebote entdecken"), try Meta Tags
    if "Angebote entdecken" in title or "Fahrzeugangebote" in title:
        og_title = re.search(r'property="og:title"\s*content="([^"]+)"', clean_html)
        if og_title:
            title = og_title.group(1).strip()
    
    # Improved Price regex
    # Common patterns: 33.240,- € or 33.240 € or 33,240.00 €
    # We look for a price followed by the Euro symbol
    price_match = re.search(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2}|,-)?)\s*€", clean_html)
    if not price_match:
        # Try finding it in audaris-price-value class or similar
        price_match = re.search(r'class="[^"]*price[^"]*"[^>]*>([^<€]+)', clean_html)
        
    price = "N/A"
    if price_match:
        price_str = price_match.group(1).strip()
        # Clean up: remove dots, handle comma
        price = price_str.split(",")[0].replace(".", "")
    
    price_status = "unknown"
    if price_match:
        context = clean_html[max(0, price_match.start()-50) : min(len(clean_html), price_match.end()+50)]
        if "brutto" in context.lower():
            price_status = "brutto"
        elif "netto" in context.lower():
            price_status = "netto"

    # Build a simple result
    fallback_data = {
        "title": title,
        "price": price,
        "price_status": price_status,
        "source": source,
        "extraction_status": "success",
        "method": "fallback_regex"
    }
    
    return {
        "source": source,
        "cars": [fallback_data],
        "extraction_status": "success",
        "method": "fallback"
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_cars.py <URL or local_file.html>")
        sys.exit(1)
        
    source = sys.argv[1]
    data = extract_car_info(source)
    
    output_file = "extracted_cars.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Extracted data saved to {output_file}")
    try:
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except UnicodeEncodeError:
        print(json.dumps(data, indent=4).encode('ascii', 'backslashreplace').decode('ascii'))
