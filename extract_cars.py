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

    # 1. Try to extract from window.dataLayer
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

    # 2. Fallback: Manual extraction using regex for key fields
    print("Attempting fallback manual extraction...")
    
    # Extract Title/Brand/Model from header tags or titles
    title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else "Unknown Car"
    
    # Simple regex for finding price pattern like 28.799 €
    # And check for brutto/netto labels nearby
    price_match = re.search(r"(\d+[\.,]\d+)\s*&nbsp;&euro;", html_content)
    price = price_match.group(1).replace(".", "") if price_match else "N/A"
    
    price_status = "unknown"
    if price_match:
        # Search for (brutto) or (netto) within 50 chars of the price
        context = html_content[max(0, price_match.start()-50) : min(len(html_content), price_match.end()+50)]
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
