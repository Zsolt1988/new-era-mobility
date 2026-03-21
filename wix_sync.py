import json
import csv
import os
import requests
import time

# Configuration (defaults for local/mock testing)
CONFIG_FILE = 'config.json'
MAPPING_FILE = 'mapping.json'
DEFAULT_CSV = 'aktive_sammlung.csv'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "wix_api_key": "YOUR_WIX_API_KEY",
            "wix_site_id": "YOUR_WIX_SITE_ID",
            "collection_id": "Cars",
            "is_mock": True
        }
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def load_mapping():
    if not os.path.exists(MAPPING_FILE):
        # Default mapping from Aktive_Sammlung CSV to possible Wix Field IDs
        return {
            "Hersteller": "brand",
            "Modell": "model",
            "Ausführung": "execution",
            "Kraftstoff": "fuelType",
            "Getriebe": "transmission",
            "PS": "power",
            "KM Stand": "mileage",
            "Erstzulassung": "registration",
            "Farbe": "color",
            "Farbe_Einfach": "simpleColor",
            "Sofortkauf-Preis": "price",
            "Link": "listingUrl",
            "Baujahr": "year"
        }
    with open(MAPPING_FILE, 'r') as f:
        return json.load(f)

def sync_data(csv_path=DEFAULT_CSV):
    config = load_config()
    mapping = load_mapping()
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    print(f"Reading data from {csv_path}...")
    items = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            item_data = {}
            for csv_col, wix_field in mapping.items():
                item_data[wix_field] = row.get(csv_col, '')
            # Wix v2 items usually need to be wrapped in a 'data' object
            items.append({"data": item_data})

    print(f"Prepared {len(items)} items for Wix.")

    if config.get("is_mock", True):
        print("MOCK MODE: Not sending real requests. Data Preview:")
        print(json.dumps(items[0] if items else {}, indent=4))
        print("Successfully validated mock sync.")
        return

    # Real synchronization logic using Wix REST API
    print(f"Sending data to Wix Site: {config['wix_site_id']}...")
    
    # Wix REST API v2 endpoint for bulk inserting items
    # Documentation: https://dev.wix.com/api/rest/wix-data/wix-data/data-items/bulk-insert-data-items
    endpoint = "https://www.wixapis.com/wix-data/v2/bulk/items/insert"
    
    headers = {
        "Authorization": config["wix_api_key"],
        "wix-site-id": config["wix_site_id"],
        "Content-Type": "application/json"
    }

    # v2 payload structure
    payload = {
        "dataCollectionId": config["collection_id"],
        "dataItems": items
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        if response.ok:
            print("Successfully synchronized with Wix! Bulk insert complete.")
            print(f"Response: {response.json().get('results', [])}")
        else:
            print(f"Wix API Error ({response.status_code}): {response.text}")
            if response.status_code == 401:
                print("Tip: Check if your API Key has expired or has the correct permissions.")
    except Exception as e:
        print(f"Failed to connect to Wix: {str(e)}")

if __name__ == "__main__":
    sync_data()
