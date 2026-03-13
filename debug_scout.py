import urllib.request
import re
import sys

def test_scrape(search_url):
    print(f"Fetching URL: {search_url}")
    try:
        req = urllib.request.Request(
            search_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept-Language': 'de-AT,de;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.getcode()
            html = resp.read().decode('utf-8', errors='replace')
            print(f"Response status: {status}")
            print(f"Response size: {len(html)} bytes")
            
            # Save HTML to file for inspection
            with open("debug_scout.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved HTML to debug_scout.html")

            prices = []
            
            # Pattern 1: JSON price fields
            raw_prices = re.findall(r'"price(?:Raw)?"\s*:\s*(\d{3,7})', html)
            if raw_prices:
                print(f"Found raw_prices: {raw_prices}")
                prices = list(sorted(set(int(p) for p in raw_prices)))[:3]

            # Pattern 2: Fallback text
            if not prices:
                text_prices = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*€', html)
                print(f"Found text_prices: {text_prices}")
                def parse_price(p: str) -> int:
                    return int(p.replace('.', '').replace(',', ''))
                prices = list(sorted(set(parse_price(p) for p in text_prices if 1000 < parse_price(p) < 500000)))[:3]

            print(f"Final extracted prices: {prices}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    url = "https://www.autoscout24.at/lst/bmw/320?atype=C&cy=A&damaged_listing=exclude&desc=0&powertype=kw&sort=price&ustate=N%2CU&offer_type=D"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    test_scrape(url)
