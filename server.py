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
import cgi
import shutil
from image_overlay.overlay_service import process_car_overlay
from report_downloader import download_report, process_excel

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
                if url:
                    subprocess.run(['python3', 'extract_cars.py', url], check=True, cwd=BASE_DIR)
                    json_path = os.path.join(BASE_DIR, 'extracted_cars.json')
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            json_result = json.load(f)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(json_result).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/extract-pdf':
            try:
                ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
                if ctype == 'multipart/form-data':
                    pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                    pdict['CONTENT-LENGTH'] = int(self.headers.get('content-length'))
                    form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
                    if 'pdf' in form:
                        file_item = form['pdf']
                        pdf_path = os.path.join(BASE_DIR, 'temp_upload.pdf')
                        with open(pdf_path, 'wb') as f:
                            f.write(file_item.file.read())
                        subprocess.run(['python3', 'extract_pdf.py', pdf_path], check=True, cwd=BASE_DIR)
                        json_path = os.path.join(BASE_DIR, 'extracted_cars.json')
                        if os.path.exists(json_path):
                            with open(json_path, 'r', encoding='utf-8') as f:
                                json_result = json.load(f)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(json_result).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/merge-bca':
            try:
                ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
                if ctype == 'multipart/form-data':
                    pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                    pdict['CONTENT-LENGTH'] = int(self.headers.get('content-length'))
                    form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']})
                    
                    if 'xls' in form and 'html' in form:
                        mode = form.getvalue('mode', 'web') # 'web' or 'excel'
                        xls_item = form['xls']
                        html_item = form['html']
                        
                        temp_dir = os.path.join(BASE_DIR, 'temp_uploads')
                        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
                            
                        xls_path = os.path.join(temp_dir, 'temp_input.xls')
                        html_path = os.path.join(temp_dir, 'temp_input.html')
                        
                        with open(xls_path, 'wb') as f: f.write(xls_item.file.read())
                        with open(html_path, 'wb') as f: f.write(html_item.file.read())
                            
                        if mode == 'excel':
                            out_path = os.path.join(BASE_DIR, 'BCA_Enriched_Result.xlsx')
                            subprocess.run(['python3', 'process_bca.py', xls_path, html_path, out_path], check=True, cwd=BASE_DIR)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "success", "message": "Excel generiert", "url": "/BCA_Enriched_Result.xlsx"}).encode('utf-8'))
                        else:
                            out_path = os.path.join(BASE_DIR, 'index.html')
                            subprocess.run(['python3', 'create_html_table.py', '--xls', xls_path, '--html', html_path, '--out', out_path], check=True, cwd=BASE_DIR)
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "success", "url": "index.html"}).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/sync-wix':
            try:
                subprocess.run(['python3', 'wix_sync.py'], check=True, cwd=BASE_DIR)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
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
                    if ',' in image_b64: image_b64 = image_b64.split(',')[1]
                    image_data = base64.b64decode(image_b64)
                    temp_input = os.path.join(BASE_DIR, 'image_overlay', 'temp_input.jpg')
                    with open(temp_input, 'wb') as f: f.write(image_data)
                    output_file = 'overlay_result.jpg'
                    output_path = os.path.join(BASE_DIR, 'image_overlay', output_file)
                    bg_path = os.path.join(BASE_DIR, 'image_overlay', 'fixed_background.png')
                    process_car_overlay(temp_input, bg_path, output_path, position_y_offset=offset)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "url": f"/image_overlay/{output_file}?t={os.path.getmtime(output_path)}"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/download-report':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url', '')
                if url:
                    download_report(url)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        elif self.path == '/api/upload-batch':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                content_b64 = data.get('content', '')
                if content_b64:
                    file_data = base64.b64decode(content_b64)
                    file_path = os.path.join(BASE_DIR, 'temp_batch.xlsx')
                    with open(file_path, 'wb') as f: f.write(file_data)
                    process_excel(file_path)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/api/get-status':
            status = "Bereit"
            if os.path.exists('status.txt'):
                try:
                    with open('status.txt', 'r', encoding='utf-8') as f: status = f.read().strip()
                except: pass
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": status}).encode('utf-8'))
            return

        if self.path == '/api/push-github':
            try:
                subprocess.run(['git', 'add', '.'], check=True, cwd=BASE_DIR)
                subprocess.run(['git', 'commit', '-m', 'Automatisches Portfolio Update'], check=False, cwd=BASE_DIR)
                subprocess.run(['git', 'push'], check=True, cwd=BASE_DIR)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        if self.path.startswith('/api/autouncle-prices') or self.path.startswith('/api/autoscout-prices'):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            search_url = params.get('url', [None])[0]
            if not search_url:
                self.send_response(400)
                self.end_headers()
                return
            try:
                req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode('utf-8', errors='replace')
                prices = re.findall(r'(\d{1,3}(?:[.,]\d{3})+)\s*€', html)
                def parse_p(p): return int(p.replace('.', '').replace(',', ''))
                valid = sorted(list(set(parse_p(p) for p in prices if 1000 < parse_p(p) < 500000)))[:3]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "prices": [{"price": p} for p in valid]}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
            return

        super().do_GET()

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    with ThreadingSimpleServer(("", PORT), MyHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}")
        httpd.serve_forever()
