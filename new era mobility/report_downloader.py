import os
import re
import sys
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError
import pandas as pd

def download_report(listing_url, filename_prefix=None, browser_context=None):
    if not listing_url or not isinstance(listing_url, str):
        return
        
    if not listing_url.startswith(('http://', 'https://')):
        listing_url = 'https://' + listing_url
        
    update_status(f"Analysiere: {listing_url}")
    print(f"Analyzing listing: {listing_url}")
    
    # Try to fetch the listing page
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Please run: pip install playwright && playwright install chromium")
        return

    if browser_context:
        # Reuse existing context
        _handle_page(listing_url, browser_context, filename_prefix=filename_prefix)
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            _handle_page(listing_url, context, filename_prefix=filename_prefix)
            browser.close()

def _handle_page(listing_url, context, filename_prefix=None):
    page = context.new_page()
    
    # Define cookie acceptance handler
    cookie_selector = '#onetrust-accept-btn-handler'
    
    try:
        # Modern Playwright versions support automatic locator handlers for overlays
        if hasattr(page, "add_locator_handler"):
            page.add_locator_handler(
                page.locator(cookie_selector),
                lambda: page.locator(cookie_selector).click()
            )
        
        print(f"Opening: {listing_url}")
        try:
            page.goto(listing_url, wait_until='networkidle', timeout=60000)
            print("Page loaded (networkidle). Now waiting 5s for full initialization...")
        except Exception as e:
            print(f"Initial goto failed or timed out, but continuing: {e}")
            
        # Extra Wartezeit hinzufügen, damit BCA die Seite und Buttons komplett aufbauen kann
        page.wait_for_timeout(5000)
        print("5s wait completed. Starting to search for PDF links...")
            
        # Define targets to find and download
        targets = [
            {
                "id": "condition",
                "selectors": [
                    'a:has-text("Zustandsbericht")',
                    'a:has-text("Technischer Bericht")',
                    'a:has-text("Condition Report")',
                    'a[href*="bcaimage.com"]',
                    'a[href*="GetDoc.aspx"]'
                ],
                "file_prefix": "Zustandsbericht"
            },
            {
                "id": "vehicle_details",
                "selectors": [
                    'a:has-text("Fahrzeug PDF")',
                    'a:has-text("Fahrzeugdaten")',
                    'a:has-text("Vehicle PDF")',
                    'a:has-text("Details PDF")',
                    'a:has-text("Fahrzeug-Exposé")',
                    'a:has-text("Fahrzeugbeschreibung")',
                    'a:has-text("Drucken")',
                    'a:has-text("Print")',
                    'a[title*="Fahrzeugdaten"]',
                    'a[title*="PDF"]'
                ],
                "file_prefix": "Fahrzeugdaten"
            }
        ]

        # Wait loop to allow user to log in if needed and find links
        max_wait = 60 
        wait_step = 2
        waited = 0
        
        found_docs = [] # List of {url, file_prefix}

        while waited < max_wait:
            current_found_count = len(found_docs)
            for target in targets:
                # Check if we already found this type in our list
                if any(d['file_prefix'] == target['file_prefix'] for d in found_docs):
                    continue
                
                for selector in target['selectors']:
                    try:
                        el = page.locator(selector).first
                        if el.is_visible(timeout=500):
                            href = el.get_attribute("href")
                            if href:
                                full_url = urllib.parse.urljoin(listing_url, href)
                                found_docs.append({
                                    "url": full_url,
                                    "file_prefix": target['file_prefix'],
                                    "element": el # Store element for click fallback
                                })
                                print(f"Found {target['file_prefix']} link!")
                                break
                    except:
                        continue
            
            # If we found at least the condition report (main goal), we could continue
            # But let's try to find both until timeout or both found
            if len(found_docs) == len(targets):
                break
                
            if waited == 0:
                print("Searching for PDF links. Please log in if prompted in the browser window.")
            
            page.wait_for_timeout(wait_step * 1000)
            waited += wait_step

        if not found_docs:
            print("Error: No PDF documents found even after waiting. Please check your login status.")
            return

    except Exception as e:
        import traceback
        print(f"Error during page interaction: {e}")
        traceback.print_exc()
        return

    # Create reports directory
    if sys.platform == "win32":
        reports_dir = "D:\\BCA_Reports"
        if not os.path.exists("D:\\"):
            reports_dir = "reports"
    else:
        # macOS/Linux: Use Downloads folder
        reports_dir = os.path.expanduser("~/Downloads/BCA_Reports")
    
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir, exist_ok=True)

    # Process each found document
    for doc in found_docs:
        r_url = doc['url']
        prefix = doc['file_prefix']
        el = doc['element']
        
        print(f"\nProcessing {prefix} for: {r_url}")
        
        # Determine specific filename
        file_name = f"{prefix}_{filename_prefix}.pdf" if filename_prefix else f"{prefix}_download.pdf"
        save_path = os.path.join(reports_dir, file_name)

        # Browser UI Interaction
        try:
            # 1. Try regular download
            try:
                # Erhöhe Timeout auf 60 Sekunden (PDF-Generierung kann bei BCA lange dauern)
                with page.expect_download(timeout=60000) as download_info:
                    print(f"Clicking link for {prefix} (expecting direct download)...")
                    # Scrolle zum Element, um sicherzustellen, dass es klickbar ist
                    el.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000) # Kurze Pause nach dem Scrollen
                    el.click(modifiers=["Alt"]) # Try to force download
                download = download_info.value
                download.save_as(save_path)
                print(f"Success: {save_path} (Direct Download)")
                continue
            except Exception as e:
                print(f"No direct download: {e}")

            # 2. Try popup (BCA often opens PDF in a new tab)
            try:
                with page.expect_popup(timeout=60000) as popup_info:
                    print(f"Clicking link for {prefix} (expecting popup)...")
                    el.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    el.click()
                popup = popup_info.value
                print(f"Popup opened for {prefix}. Waiting 60s for PDF generation...")
                try:
                    popup.wait_for_load_state("networkidle", timeout=60000)
                except:
                    print("Popup networkidle timeout, but continuing...")
                
                # Warte 60 Sekunden im Popup-Fenster, wie vom User gewünscht
                popup.wait_for_timeout(60000)
                
                # Fetch the URL of the popup
                resp = popup.request.get(popup.url)
                if 'pdf' in resp.headers.get('content-type', '').lower():
                    with open(save_path, 'wb') as f:
                        f.write(resp.body())
                    print(f"Success: {save_path} (Popup Content)")
                else:
                    print(f"Popup content is not PDF: {resp.headers.get('content-type')}")
                popup.close()
                continue
            except Exception as e:
                print(f"No popup generated: {e}")
                
            # 3. Final Fallback (only if it's actually a PDF)
            print("Attempting final direct request fallback...")
            res = page.request.get(r_url)
            if 'pdf' in res.headers.get('content-type', '').lower():
                with open(save_path, 'wb') as f:
                    f.write(res.body())
                print(f"Success: {save_path} (Final Fallback)")
            else:
                print(f"Final fallback failed. URL does not return a PDF (Type: {res.headers.get('content-type')})")

        except Exception as e:
            print(f"Browser interaction failed for {prefix}: {e}")
                
    page.close()


