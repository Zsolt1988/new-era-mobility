import http.server
import socketserver
import json
import urllib.parse
import subprocess
import os

PORT = 8080

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
                            ['python', 'extract_cars.py', url],
                            check=True,
                            capture_output=True,
                            text=True
                        )
                        print("Extraction script completed.")
                        print(result.stdout)
                        
                        # Read the newly generated json file
                        if os.path.exists('extracted_cars.json'):
                            with open('extracted_cars.json', 'r', encoding='utf-8') as f:
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
                
        else:
            self.send_error(404, "Endpoint not found")

with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    print(f"Backend Server running at http://localhost:{PORT}")
    print("Keep this terminal open, and use the UI to trigger extractions.")
    httpd.serve_forever()
