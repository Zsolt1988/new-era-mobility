import json
import requests
import os

def inspect_collection():
    if not os.path.exists('config.json'):
        print("Error: config.json not found.")
        return
    
    with open('config.json', 'r') as f:
        config = json.load(f)

    collection_id = config['collection_id']
    print(f"Inspecting collection '{collection_id}' for Wix Site: {config['wix_site_id']}...")
    
    # Wix REST API v2 endpoint for getting a single collection
    endpoint = f"https://www.wixapis.com/wix-data/v2/collections/{collection_id}"
    
    headers = {
        "Authorization": config["wix_api_key"],
        "wix-site-id": config["wix_site_id"],
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(endpoint, headers=headers)
        if response.ok:
            collection = response.json().get('collection', {})
            fields = collection.get('fields', [])
            print(f"Found {len(fields)} fields:")
            for f in fields:
                print(f"- Key: {f.get('key')}, Display Name: {f.get('displayName')}, Type: {f.get('type')}")
        else:
            print(f"Wix API Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"Failed to connect to Wix: {str(e)}")

if __name__ == "__main__":
    inspect_collection()
