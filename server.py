import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import subprocess
import os
import re
import base64
import sys
import traceback
from image_overlay.overlay_service import process_car_overlay

PORT = 8085
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

    pass

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/extract':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url', '')
                print(f"Extraction requested for: {url}")
                
                if url:
                    # Run the python extraction script
                    # This will overwrite extracted_cars.json
                    try:
                        result = subprocess.run(
                            ['python3', 'extract_cars.py', url],
                            check=True,
                            capture_output=True,
                            text=True,
                            cwd=BASE_DIR
                        )
                        print("Extraction script completed.")
                        print(result.stdout)
                        
                        # Read the newly generated json file
                        json_path = os.path.join(BASE_DIR, 'extracted_cars.json')
                        if os.path.exists(json_path):
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_result = json.load(f)
                                
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(json_result).encode('utf-8'))
                        else:
                            self.send_response(500)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "error", "message": "Failed to create extracted_cars.json"}).encode('utf-8'))
                            
                    except subprocess.CalledProcessError as e:
                        print(f"Subprocess error: {e.stderr}")
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": f"Extraction failed: {e.stderr}"}).encode('utf-8'))
                    except Exception as e:
                        print(f"Unexpected error: {str(e)}")
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": f"Server error: {str(e)}"}).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "No URL provided"}).encode('utf-8'))
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                print(f"Received data: {post_data.decode('utf-8', errors='ignore')}")
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"Invalid JSON: {str(e)}"}).encode('utf-8'))
            except Exception as e:
                print(f"Generic error in do_POST: {str(e)}")
                self.send_response(500)
                self.end_headers()
                
        elif self.path == '/api/export-csv':
            try:
                print("CSV Export requested.")
                # Run the export script
                result = subprocess.run(
                    ['python3', 'export_aktive_sammlung.py'],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=BASE_DIR
                )
                print("Export script completed.")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "CSV exported successfully"}).encode('utf-8'))
            except subprocess.CalledProcessError as e:
                print(f"Export script error: {e.stderr}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"Export failed: {e.stderr}"}).encode('utf-8'))
            except Exception as e:
                print(f"Unexpected error during CSV export: {str(e)}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/overlay':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                image_b64 = data.get('image', '')
                offset = data.get('offset', 0)
                
                if image_b64:
                    # Remove header if present (e.g. data:image/jpeg;base64,...)
                    if ',' in image_b64:
                        image_b64 = image_b64.split(',')[1]
                    
                    image_data = base64.b64decode(image_b64)
                    
                    # Save temp input
                    temp_input = os.path.join(BASE_DIR, 'image_overlay', 'temp_input.jpg')
                    with open(temp_input, 'wb') as f:
                        f.write(image_data)
                    
                    # Prepare output path
                    output_file = 'overlay_result.jpg'
                    output_path = os.path.join(BASE_DIR, 'image_overlay', output_file)
                    bg_path = os.path.join(BASE_DIR, 'image_overlay', 'fixed_background.png')
                    
                    # Process
                    print("Starting overlay process...")
                    process_car_overlay(temp_input, bg_path, output_path, position_y_offset=offset)
                    
                    if os.path.exists(output_path):
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "status": "ok", 
                            "url": f"/image_overlay/{output_file}?t={os.path.getmtime(output_path)}"
                        }).encode('utf-8'))
                    else:
                        raise FileNotFoundError(f"Overlay created no file at {output_path}")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "No image data provided"}).encode('utf-8'))
            except Exception as e:
                print(f"Error in overlay API: {str(e)}")
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/sync-wix':
            try:
                print("Wix Synchronization requested.")
                # Run the wix sync script
                result = subprocess.run(
                    ['python3', 'wix_sync.py'],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=BASE_DIR
                )
                print("Wix synchronization script completed.")
                print(result.stdout)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": "Wix synchronization successful"}).encode('utf-8'))
            except subprocess.CalledProcessError as e:
                print(f"Wix sync error: {e.stderr}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"Wix sync failed: {e.stderr}"}).encode('utf-8'))
            except Exception as e:
                print(f"Unexpected error during Wix sync: {str(e)}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/save-cars':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                new_data = json.loads(post_data.decode('utf-8'))
                
                print("Saving updated car data.")
                with open(os.path.join(BASE_DIR, 'extracted_cars.json'), 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, indent=4, ensure_ascii=False)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                print(f"Error saving cars: {str(e)}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self):
        # Handle the autoscout price scraping endpoint
        if self.path.startswith('/api/autoscout-prices'):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            search_url = params.get('url', [None])[0]

            if not search_url:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "No url param provided"}).encode('utf-8'))
                return

            try:
                print(f"DEBUG: Fetching AutoScout24 URL: {search_url}")
                # Fetch AutoScout24 with a browser-like User-Agent to avoid bot blocks
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
                    print(f"DEBUG: Response status: {status}")
                    print(f"DEBUG: HTML Snippet (first 500 chars): {html[:500]}")

                print(f"Fetched AutoScout24 page ({len(html)} bytes)")

                # Try to extract prices from JSON-LD or inline price data
                # AutoScout24 embeds listing data in <script type="application/json"> or window.__INITIAL_STATE__
                prices = []

                # Find all <article> tags first to isolate valid listings from "similar vehicles"
                articles = re.findall(r'<article.*?</article>', html, re.DOTALL)
                
                valid_prices = []
                for article in articles:
                    # STRICT FILTERING: Only consider vehicles from the actual search results
                    if 'data-source="listpage_search-results"' not in article:
                        continue
                        
                    # Ignore sponsored listings if they bypass sorting
                    if 'sponsored' in article.lower() or 'promoted' in article.lower():
                        continue

                    # Extract the price for this valid article
                    price_m = re.search(r'data-price="(\d+)"', article)
                    if price_m:
                        valid_prices.append(int(price_m.group(1)))

                if valid_prices:
                    prices = list(sorted(set(valid_prices)))[:3]

                # Fallback: Pattern 2: JSON price fields if articles structure changes completely
                if not prices:
                    raw_prices = re.findall(r'"price(?:Raw)?"\s*:\s*(\d{3,7})', html)
                    if raw_prices:
                        prices = list(sorted(set(int(p) for p in raw_prices)))[:3]

                # Pattern 3: Fallback — price text like "12.500 €" or "12,500 €"
                if not prices:
                    text_prices = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*€', html)
                    def parse_price(p: str) -> int:
                        return int(p.replace('.', '').replace(',', ''))
                    prices = list(sorted(set(parse_price(p) for p in text_prices if 1000 < parse_price(p) < 500000)))[:3]

                if prices:
                    result = {
                        "status": "ok",
                        "prices": [{"rank": i+1, "price": p, "formatted": f"€ {p:,}".replace(',', '.')} for i, p in enumerate(prices)]
                    }
                else:
                    result = {"status": "no_prices", "message": "No prices could be extracted from the page. AutoScout24 may require JavaScript."}

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode('utf-8'))

            except Exception as e:
                print(f"AutoScout scrape error: {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        else:
            # Default: serve static files
            super().do_GET()

with ThreadingSimpleServer(("", PORT), MyHandler) as httpd:
    print(f"Backend Server running at http://localhost:{PORT}")
    print("Keep this terminal open, and use the UI to trigger extractions.")
    httpd.serve_forever()
