import pandas as pd
from bs4 import BeautifulSoup
import re
import os
import requests
from io import BytesIO

import sys

# Pfade
if len(sys.argv) > 3:
    xls_path = sys.argv[1]
    html_path = sys.argv[2]
    output_path = sys.argv[3]
else:
    xls_path = '/Users/zsoltsimon/Desktop/Gemini_Antigravity/antigravity-scratch/BCAGermanyCheetah_20260425..xls'
    html_path = '/Users/zsoltsimon/Desktop/Gemini_Antigravity/antigravity-scratch/bca_komplett.html'
    output_path = '/Users/zsoltsimon/Desktop/Gemini_Antigravity/antigravity-scratch/BCA_Enriched_20260425.xlsx'

temp_img_dir = os.path.join(os.path.dirname(output_path), 'temp_images')

def process_bca():
    if not os.path.exists(temp_img_dir):
        os.makedirs(temp_img_dir)

    # 1. HTML parsen
    print("Lese HTML-Datei...")
    # Versuche UTF-8, dann Latin-1
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(html_path, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()

    print("Suche nach Fahrzeug-Listings...")
    # RTF/HTML Cleaning
    content = content.replace('\\<', '<').replace('\\>', '>').replace('\\"', '"').replace('\\/', '/')
    content = re.sub(r"\\'([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), content)
    
    # Listings extrahieren
    listing_blocks = re.split(r'(?=<div class="listing")', content)
    
    extracted_data = []
    print(f"Gefundene Blöcke: {len(listing_blocks)}")

    for block in listing_blocks:
        if '<div class="listing"' not in block: continue
        
        # Katalognummer
        lot_match = re.search(r'Katalognummer\s*(\d+)', block)
        lot_no = int(lot_match.group(1)) if lot_match else None
            
        # Bild
        img_match = re.search(r'<img[^>]+src="([^"]+)"', block)
        img_url = ""
        if img_match:
            src = img_match.group(1).replace('\\', '').replace('&amp;', '&')
            img_url = "https:" + src if src.startswith('//') else src
            # Upgrade quality
            img_url = img_url.replace('width=100', 'width=800').replace('minwidth=600', 'minwidth=800')
            if 'width=' not in img_url:
                img_url += '&width=800&minwidth=800'
            
        # Preis
        price = ""
        p_match = re.search(r'>\s*([\d.]+)\s*(?:€|\x80|â‚¬|EUR)', block)
        if p_match:
            price = p_match.group(1) + " €"

        if lot_no:
            extracted_data.append({
                'Katalognummer': lot_no,
                'BCA_Bild_URL': img_url,
                'BCA_Preis': price
            })

    df_html = pd.DataFrame(extracted_data).drop_duplicates(subset=['Katalognummer'])
    print(f"{len(df_html)} eindeutige Fahrzeuge aus HTML extrahiert.")

    # 2. XLS laden mit Header-Erkennung
    print("Lese Excel-Datei...")
    header_idx = 0
    temp_df = pd.read_excel(xls_path, header=None, nrows=20)
    for i, row in temp_df.iterrows():
        if any("Katalognummer" in str(val) for val in row.values):
            header_idx = i
            print(f"Header in Zeile {i} gefunden.")
            break
            
    df_xls = pd.read_excel(xls_path, header=header_idx)

    # 3. Zusammenführen
    df_xls['Katalognummer_Num'] = pd.to_numeric(df_xls['Katalognummer'], errors='coerce')
    df_final = pd.merge(df_xls, df_html, left_on='Katalognummer_Num', right_on='Katalognummer', how='left')

    # 4. Mit XlsxWriter speichern und Bilder einbetten
    print("Erstelle Excel-Datei mit eingebetteten Bildern...")
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    df_final.to_excel(writer, sheet_name='Fahrzeuge', index=False)
    
    workbook = writer.book
    worksheet = writer.sheets['Fahrzeuge']
    
    # Spaltenbreite für Bild-Spalte setzen
    img_col_idx = len(df_final.columns)
    worksheet.set_column(img_col_idx, img_col_idx, 20)
    worksheet.write(0, img_col_idx, 'Fahrzeugbild')

    for idx, row in df_final.iterrows():
        url = row['BCA_Bild_URL']
        if pd.notna(url) and url:
            try:
                # Bild herunterladen
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    img_name = f"img_{row['Katalognummer_Num']}.jpg"
                    img_path = os.path.join(temp_img_dir, img_name)
                    with open(img_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Bild einfügen (skaliert)
                    worksheet.set_row(idx + 1, 100) # Zeilenhöhe anpassen
                    worksheet.insert_image(idx + 1, img_col_idx, img_path, {
                        'x_scale': 0.15, 
                        'y_scale': 0.15,
                        'x_offset': 5,
                        'y_offset': 5,
                        'object_position': 1
                    })
            except Exception as e:
                print(f"Fehler beim Bild für Kat-Nr {row['Katalognummer_Num']}: {e}")

    writer.close()
    print(f"Erfolg! Datei gespeichert unter: {output_path}")
    
    found_count = df_final['BCA_Bild_URL'].notna().sum()
    print(f"Abgleich-Ergebnis: {found_count} von {len(df_xls)} Fahrzeugen ergänzt.")

if __name__ == "__main__":
    process_bca()