def update_status(message):
    try:
        # Use a consistent path relative to the script
        with open('status.txt', 'w', encoding='utf-8') as f:
            f.write(message)
    except Exception as e:
        print(f"Status update error: {e}")

def process_excel(file_path):
    update_status(f"Dateieinlesen wurde gestartet...")
    print(f"Reading Excel file: {file_path}")
    try:
        # Read Excel: Column C (index 2) and Column AB (index 27)
        # Rows 8 to 208 (skip 7 rows, read 201)
        df = pd.read_excel(file_path, header=None, usecols=[2, 27], skiprows=7, nrows=201)
        
        # Collect data: (prefix, url) until the first empty URL row is encountered
        batch_data = []
        for _, row in df.iterrows():
            prefix = str(row[2]).strip() if pd.notna(row[2]) else ""
            url = str(row[27]).strip() if pd.notna(row[27]) else ""
            
            if not url or url.lower() == 'nan':
                break
            batch_data.append((prefix, url))
        
        print(f"Found {len(batch_data)} URLs in column AB.")
        
        if not batch_data:
            print("No URLs found to process.")
            return

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            )
            
            for i, (prefix, url) in enumerate(batch_data):
                msg = f"Verarbeite Zeile {i+8} (ID: {prefix}, URL {i+1} von {len(batch_data)}): {url}"
                update_status(msg)
                print(f"\n--- {msg} ---")
                
                try:
                    download_report(url, filename_prefix=prefix, browser_context=context)
                except Exception as e:
                    print(f"Error processing {url}: {e}")
            
            update_status("Batch abgeschlossen.")
            browser.close()
            print("\nBatch processing completed.")

    except Exception as e:
        print(f"Error reading Excel file: {e}")

if __name__ == "__main__":
    if "--excel" in sys.argv:
        try:
            excel_idx = sys.argv.index("--excel") + 1
            if excel_idx < len(sys.argv):
                process_excel(sys.argv[excel_idx])
            else:
                print("Error: No excel file path provided after --excel")
        except Exception as e:
            print(f"CLI Error: {e}")
    elif len(sys.argv) > 1:
        url = sys.argv[1]
        download_report(url)
    else:
        url = input("Please enter the car listing URL or --excel [path]: ").strip()
        if url.startswith("--excel "):
             process_excel(url.replace("--excel ", "").strip())
        elif url:
            download_report(url)
        else:
            print("No URL provided.")

