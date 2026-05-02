import http.server
import socketserver
import json
import os
import subprocess
import base64
import traceback
import cgi
from report_downloader import download_report, process_excel

PORT = 8087
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    pass

class DownloaderHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/get-status':
            status = "Bereit"
            if os.path.exists('status.txt'):
                with open('status.txt', 'r', encoding='utf-8') as f:
                    status = f.read().strip()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": status}).encode('utf-8'))
            return
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/download-report':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url', '')
                
                if url:
                    # Run in a separate process to avoid blocking the server, 
                    # but the HTML expects a JSON response after completion.
                    # Given the CLI structure of report_downloader.py, we can just call it.
                    print(f"Starting download for: {url}")
                    download_report(url)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": "Download abgeschlossen."}).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/upload-batch':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                filename = data.get('filename', 'batch.xlsx')
                content_b64 = data.get('content', '')
                
                if content_b64:
                    file_data = base64.b64decode(content_b64)
                    file_path = os.path.join(BASE_DIR, 'temp_batch.xlsx')
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    print(f"Batch upload received: {filename}")
                    # Process the excel
                    process_excel(file_path)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "message": "Batch Download abgeschlossen."}).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    with ThreadingSimpleServer(("", PORT), DownloaderHandler) as httpd:
        print(f"Downloader Server running at http://localhost:{PORT}")
        httpd.serve_forever()
