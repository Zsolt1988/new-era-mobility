import urllib.request
import json

def test_backend():
    url = "http://localhost:8080/api/autoscout-prices?url=https%3A%2F%2Fwww.autoscout24.at%2Flst%2Fbmw%2F320%3Fatype%3DC%26cy%3DA%26damaged_listing%3Dexclude%26desc%3D0%26offer_type%3DD"
    print(f"Testing local backend: {url}")
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print("Response success!")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Backend test failed: {e}")

if __name__ == "__main__":
    test_backend()
