import pandas as pd
from bs4 import BeautifulSoup
import re
import math
import argparse
import sys
import os
import json
import html as html_lib
from datetime import datetime, timedelta

def parse_args():
    parser = argparse.ArgumentParser(description='BCA Daten Mergen')
    parser.add_argument('--xls', type=str, default='BCAGermanyCheetah_20260425..xls')
    parser.add_argument('--html', type=str, default='bca_komplett.html')
    parser.add_argument('--out', type=str, default='index.html')
    parser.add_argument('--archive-days', type=int, default=30, help='How many days to keep vehicles in the archive')
    parser.add_argument('--price-col', type=str, default=None, help='Specific Excel column to use for Netto Price')
    return parser.parse_args()

def parse_expiry_date(listing_html):
    listing_html = html_lib.unescape(str(listing_html))
    now = datetime.now()
    year = now.year
    
    # Try "Ende: 28.04.2025 10:00" (with year)
    ende_match = re.search(r'Ende:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', listing_html)
    if ende_match:
        day, month, yr, hour, minute = map(int, ende_match.groups())
        if yr >= 2024 and yr <= 2030:
            return datetime(yr, month, day, hour, minute).strftime('%Y-%m-%d %H:%M:%S')

    # Try "Ende: 28.04 10:00" (without year)
    ende_match = re.search(r'Ende:\s*(\d{2})\.(\d{2})\s+(\d{2}):(\d{2})', listing_html)
    if ende_match:
        day, month, hour, minute = map(int, ende_match.groups())
        expiry = datetime(year, month, day, hour, minute)
        if expiry < now - timedelta(days=1):
            expiry = expiry.replace(year=year + 1)
        return expiry.strftime('%Y-%m-%d %H:%M:%S')

    # Try "Ende: 28.04.25 10:00" (short year)
    ende_match = re.search(r'Ende:\s*(\d{2})\.(\d{2})\.(\d{2})\s+(\d{2}):(\d{2})', listing_html)
    if ende_match:
        day, month, yr, hour, minute = map(int, ende_match.groups())
        yr += 2000
        if yr >= 2024 and yr <= 2030:
            return datetime(yr, month, day, hour, minute).strftime('%Y-%m-%d %H:%M:%S')

    # Try "Auktionsende: DD.MM.YYYY HH:MM" or "Endet: DD.MM.YYYY HH:MM"
    ende_match = re.search(r'(?:Auktionsende|Endet|Laufzeit|Läuft bis):?\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})', listing_html)
    if ende_match:
        day, month, yr, hour, minute = map(int, ende_match.groups())
        if yr >= 2024 and yr <= 2030:
            return datetime(yr, month, day, hour, minute).strftime('%Y-%m-%d %H:%M:%S')

    # Try "3Tag(e) 0Std. 21Min."
    countdown_match = re.search(r'(\d+)Tag\(e\)\s*(\d+)Std\.\s*(\d+)Min\.', listing_html)
    if countdown_match:
        days, hours, mins = map(int, countdown_match.groups())
        expiry = now + timedelta(days=days, hours=hours, minutes=mins)
        return expiry.strftime('%Y-%m-%d %H:%M:%S')

    # Try German "0 Tage 1 Stunden 0 Minuten"
    countdown_match = re.search(r'(\d+)\s*Tage?\s*(\d+)\s*Stunden?\s*(\d+)\s*Minuten?', listing_html, re.IGNORECASE)
    if countdown_match:
        days, hours, mins = map(int, countdown_match.groups())
        expiry = now + timedelta(days=days, hours=hours, minutes=mins)
        return expiry.strftime('%Y-%m-%d %H:%M:%S')

    # Try German "2Std. 42Min." countdowns
    countdown_match = re.search(r'(\d+)\s*Std\.?\s*(\d+)\s*Min\.?', listing_html, re.IGNORECASE)
    if countdown_match:
        hours, mins = map(int, countdown_match.groups())
        expiry = now + timedelta(hours=hours, minutes=mins)
        return expiry.strftime('%Y-%m-%d %H:%M:%S')

    # Try JSON countdown attributes like data-bid-session-start-date
    json_match = re.search(r'data-bid-session-start-date\s*=\s*\'(\{[^\']+\})\'|data-bid-session-start-date\s*=\s*"(\{[^\"]+\})"', listing_html)
    if json_match:
        json_text = json_match.group(1) or json_match.group(2)
        try:
            data = json.loads(html_lib.unescape(json_text).replace("'", '"'))
            days = int(data.get('Days', 0))
            hours = int(data.get('Hours', 0))
            mins = int(data.get('Minutes', 0))
            expiry = now + timedelta(days=days, hours=hours, minutes=mins)
            return expiry.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
    
    # Try href or label-based duration text
    countdown_match = re.search(r'Auktion endet in:\s*<div[^>]*>([^<]+)<', listing_html, re.IGNORECASE)
    if countdown_match:
        inner = countdown_match.group(1)
        return parse_expiry_date(inner)

    return None


def extract_sheet_expiry(df_temp):
    """Find a sheet-level expiry date from metadata rows in the raw Excel sheet."""
    if df_temp is None:
        return None

    for _, row in df_temp.iterrows():
        for idx, cell in row.items():
            if isinstance(cell, str) and 'enddatum' in cell.lower():
                try:
                    candidate = row.iloc[idx + 1]
                except Exception:
                    candidate = None
                if candidate is not None and str(candidate).strip():
                    parsed = extract_expiry_from_row(pd.Series({0: candidate}))
                    if parsed:
                        return parsed
    return None


def extract_expiry_from_row(row):
    """Try to extract an expiry datetime from a pandas Series (row).
    Handles explicit columns (like 'F5', 'Ende', 'Auktionsende'), Excel serials,
    unix timestamps and free-form date strings.
    Returns an ISO formatted string or None.
    """
    if row is None:
        return None

    def format_dt(dt):
        try:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return None

    def try_parse_value(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        # pandas Timestamp or datetime
        if hasattr(val, 'to_pydatetime'):
            try:
                return format_dt(pd.to_datetime(val).to_pydatetime())
            except:
                pass
        if isinstance(val, datetime):
            return format_dt(val)
        # Numeric: could be excel serial or unix timestamp
        if isinstance(val, (int, float)) and not pd.isna(val):
            try:
                ival = float(val)
                # Unix seconds
                if ival > 1e9:
                    try:
                        return format_dt(datetime.fromtimestamp(int(ival)))
                    except:
                        pass
                # Excel serial (days since 1899-12-30)
                if ival > 20000 and ival < 60000:
                    try:
                        base = datetime(1899, 12, 30)
                        days = int(ival)
                        frac = ival - days
                        secs = int(round(frac * 86400))
                        dt = base + timedelta(days=days, seconds=secs)
                        return format_dt(dt)
                    except:
                        pass
            except:
                pass
        # String: try parse_expiry_date (HTML-like) first
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return None
            now = datetime.now()
            year = now.year
            # Some strings include the label 'Ende:' etc.
            parsed = parse_expiry_date(s)
            if parsed:
                return parsed
            # Try plain German date/time without year: 22.05 13:59
            short_match = re.match(r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$', s)
            if short_match:
                day, month, hour, minute = map(int, short_match.groups())
                expiry = datetime(year, month, day, hour, minute)
                if expiry < now - timedelta(days=1):
                    expiry = expiry.replace(year=year + 1)
                return format_dt(expiry)
            # Try pandas parser (dayfirst)
            try:
                dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
                if not pd.isna(dt):
                    return format_dt(dt.to_pydatetime())
            except:
                pass
        return None

    # 1) look for likely column names
    for col in row.index:
        low = str(col).lower()
        if any(key in low for key in ['f5', 'ende', 'auktions', 'endet', 'laufzeit', 'läuft', 'endzeit', 'expiry', 'ablauf']):
            val = row.get(col)
            res = try_parse_value(val)
            if res:
                return res

    # 2) try some specific common column labels if present
    common_cols = ['expiry_date', 'expiry', 'Ende', 'Auktionsende', 'Endet', 'Ende Datum']
    for cname in common_cols:
        if cname in row.index:
            res = try_parse_value(row.get(cname))
            if res: return res

    # 3) fallback: scan all values for something that parses
    for col in row.index:
        val = row.get(col)
        res = try_parse_value(val)
        if res:
            return res

    return None

TRANSPORT_COSTS = {
    "Bad Hersfeld": {"pkw": 374, "suv": 487, "lcv": 537},
    "BCA Berlin / Hoppegarten": {"pkw": 402, "suv": 522, "lcv": 572},
    "BCA Heidenheim": {"pkw": 253, "suv": 329, "lcv": 379},
    "BCA Neuss": {"pkw": 484, "suv": 630, "lcv": 680},
    "Bitterfeld-Wolfen": {"pkw": 402, "suv": 522, "lcv": 572},
    "Bochum": {"pkw": 501, "suv": 651, "lcv": 701},
    "Brackel": {"pkw": 490, "suv": 637, "lcv": 687},
    "Braunschweig": {"pkw": 490, "suv": 637, "lcv": 687},
    "Bremen": {"pkw": 523, "suv": 680, "lcv": 730},
    "Buch": {"pkw": 253, "suv": 329, "lcv": 379},
    "Calden": {"pkw": 484, "suv": 630, "lcv": 680},
    "Dorfmark / Hartmann Bad Fallingbostel": {"pkw": 490, "suv": 637, "lcv": 687},
    "Dortmund": {"pkw": 484, "suv": 630, "lcv": 680},
    "Duisburg": {"pkw": 484, "suv": 630, "lcv": 680},
    "Duisburg Salloum": {"pkw": 484, "suv": 630, "lcv": 680},
    "Düren": {"pkw": 479, "suv": 623, "lcv": 673},
    "Düsseldorf": {"pkw": 484, "suv": 630, "lcv": 680},
    "Emmering": {"pkw": 197, "suv": 256, "lcv": 306},
    "Hakenstedt": {"pkw": 407, "suv": 530, "lcv": 580},
    "Illingen": {"pkw": 253, "suv": 329, "lcv": 379},
    "Kerpen": {"pkw": 468, "suv": 608, "lcv": 658},
    "Ketzin": {"pkw": 402, "suv": 522, "lcv": 572},
    "Kitzingen": {"pkw": 253, "suv": 329, "lcv": 379},
    "Krefeld ARS": {"pkw": 484, "suv": 630, "lcv": 680},
    "Lähden": {"pkw": 484, "suv": 630, "lcv": 680},
    "Leipzig-Knautnaundorf ARS": {"pkw": 402, "suv": 522, "lcv": 572},
    "Lüdersfeld": {"pkw": 490, "suv": 637, "lcv": 687},
    "Mönchengladbach": {"pkw": 495, "suv": 644, "lcv": 694},
    "Mücke": {"pkw": 396, "suv": 515, "lcv": 565},
    "Neuss ATN": {"pkw": 484, "suv": 630, "lcv": 680},
    "Niederaula - Hartmann": {"pkw": 374, "suv": 487, "lcv": 537},
    "Nürnberg": {"pkw": 253, "suv": 329, "lcv": 379},
    "Oberndorf am Neckar": {"pkw": 330, "suv": 429, "lcv": 479},
    "Rackwitz": {"pkw": 402, "suv": 522, "lcv": 572},
    "Rehden": {"pkw": 484, "suv": 630, "lcv": 680},
    "Riedstadt ARS": {"pkw": 374, "suv": 487, "lcv": 537},
    "Schkopau": {"pkw": 402, "suv": 522, "lcv": 572},
    "Schöneck-Kilianstädten": {"pkw": 374, "suv": 487, "lcv": 537},
    "Seddiner See": {"pkw": 391, "suv": 508, "lcv": 558},
    "Wegberg": {"pkw": 484, "suv": 630, "lcv": 680},
    "Wiedemar": {"pkw": 402, "suv": 522, "lcv": 572},
    "Wolnzach": {"pkw": 204, "suv": 265, "lcv": 315},
    "Zörbig": {"pkw": 402, "suv": 522, "lcv": 572},
    "Zülpich": {"pkw": 473, "suv": 615, "lcv": 665},
    "Denmark": {"pkw": 400, "suv": 520, "lcv": 570}
}

def calculate_final_price_data(netto_preis, location, karosserie):
    if netto_preis is None or pd.isna(netto_preis): netto_preis = 0
    brutto_basis_de = netto_preis * 1.19
    auction_percent = brutto_basis_de * 0.035
    auction_fix = 140
    karosserie_low = str(karosserie).lower()
    is_lcv = any(word in karosserie_low for word in ['kasten', 'lcv', 'transporter', 'van', 'pritsche', 'pick-up'])
    is_suv = any(word in karosserie_low for word in ['suv', 'gelände', 'off-road', 'offroad', 'pickup'])
    car_type = "lcv" if is_lcv else ("suv" if is_suv else "pkw")
    transport_cost = 600
    location_clean = str(location).strip()
    if location_clean in TRANSPORT_COSTS: 
        transport_cost = TRANSPORT_COSTS[location_clean].get(car_type, TRANSPORT_COSTS[location_clean]['pkw'])
    else:
        for loc_name in TRANSPORT_COSTS:
            if loc_name in location_clean or location_clean in loc_name:
                transport_cost = TRANSPORT_COSTS[loc_name].get(car_type, TRANSPORT_COSTS[loc_name]['pkw'])
                break
    import_fee = 800
    commission = max(500, netto_preis * 0.02)
    total_netto = netto_preis + auction_percent + auction_fix + (transport_cost * 1.5) + import_fee + commission
    total_brutto_at = total_netto * 1.20
    return {
        "netto_basis": netto_preis,
        "auction_percent": auction_percent,
        "auction_fix": auction_fix,
        "transport": transport_cost,
        "import_fee": import_fee,
        "total_netto": total_netto,
        "total_brutto_at": total_brutto_at,
        "car_type": car_type.upper()
    }

WARRANTY_DATA = {
    'A': {
        200: {'Standard': 149, 'Komfort': 279, 'Premium': 429},
        235: {'Standard': 269, 'Komfort': 429, 'Premium': 729},
        350: {'Standard': 389, 'Komfort': 529, 'Premium': 929},
    },
    'B': {
        200: {'Standard': 199, 'Komfort': 329, 'Premium': 479},
        235: {'Standard': 319, 'Komfort': 479, 'Premium': 779},
        350: {'Standard': 439, 'Komfort': 579, 'Premium': 979},
    },
    'C': {
        200: {'Standard': 249, 'Komfort': 379, 'Premium': 529},
        235: {'Standard': 369, 'Komfort': 529, 'Premium': 829},
        350: {'Standard': 489, 'Komfort': 629, 'Premium': 1029},
    }
}

def calculate_warranty_prices(ps, age, km, fuel_type="", weight=0):
    try:
        kw = int(float(ps) / 1.36)
    except:
        kw = 0
    
    fuel_low = str(fuel_type).lower()
    is_electric = "elektro" in fuel_low
    is_alt = any(word in fuel_low for word in ['hybrid', 'plug-in', 'lpg', 'erdgas', 'cng', 'gas'])

    # Power check (<= 350 kW)
    if kw > 350:
        return None
        
    # Weight check (placeholder, if data available)
    if is_electric and weight > 3500:
        return None

    # Determine Category
    category = None
    if age <= 8 and km <= 150000:
        category = 'A'
    elif age <= 10 and km <= 200000:
        category = 'B'
    elif age <= 15 and km <= 200000:
        category = 'C'
    
    if not category:
        return None
    
    # Determine Power Group
    power_group = 350
    if kw <= 200: power_group = 200
    elif kw <= 235: power_group = 235
    
    prices = WARRANTY_DATA[category][power_group].copy()
    
    # Electric Specific: Forbidden Standard Tariff
    if is_electric:
        if 'Standard' in prices:
            del prices['Standard']
    
    # Surcharge (+30%)
    if is_alt or is_electric:
        for k in prices:
            prices[k] = int(prices[k] * 1.30)
    
    # Final 50% Margin (Hidden)
    for k in prices:
        prices[k] = int(prices[k] * 1.50)
            
    return prices

def update_archive(new_data, days_limit):
    archive_path = 'sold_archive.json'
    now = pd.Timestamp.now()
    
    # 1. Load existing archive
    archive = []
    if os.path.exists(archive_path):
        try:
            with open(archive_path, 'r', encoding='utf-8') as f:
                archive = json.load(f)
        except:
            archive = []

    # 2. Add current date to new entries and merge
    archive_map = {str(item.get('uid')): item for item in archive if 'uid' in item}
    
    for item in new_data:
        item_uid = str(item.get('uid'))
        if item_uid in archive_map:
            # Keep original archive_date
            item['archive_date'] = archive_map[item_uid].get('archive_date', now.strftime('%Y-%m-%d'))
        else:
            item['archive_date'] = now.strftime('%Y-%m-%d')
        archive_map[item_uid] = item

    # 3. Filter by date limit
    final_archive = []
    limit_date = now - pd.Timedelta(days=days_limit)
    
    for item in archive_map.values():
        try:
            item_date = pd.to_datetime(item.get('archive_date', now.strftime('%Y-%m-%d')))
            if item_date >= limit_date:
                final_archive.append(item)
        except:
            final_archive.append(item)
    
    # Sort by ID (numeric)
    try:
        final_archive.sort(key=lambda x: int(x['id']))
    except:
        pass

    # 4. Save back to file
    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(final_archive, f, ensure_ascii=False, indent=4)
    
    print(f"Archiv aktualisiert: {len(final_archive)} Fahrzeuge gespeichert.")
    return final_archive

def process_bca():
    args = parse_args()
    xls_path = args.xls
    html_path = args.html
    output_html_path = args.out

    try:
        df_temp = pd.read_excel(xls_path, header=None)
        header_row_idx = None
        for i, row in df_temp.iterrows():
            if "Katalognummer" in row.values:
                header_row_idx = i
                break
        df = pd.read_excel(xls_path, skiprows=header_row_idx)
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(html_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
        content = content.replace('\\<', '<').replace('\\>', '>').replace('\\"', '"').replace('\\/', '/')
        content = re.sub(r"\\'([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), content)
        content = html_lib.unescape(content)

        sheet_expiry = extract_sheet_expiry(df_temp)
        listings = re.split(r'(?=<div class="listing")', content)
        extracted_html_data = []
        for l in listings:
            if '<div class="listing"' not in l: continue
            lot_match = re.search(r'Katalognummer\s*([0-9]+)', l)
            img_match = re.search(r'<img[^>]+src="([^"]+)"', l)
            if lot_match:
                img_url = img_match.group(1) if img_match else ""
                if img_url:
                    if img_url.startswith('//'): img_url = 'https:' + img_url
                    img_url = img_url.replace('width=100', 'width=800').replace('minwidth=600', 'minwidth=800')
                    if 'width=' not in img_url: img_url += '&width=800&minwidth=800'
                extracted_html_data.append({
                    "Katalognummer": int(lot_match.group(1)),
                    "BCA_Bild_URL": img_url,
                    "BCA_Standort": "Unbekannt",
                    "BCA_HTML_Price": 0.0,
                    "expiry_date": parse_expiry_date(l) or sheet_expiry
                })
                p_match = re.search(r'>\s*([\d.]+)\s*(?:€|\x80|â‚¬|EUR)', l)
                if p_match: extracted_html_data[-1]["BCA_HTML_Price"] = float(p_match.group(1).replace('.', ''))
                loc_match = re.search(r'flag--[A-Z]{2}[^>]*></i>.*?<span>(.*?),', l)
                if not loc_match: loc_match = re.search(r'<span>\s*([^<,]+?)\s*,\s*Katalognummer', l)
                if loc_match:
                    loc_raw = loc_match.group(1).split('(')[-1].split(';')[0].replace('Austria)', '').replace('GERMANY -', '').strip()
                    extracted_html_data[-1]["BCA_Standort"] = loc_raw

        if len(extracted_html_data) > 0:
            df_html = pd.DataFrame(extracted_html_data).drop_duplicates(subset=['Katalognummer'])
        else:
            df_html = pd.DataFrame(columns=['Katalognummer'])
        df['Katalognummer_Num'] = pd.to_numeric(df['Katalognummer'], errors='coerce')
        final_df = pd.merge(df, df_html, left_on='Katalognummer_Num', right_on='Katalognummer', how='left')
        
        def clean_val(val, default=""):
            if pd.isna(val): return default
            return val

        # Load Archive for ID consistency
        archive_path = 'sold_archive.json'
        archive = []
        if os.path.exists(archive_path):
            try:
                with open(archive_path, 'r', encoding='utf-8') as f:
                    archive = json.load(f)
            except: pass
        
        archive_map = {str(item.get('uid')): item for item in archive if 'uid' in item}
        max_id = 0
        for item in archive:
            try:
                vid = int(item['id'])
                if vid > max_id: max_id = vid
            except: pass
        next_new_id = max_id + 1

        js_data = []
        for _, row in final_df.iterrows():
            item_uid = str(clean_val(row.get('Inventarnummer', row.get('Katalognummer_Num', '')))).strip()
            
            # Determine Unique ID
            if item_uid in archive_map:
                car_id = archive_map[item_uid]['id']
            else:
                car_id = str(next_new_id)
                next_new_id += 1

            html_price = row.get('BCA_HTML_Price', 0.0)
            args = parse_args()
            if args.price_col and args.price_col in row:
                p_raw = str(row.get(args.price_col, '0'))
                p_netto = float(re.sub(r'[^\d.]', '', p_raw.replace('.', '').replace(',', '.')) or 0)
            elif not pd.isna(html_price) and html_price > 0:
                p_netto = float(html_price)
            else:
                p_raw = str(row.get('Aktuelles Gebot') or row.get('Netto-Preis') or row.get('BCA Netto') or row.get('Ist-Preis') or row.get('Startpreis') or '0')
                p_netto = float(re.sub(r'[^\d.]', '', p_raw.replace('.', '').replace(',', '.')) or 0)
            km_val = row.get('KM Stand', 0)
            km_raw = 0
            if not pd.isna(km_val):
                try:
                    # Logik: Wenn der Wert Nachkommastellen hat (z.B. 67.738), 
                    # ist es ein falsch interpretierter Tausender-Punkt -> * 1000.
                    # Wenn es eine ganze Zahl ist (z.B. 327.0), sind es echte KM.
                    if km_val < 1000 and (km_val % 1) != 0:
                        km_raw = int(round(km_val * 1000))
                    else:
                        km_raw = int(km_val)
                except:
                    km_raw = 0

            km_str = f"{km_raw:,}".replace(',', '.') if not pd.isna(km_val) else "-"
            ps = str(row.get('PS', '-')).split('.')[0]
            aus1 = str(row.get('Ausstattung', '')).replace('nan', '')
            aus2 = str(row.get('Ausstattung 2', '')).replace('nan', '')
            aus_full = [a.strip() for a in (aus1 + (", " + aus2 if aus2 else "")).split(',') if a.strip()]
            
            year_raw = 0
            try:
                ez_str = str(row.get('Erstzulassung', ''))
                year_match = re.search(r'20\d{2}', ez_str)
                if year_match: year_raw = int(year_match.group(0))
            except: pass
            calc = calculate_final_price_data(p_netto, row.get('BCA_Standort', ''), row.get('Karosserietyp', ''))
            # Warranty Calculation
            age = 2026 - year_raw if year_raw > 0 else 99
            fuel_type = row.get('Kraftstoff', '')
            warranty_options = calculate_warranty_prices(ps, age, km_raw, fuel_type)

            # Expiry Date Logik: Prio 1 ist ein bereits vorhandener Zeitstempel
            expiry_final = row.get('expiry_date')
            # Falls durch den Merge Suffixe entstanden sind (expiry_date_x/y)
            if expiry_final is None or (isinstance(expiry_final, float) and pd.isna(expiry_final)):
                expiry_final = row.get('expiry_date_y', row.get('expiry_date_x', None))
            # Stelle sicher, dass NaN-Werte zu None werden
            if expiry_final is not None and isinstance(expiry_final, float) and pd.isna(expiry_final):
                expiry_final = None

            # Wenn noch kein Ablaufdatum vorhanden ist, versuche XLS-Fallback oder andere Spalten
            if expiry_final is None:
                try:
                    expiry_from_row = extract_expiry_from_row(row)
                    if expiry_from_row:
                        expiry_final = expiry_from_row
                except Exception:
                    expiry_final = None

            if expiry_final is None:
                expiry_final = sheet_expiry
            js_data.append({
                "id": car_id,
                "category": "Auktionsfahrzeuge",
                "name": f"{clean_val(row.get('Hersteller', ''))} {clean_val(row.get('Modell', ''))}".strip(),
                "ausfuehrung": str(clean_val(row.get('Ausführung', row.get('Ausstattungsvariante', '')))).replace('nan', ''),
                "img": clean_val(row.get('BCA_Bild_URL', ''), ''),
                "ez": str(clean_val(row.get('Erstzulassung', '-'))).replace('nan', '-'),
                "km": km_str,
                "km_raw": km_raw,
                "year_raw": year_raw,
                "ps": ps,
                "kraftstoff": str(clean_val(row.get('Kraftstoff', '-')))[:20],
                "ausstattung": aus_full[:6],
                "ausstattung_full": aus_full,
                "location": clean_val(row.get('BCA_Standort', 'Unbekannt'), 'Unbekannt'),
                "car_type": calc['car_type'],
                "bca_price": p_netto,
                "transport": calc['transport'],
                "details": calc,
                "warranty_options": warranty_options,
                "expiry_date": clean_val(expiry_final, None),
                "uid": item_uid,
                "verkaufspreis": archive_map[item_uid].get('verkaufspreis', 0) if item_uid in archive_map else 0,
                "raw_data": {str(k): (v if type(v) in (int, float, str, bool) else str(v)) for k, v in row.items() if pd.notna(v)}
            })

        # Update Local Archive
        update_archive(js_data, args.archive_days)

        html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/lucide@latest"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Outfit', sans-serif; background-color: #f8fafc; position: relative; min-height: 100vh; -webkit-font-smoothing: antialiased; }}
            .glass-card {{ background: white; border: 1px solid #e2e8f0; }}
            .calc-box {{ background: #f1f5f9; border: 1px dashed #cbd5e1; }}
            .ausstattung-badge {{ background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
            .filter-select {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 8px 12px; }}
            .glass-modal {{ background: white; backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.3); }}
            
            #toast {{ position: fixed; bottom: 2rem; right: 2rem; padding: 1rem 1.5rem; border-radius: 1rem; background: white; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; display: none; z-index: 9999; animation: slideUp 0.3s ease-out; }}
            @keyframes slideUp {{ from {{ transform: translateY(100%); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
            
            .sync-btn {{ background: #059669; color: white; transition: all 0.3s; cursor: pointer; }}
            .sync-btn:hover {{ background: #047857; transform: translateY(-1px); }}
            
            #modalScrollArea::-webkit-scrollbar {{ width: 6px; }}
            #modalScrollArea::-webkit-scrollbar-track {{ background: transparent; }}
            #modalScrollArea::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 10px; }}

            .message-hidden {{ display: none; opacity: 0; max-height: 0; overflow: hidden; }}
            .message-visible {{ display: block; opacity: 1; max-height: 200px; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }}
            
            .success-overlay {{ position: absolute; inset: 0; background: white; display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 200; opacity: 0; pointer-events: none; transition: opacity 0.5s ease; }}
            .success-overlay.active {{ opacity: 1; pointer-events: auto; }}
            
            .checkmark-circle {{ width: 80px; height: 80px; border-radius: 50%; background: #f0fdf4; display: flex; align-items: center; justify-content: center; margin-bottom: 1.5rem; transform: scale(0.5); transition: transform 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
            .success-overlay.active .checkmark-circle {{ transform: scale(1); }}

            input[type=number] {{ -moz-appearance: textfield; appearance: textfield; }}
            .timer-badge {{ transition: background-color 0.5s ease; }}

            @media (max-width: 480px) {{
                .card-padding {{ padding: 0.75rem !important; }}
                .card-title {{ font-size: 0.9rem !important; }}
                .card-specs {{ font-size: 9px !important; }}
            }}
            
            .multi-select-container {{ position: relative; }}
            .multi-select-dropdown {{ position: absolute; top: 100%; left: 0; width: 100%; background: white; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); z-index: 100; max-height: 250px; overflow-y: auto; display: none; padding: 0.5rem; }}
            .multi-select-dropdown.active {{ display: block; }}
            .multi-select-item {{ display: flex; items-center: center; gap: 0.5rem; padding: 0.5rem; border-radius: 8px; cursor: pointer; transition: background 0.2s; }}
            .multi-select-item:hover {{ background: #f1f5f9; }}
            .multi-select-item input {{ cursor: pointer; }}
        </style>
    </head>
    <body class="p-4 md:p-8 bg-slate-50 text-slate-800">
    <div id="wixContentWrapper">
        <div id="toast" onclick="this.style.display='none'">
        <div class="flex items-center gap-3">
            <div id="toastIcon"></div>
            <div id="toastMessage" class="text-sm font-bold"></div>
        </div>
    </div>

    <!-- Anfrage Modal -->
    <div id="modalBackdrop"
        class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] hidden flex items-start justify-center p-4 transition-opacity duration-300 opacity-0 min-h-full">
        <div id="modalContainer"
            class="max-w-2xl w-full glass-modal rounded-3xl shadow-2xl overflow-hidden transform transition-all duration-300 scale-95 opacity-0 flex flex-col max-h-[95vh] relative mt-10 md:mt-20">

            <!-- Success Overlay -->
            <div id="successOverlay" class="success-overlay">
                <div class="checkmark-circle">
                    <i data-lucide="check" class="w-10 h-10 text-emerald-600"></i>
                </div>
                <h3 class="text-2xl font-bold text-slate-800 mb-2">Anfrage gesendet!</h3>
                <p class="text-slate-500 text-center px-8">Wir melden uns in Kürze bei Ihnen.</p>
                <button onclick="closeModal()"
                    class="mt-8 px-8 py-3 bg-blue-600 text-white font-bold rounded-2xl shadow-lg">Schließen</button>
            </div>

            <!-- Modal Header -->
            <div class="relative h-32 md:h-48 bg-slate-100 flex-shrink-0">
                <img id="modalCarImg" src="" class="w-full h-full object-cover" alt="Auto">
                <div class="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent"></div>
                <button onclick="closeModal()"
                    class="absolute top-4 right-4 p-2 bg-white/80 hover:bg-white rounded-full text-slate-600 shadow-sm">
                    <i data-lucide="x" class="w-6 h-6"></i>
                </button>
                <div class="absolute bottom-4 left-6 md:left-8">
                    <h3 id="modalCarName" class="text-xl md:text-2xl font-bold text-slate-800 leading-tight">...</h3>
                    <p class="text-xs md:text-sm text-slate-500 font-medium">ID: <span id="modalCarId">...</span></p>
                </div>
            </div>

            <!-- Modal Content -->
            <div id="modalScrollArea" class="p-4 md:p-8 pt-4 overflow-y-auto flex-grow">
                <div class="space-y-4 md:space-y-6">
                    <div class="grid grid-cols-1 gap-3">
                        <label
                            class="flex items-center gap-4 p-4 rounded-2xl bg-white border border-slate-100 hover:border-blue-200 transition-all cursor-pointer group">
                            <input type="checkbox" id="checkEmail" onchange="validateForm()"
                                class="w-5 h-5 text-blue-600 border-slate-300 rounded">
                            <div class="flex flex-col">
                                <span
                                    class="text-slate-800 font-semibold text-sm md:text-base group-hover:text-blue-600 transition-colors">Zustandsbericht</span>
                                <span class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Per E-Mail
                                    erhalten</span>
                            </div>
                        </label>

                        <label
                            class="flex items-center gap-4 p-4 rounded-2xl bg-white border border-slate-100 hover:border-blue-200 transition-all cursor-pointer group">
                            <input type="checkbox" id="checkImport"
                                onchange="toggleMessageField(this.checked); validateForm()"
                                class="w-5 h-5 text-blue-600 border-slate-300 rounded">
                            <div class="flex flex-col">
                                <span
                                    class="text-slate-800 font-semibold text-sm md:text-base group-hover:text-blue-600 transition-colors">Allgemeine
                                    Frage</span>
                                <span class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Zum
                                    Import-Ablauf</span>
                            </div>
                        </label>

                        <div class="rounded-2xl border border-slate-100 overflow-hidden" id="calcContainer">
                            <label
                                class="flex items-center gap-4 p-4 bg-white hover:bg-slate-50 transition-all cursor-pointer group">
                                <input type="checkbox" id="checkLimit"
                                    onchange="toggleCalculator(this.checked); validateForm()"
                                    class="w-5 h-5 text-blue-600 border-slate-300 rounded">
                                <div class="flex flex-col">
                                    <span
                                        class="text-slate-800 font-semibold text-sm md:text-base group-hover:text-blue-600 transition-colors">Kalkulieren</span>
                                    <span
                                        class="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Kostenaufstellung</span>
                                </div>
                            </label>
                            <div id="detailedCalc"
                                class="hidden bg-slate-50 border-t border-slate-100 p-4 md:p-6 space-y-4">
                                <div class="flex items-center justify-between">
                                    <span class="text-[10px] font-bold text-slate-500 uppercase">Gebot Netto</span>
                                    <div class="relative w-28 md:w-32">
                                        <input type="number" id="modalLimitInput" oninput="runModalCalc()" value="0"
                                            class="w-full pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm font-bold outline-none">
                                        <span
                                            class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-bold">€</span>
                                    </div>
                                </div>
                                <select id="optWarranty" onchange="runModalCalc()"
                                    class="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-sm outline-none">
                                    <option value="0">Keine Zusatzgarantie</option>
                                </select>
                                <div class="space-y-2 text-[11px] md:text-sm pt-4 border-t border-slate-200">
                                    <div class="flex justify-between"><span>Netto Gebot:</span><span id="resNetto"
                                            class="font-bold">0 €</span></div>
                                    <div class="flex justify-between"><span>Transport:</span><span id="resTransport">0
                                            €</span></div>
                                    <div class="flex justify-between"><span>Anmeldung AT:</span><span>800 €</span></div>
                                    <div class="flex justify-between text-slate-400 italic"><span>Gebühren:</span><span
                                            id="resProvision">0 €</span></div>
                                    <div id="resOptionsRow" class="flex justify-between text-blue-600 hidden">
                                        <span>Optionen:</span><span id="resOptions">0 €</span>
                                    </div>
                                    <div class="pt-4 border-t border-slate-300">
                                        <div class="flex justify-between items-baseline">
                                            <span class="text-[10px] font-black text-slate-400 uppercase">Gesamt
                                                Brutto</span>
                                            <span id="resTotalBrutto"
                                                class="text-xl md:text-3xl font-black text-blue-600">0 €</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="p-4 md:p-6 bg-blue-50/50 rounded-3xl border border-blue-100 space-y-4">
                        <label
                            class="text-[10px] font-bold text-blue-400 uppercase tracking-widest block">Kontaktdaten</label>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <input type="text" id="userName" placeholder="Name"
                                class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl outline-none text-sm">
                            <input type="email" id="userEmail" placeholder="E-Mail"
                                class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl outline-none text-sm">
                        </div>
                        <div id="messageContainer" class="message-hidden">
                            <textarea id="userMessage" rows="2" placeholder="Nachricht (optional)"
                                class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl outline-none text-sm resize-none"></textarea>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Modal Footer -->
            <div class="p-4 md:p-6 bg-white border-t border-slate-100 flex flex-col md:flex-row gap-3 flex-shrink-0">
                <button id="btnSubmitInquiry" disabled onclick="sendInquiry()"
                    class="flex-[2] bg-blue-600 disabled:bg-slate-200 text-white font-bold py-4 rounded-2xl shadow-xl flex items-center justify-center gap-2">
                    <i data-lucide="send" class="w-5 h-5"></i>
                    <span id="btnText">Anfrage senden</span>
                </button>
                <button onclick="closeModal()"
                    class="flex-1 bg-white text-slate-500 font-bold py-4 rounded-2xl border border-slate-200 text-sm">Abbrechen</button>
            </div>
        </div>
    </div>

    <!-- Data Modal -->
    <div id="dataModalBackdrop"
        class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm z-[110] hidden flex items-start justify-center p-4 transition-opacity duration-300 opacity-0 min-h-full">
        <div id="dataModalContainer"
            class="max-w-2xl w-full glass-modal rounded-3xl shadow-2xl overflow-hidden transform transition-all duration-300 scale-95 opacity-0 flex flex-col relative max-h-[90vh] mt-10 md:mt-20">
            <button onclick="closeDataModal()"
                class="absolute top-4 right-4 z-50 bg-white/80 p-2 rounded-full shadow-lg hover:bg-white transition-colors">
                <i data-lucide="x" class="w-5 h-5 text-slate-600"></i>
            </button>
            <div id="dataModalContent" class="overflow-y-auto w-full">
                <!-- Dynamic Content -->
            </div>
        </div>
    </div>

    <!-- Main Container -->
    <div id="mainContainer" class="max-w-7xl mx-auto">
        <header class="mb-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
                <h1 class="text-3xl md:text-4xl font-bold text-slate-800">Auktionsfahrzeuge</h1>
                <div class="flex flex-col sm:flex-row items-center gap-3">
                    <button id="syncGitHub" onclick="syncToGitHub()"
                        class="sync-btn w-full sm:w-auto px-6 py-3 rounded-xl font-bold text-sm shadow-lg flex items-center justify-center gap-2">
                        <i data-lucide="refresh-cw" class="w-4 h-4"></i> Live-Update
                    </button>
                    <div class="relative w-full sm:w-64">
                        <i data-lucide="search"
                            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"></i>
                        <input type="text" id="searchInput" placeholder="Suchen..."
                            class="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-xl outline-none bg-white shadow-sm">
                    </div>
                </div>
            </div>

            <div
                class="flex flex-col md:flex-row items-end gap-4 p-4 md:p-5 bg-white rounded-2xl border border-slate-200 shadow-sm">
                <div class="w-full md:w-32">
                    <label class="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">Marke</label>
                    <select id="makeFilter" class="filter-select w-full outline-none text-sm">
                        <option value="">Alle Marken</option>
                    </select>
                </div>
                <div class="w-full md:w-auto">
                    <label class="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">Baujahr</label>
                    <div class="flex items-center gap-2">
                        <select id="yearMin" class="filter-select w-full md:w-24 outline-none text-sm">
                            <option value="0">Jahr von</option>
                        </select>
                        <select id="yearMax" class="filter-select w-full md:w-24 outline-none text-sm">
                            <option value="9999">Jahr bis</option>
                        </select>
                    </div>
                </div>
                <div class="w-full md:w-auto">
                    <label class="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">Kilometer</label>
                    <div class="flex items-center gap-2">
                        <select id="kmMin" class="filter-select w-full md:w-28 outline-none text-sm">
                            <option value="0">KM von</option>
                            <option value="0">0 KM</option>
                            <option value="10000">10.000 KM</option>
                            <option value="20000">20.000 KM</option>
                            <option value="30000">30.000 KM</option>
                            <option value="40000">40.000 KM</option>
                            <option value="50000">50.000 KM</option>
                            <option value="60000">60.000 KM</option>
                            <option value="70000">70.000 KM</option>
                            <option value="80000">80.000 KM</option>
                            <option value="90000">90.000 KM</option>
                            <option value="100000">100.000 KM</option>
                            <option value="125000">125.000 KM</option>
                            <option value="150000">150.000 KM</option>
                            <option value="200000">200.000 KM</option>
                        </select>
                        <select id="kmMax" class="filter-select w-full md:w-28 outline-none text-sm">
                            <option value="9999999">KM bis</option>
                            <option value="10000">10.000 KM</option>
                            <option value="20000">20.000 KM</option>
                            <option value="30000">30.000 KM</option>
                            <option value="40000">40.000 KM</option>
                            <option value="50000">50.000 KM</option>
                            <option value="60000">60.000 KM</option>
                            <option value="70000">70.000 KM</option>
                            <option value="80000">80.000 KM</option>
                            <option value="90000">90.000 KM</option>
                            <option value="100000">100.000 KM</option>
                            <option value="125000">125.000 KM</option>
                            <option value="150000">150.000 KM</option>
                            <option value="200000">200.000 KM</option>
                            <option value="9999999">Beliebig</option>
                        </select>
                    </div>
                </div>
                <div class="w-full md:w-56 multi-select-container">
                    <label class="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">Ausstattung</label>
                    <div id="multiSelectBtn" onclick="toggleMultiSelect(event)"
                        class="filter-select w-full outline-none text-sm cursor-pointer flex justify-between items-center">
                        <span id="selectedCountText" class="truncate mr-2">Alle Merkmale</span>
                        <i data-lucide="chevron-down" class="w-4 h-4 text-slate-400"></i>
                    </div>
                    <div id="multiSelectDropdown" class="multi-select-dropdown">
                        <!-- JS populated -->
                    </div>
                </div>
                <div class="w-full md:w-40">
                    <label class="text-[10px] font-bold text-slate-400 uppercase ml-1 block mb-1">Sortierung</label>
                    <select id="sortOrder" class="filter-select w-full outline-none text-sm">
                        <option value="newest">Neueste zuerst</option>
                        <option value="oldest">Älteste zuerst</option>
                        <option value="price-asc">Preis aufst.</option>
                        <option value="price-desc">Preis abst.</option>
                        <option value="km-asc">KM aufst.</option>
                        <option value="id-asc">ID aufst.</option>
                        <option value="id-desc">ID abst.</option>
                    </select>
                </div>
                <button onclick="resetFilters()"
                    class="w-full md:w-auto px-4 py-2.5 text-xs text-blue-500 font-bold hover:bg-blue-50 rounded-lg transition-colors">Filter
                    Reset</button>
            </div>
        </header>

        <!-- Grid: Mobil 1 Spalte, Desktop 4 Spalten -->
        <div id="carGrid" class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6 mb-12"></div>
        <div id="pagination" class="flex justify-center items-center gap-2 pb-12"></div>
    </div>

    <script>
        const cars = {json.dumps(filtered_data, allow_nan=False)};

        const fmt = new Intl.NumberFormat('de-DE', {{ style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }});
        let currentPage = 1;
        const itemsPerPage = 50;
        let currentCarId = null;

        async function syncToGitHub() {{
            const btn = document.getElementById('syncGitHub');
            const old = btn.innerHTML;
            btn.disabled = true; btn.innerText = 'Syncing...';
            try {{
                const res = await fetch('/api/push-github');
                const data = await res.json();
                showToast(data.status === 'success' ? 'Update Live!' : 'Fehler', data.status);
            }} catch (e) {{ showToast('Server Fehler', 'error'); }}
            finally {{ btn.disabled = false; btn.innerHTML = old; lucide.createIcons(); }}
        }}

        function initFilters() {{
            const makes = [...new Set(cars.map(c => c.name.split(' ')[0]))].sort();
            const mFilter = document.getElementById('makeFilter');
            makes.forEach(m => {{ const opt = document.createElement('option'); opt.value = m; opt.innerText = m; mFilter.appendChild(opt); }});

            const years = [...new Set(cars.map(c => c.year_raw))].sort((a, b) => b - a);
            const yMin = document.getElementById('yearMin');
            const yMax = document.getElementById('yearMax');
            years.forEach(y => {{
                const opt1 = document.createElement('option'); opt1.value = y; opt1.innerText = y; yMin.appendChild(opt1);
                const opt2 = document.createElement('option'); opt2.value = y; opt2.innerText = y; yMax.appendChild(opt2);
            }});

            const features = [...new Set(cars.flatMap(c => c.ausstattung_full))].filter(Boolean).sort();
            const dropdown = document.getElementById('multiSelectDropdown');
            dropdown.innerHTML = features.map(f => `
                    <label class="multi-select-item text-xs font-medium text-slate-600">
                        <input type="checkbox" value="${{f}}" onchange="onFeatureChange()" class="feature-checkbox rounded border-slate-300 text-blue-600 focus:ring-blue-500">
                        <span class="truncate">${{f}}</span>
                    </label>
                `).join('');

            ['makeFilter', 'yearMin', 'yearMax', 'kmMin', 'kmMax', 'searchInput', 'sortOrder'].forEach(id => {{
                document.getElementById(id).addEventListener('change', () => {{ currentPage = 1; render(); }});
                document.getElementById(id).addEventListener('input', () => {{ currentPage = 1; render(); }});
            }});

            window.addEventListener('click', (e) => {{
                if (!e.target.closest('.multi-select-container')) {{
                    document.getElementById('multiSelectDropdown').classList.remove('active');
                }}
            }});
        }}

        function toggleMultiSelect(e) {{
            e.stopPropagation();
            document.getElementById('multiSelectDropdown').classList.toggle('active');
        }}

        function onFeatureChange() {{
            const checked = Array.from(document.querySelectorAll('.feature-checkbox:checked')).map(cb => cb.value);
            const btnText = document.getElementById('selectedCountText');
            if (checked.length === 0) btnText.innerText = "Alle Merkmale";
            else if (checked.length === 1) btnText.innerText = checked[0];
            else btnText.innerText = `${{checked.length}} Merkmale`;
            currentPage = 1;
            render();
        }}

        function showToast(msg, type) {{
            const toast = document.getElementById('toast');
            document.getElementById('toastMessage').innerText = msg;
            document.getElementById('toastIcon').innerHTML = type === 'success' ? '<i data-lucide="check-circle" class="w-5 h-5 text-emerald-500"></i>' : '<i data-lucide="alert-circle" class="w-5 h-5 text-red-500"></i>';
            lucide.createIcons();
            toast.style.display = 'block'; setTimeout(() => {{ toast.style.display = 'none'; }}, 3000);
        }}

        function openModal(name, id, img, event) {{
            currentCarId = id;
            const container = document.getElementById('modalContainer');
            
            // Pop-up ganz oben platzieren
            container.style.marginTop = '50px';
            
            // Wix anweisen, zum iFrame-Anfang zu scrollen (mit 50px Puffer)
            window.parent.postMessage({{ type: 'scroll_to_top', offset: 50 }}, '*');

            const car = cars.find(c => String(c.id) === String(id));
            document.getElementById('modalCarName').innerText = name;
            document.getElementById('modalCarId').innerText = id;
            document.getElementById('modalCarImg').src = img || 'https://via.placeholder.com/600x400';
            document.getElementById('modalLimitInput').value = car.bca_price;

            const wSelect = document.getElementById('optWarranty');
            wSelect.innerHTML = '<option value="0">Keine Zusatzgarantie</option>';
            if (car.warranty_options) {{
                Object.entries(car.warranty_options).forEach(([level, price]) => {{
                    const opt = document.createElement('option'); opt.value = price; opt.innerText = `12M ${{level}} - ${{price}}€`;
                    wSelect.appendChild(opt);
                }});
            }}

            const backdrop = document.getElementById('modalBackdrop');
            backdrop.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            updateModalState(true);
            setTimeout(() => {{ backdrop.classList.add('opacity-100'); document.getElementById('modalContainer').classList.add('scale-100', 'opacity-100'); }}, 10);

            document.getElementById('checkEmail').checked = false;
            document.getElementById('checkLimit').checked = false;
            document.getElementById('checkImport').checked = false;
            document.getElementById('successOverlay').classList.remove('active');
            toggleCalculator(false); toggleMessageField(false); validateForm();
        }}

        function closeModal() {{
            const backdrop = document.getElementById('modalBackdrop');
            backdrop.classList.remove('opacity-100');
            document.getElementById('modalContainer').classList.remove('scale-100', 'opacity-100');
            document.body.style.overflow = '';
            updateModalState(false);
            setTimeout(() => {{ 
                backdrop.classList.add('hidden'); 
                document.getElementById('modalContainer').style.marginTop = '';
            }}, 300);
        }}

        function toggleCalculator(s) {{ document.getElementById('detailedCalc').classList.toggle('hidden', !s); if (s) runModalCalc(); }}
        function toggleMessageField(s) {{ document.getElementById('messageContainer').classList.toggle('message-hidden', !s); if (s) document.getElementById('messageContainer').classList.add('message-visible'); }}

        function openDataModal(id, event) {{
            const container = document.getElementById('dataModalContainer');

            // Pop-up ganz oben platzieren
            container.style.marginTop = '50px';
            
            // Wix anweisen, zum iFrame-Anfang zu scrollen (mit 50px Puffer)
            window.parent.postMessage({{ type: 'scroll_to_top', offset: 50 }}, '*');

            const car = cars.find(c => String(c.id) === String(id));
            if (!car) return;
            const content = document.getElementById('dataModalContent');
            content.innerHTML = `
                    <div class="flex flex-col w-full">
                        <!-- Hero Section -->
                        <div class="relative h-64 md:h-80 w-full bg-slate-900 flex-shrink-0">
                            <img src="${{car.img}}" class="w-full h-full object-cover opacity-90" alt="${{car.name}}">
                            <div class="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent"></div>
                            <div class="absolute bottom-0 left-0 p-6 md:p-8 w-full">
                                <h2 class="text-3xl md:text-4xl font-extrabold text-white mb-3 tracking-tight drop-shadow-md">${{car.name}}</h2>
                                ${{car.ausfuehrung && car.ausfuehrung.trim() !== '' && car.ausfuehrung !== '-' && car.ausfuehrung !== 'nan' ? `<div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-600/90 text-white text-xs md:text-sm font-semibold backdrop-blur-md border border-blue-400/30 shadow-sm"><i data-lucide="tag" class="w-3 h-3 md:w-4 md:h-4"></i> ${{car.ausfuehrung}}</div>` : ''}}
                            </div>
                        </div>
                        
                        <!-- Details Section -->
                        <div class="p-6 md:p-8 flex flex-col gap-8 bg-white">
                            
                            <!-- Key Data Grid -->
                            <div>
                                <h3 class="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                                    <i data-lucide="activity" class="w-5 h-5 text-blue-600"></i> Fahrzeugdaten
                                </h3>
                                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div class="flex flex-col p-4 bg-slate-50 rounded-2xl border border-slate-100 hover:border-blue-200 hover:shadow-md transition-all">
                                        <div class="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm mb-3 text-blue-600">
                                            <i data-lucide="calendar" class="w-5 h-5"></i>
                                        </div>
                                        <span class="text-[11px] font-bold text-slate-400 uppercase mb-1">Erstzulassung</span>
                                        <span class="font-bold text-slate-800 text-base md:text-lg">${{car.ez}}</span>
                                    </div>
                                    <div class="flex flex-col p-4 bg-slate-50 rounded-2xl border border-slate-100 hover:border-blue-200 hover:shadow-md transition-all">
                                        <div class="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm mb-3 text-blue-600">
                                            <i data-lucide="gauge" class="w-5 h-5"></i>
                                        </div>
                                        <span class="text-[11px] font-bold text-slate-400 uppercase mb-1">Laufleistung</span>
                                        <span class="font-bold text-slate-800 text-base md:text-lg">${{car.km}} KM</span>
                                    </div>
                                    <div class="flex flex-col p-4 bg-slate-50 rounded-2xl border border-slate-100 hover:border-blue-200 hover:shadow-md transition-all">
                                        <div class="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm mb-3 text-blue-600">
                                            <i data-lucide="zap" class="w-5 h-5"></i>
                                        </div>
                                        <span class="text-[11px] font-bold text-slate-400 uppercase mb-1">Leistung</span>
                                        <span class="font-bold text-slate-800 text-base md:text-lg">${{car.ps}} PS</span>
                                    </div>
                                    <div class="flex flex-col p-4 bg-slate-50 rounded-2xl border border-slate-100 hover:border-blue-200 hover:shadow-md transition-all">
                                        <div class="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm mb-3 text-blue-600">
                                            <i data-lucide="fuel" class="w-5 h-5"></i>
                                        </div>
                                        <span class="text-[11px] font-bold text-slate-400 uppercase mb-1">Kraftstoff</span>
                                        <span class="font-bold text-slate-800 text-base md:text-lg whitespace-nowrap overflow-hidden text-ellipsis w-full block">${{car.kraftstoff}}</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Highlights -->
                            <div>
                                <h3 class="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                                    <i data-lucide="list-checks" class="w-5 h-5 text-blue-600"></i> Ausstattungshighlights
                                </h3>
                                <div class="flex flex-wrap gap-2">
                                    ${{(car.ausstattung_full || []).map(a => `<span class="px-3 py-1.5 bg-slate-100 border border-slate-200 rounded-xl text-xs md:text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors">${{a}}</span>`).join('')}}
                                </div>
                            </div>
                            
                        </div>
                        
                        <!-- Footer -->
                        <div class="p-4 md:p-6 bg-slate-50 border-t border-slate-100 flex justify-end">
                            <button onclick="closeDataModal()" class="px-8 py-3 bg-white text-slate-700 font-bold rounded-xl text-sm border border-slate-200 shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2">
                                <i data-lucide="x" class="w-4 h-4"></i> Schließen
                            </button>
                        </div>
                    </div>
                `;
            const bg = document.getElementById('dataModalBackdrop');
            const c = document.getElementById('dataModalContainer');
            bg.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            updateModalState(true);
            setTimeout(() => {{ bg.classList.add('opacity-100'); c.classList.add('scale-100', 'opacity-100'); }}, 10);
            lucide.createIcons();
        }}

        function closeDataModal() {{
            const bg = document.getElementById('dataModalBackdrop');
            const c = document.getElementById('dataModalContainer');
            bg.classList.remove('opacity-100');
            c.classList.remove('scale-100', 'opacity-100');
            document.body.style.overflow = '';
            updateModalState(false);
            setTimeout(() => {{
                bg.classList.add('hidden');
                c.style.marginTop = '';
            }}, 300);
        }}

        function validateForm() {{
            const any = ['checkEmail', 'checkLimit', 'checkImport'].some(id => document.getElementById(id).checked);
            const name = document.getElementById('userName').value.trim().length > 1;
            const mail = document.getElementById('userEmail').value.trim().includes('@');
            document.getElementById('btnSubmitInquiry').disabled = !any || !name || !mail;
        }}

        document.getElementById('userName').addEventListener('input', validateForm);
        document.getElementById('userEmail').addEventListener('input', validateForm);

        function runModalCalc() {{
            if (!currentCarId) return;
            const car = cars.find(c => c.id === currentCarId);
            const rawNetto = document.getElementById('modalLimitInput').value.replace(/\./g, '');
            const netto = parseFloat(rawNetto) || 0;
            const fees = (netto * 1.19 * 0.035) + 140;
            const transport = car.transport * 1.5;
            const commission = Math.max(500, netto * 0.02);
            const warranty = parseFloat(document.getElementById('optWarranty').value);
            const totalNetto = netto + fees + transport + 800 + commission + warranty;

            document.getElementById('resNetto').innerText = fmt.format(netto);
            document.getElementById('resTransport').innerText = fmt.format(transport);
            document.getElementById('resProvision').innerText = fmt.format(fees + commission);
            document.getElementById('resTotalBrutto').innerText = fmt.format(totalNetto * 1.20);

            const optRow = document.getElementById('resOptionsRow');
            if (warranty > 0) {{ optRow.classList.remove('hidden'); document.getElementById('resOptions').innerText = fmt.format(warranty); }}
            else {{ optRow.classList.add('hidden'); }}
        }}

        function sendInquiry() {{
            const car = cars.find(c => c.id === currentCarId);
            
            // Grunddaten vorbereiten
            const data = {{
                type: 'vehicle_inquiry',
                carId: currentCarId,
                carName: car.name,
                userData: {{
                    name: document.getElementById('userName').value,
                    email: document.getElementById('userEmail').value
                }}
            }};

            // Nur wenn "Zustandsbericht" angewählt ist, senden wir ein "Ja"
            if (document.getElementById('checkEmail').checked) {{
                data.zustandsbericht = 'Ja';
            }}

            // NEU: Nur wenn "Allgemeine Anfrage" angewählt ist, senden wir die Nachricht mit
            if (document.getElementById('checkImport').checked) {{
                data.nachricht = document.getElementById('userMessage').value;
            }}

            // Nur wenn "Kalkulation" angewählt ist, senden wir die Preisdaten mit
            if (document.getElementById('checkLimit').checked) {{
                const rawNetto = document.getElementById('modalLimitInput').value.replace(/\./g, '');
                const netto = parseFloat(rawNetto) || 0;
                const fees = (netto * 1.19 * 0.035) + 140;
                const transport = car.transport * 1.5;
                const commission = Math.max(500, netto * 0.02);
                const warranty = parseFloat(document.getElementById('optWarranty').value);
                const totalNetto = netto + fees + transport + 800 + commission + warranty;

                data.calculation = {{
                    gebotNetto: netto,
                    transport: transport,
                    anmeldung: 800,
                    provision: fees + commission,
                    garantie: warranty,
                    gesamtBrutto: totalNetto * 1.20
                }};
            }}
            
            window.parent.postMessage(JSON.stringify(data), "*");
            
            document.getElementById('btnSubmitInquiry').disabled = true;
            setTimeout(() => {{ document.getElementById('successOverlay').classList.add('active'); lucide.createIcons(); }}, 800);
        }}

        function formatNumberInput(el, id) {{
            let val = el.value.replace(/\./g, '').replace(/[^\d]/g, '');
            if (val === '') {{
                updateCalc(id, 0);
                return;
            }}
            const num = parseInt(val);
            el.value = num.toLocaleString('de-DE');
            updateCalc(id, num);
        }}

        function updateCalc(id, val) {{
            const car = cars.find(c => String(c.id) === String(id));
            if (!car) return;
            const netto = parseFloat(val) || 0;
            car.bca_price = netto; // Synchronize with internal data
            const fees = (netto * 1.19) * 0.035 + 140;
            const comm = Math.max(500, netto * 0.02);
            const transport = car.transport * 1.5;
            const totalBrutto = (netto + fees + transport + 800 + comm) * 1.20;
            const el = document.getElementById(`mainPrice_${{id}}`);
            if (el) el.innerText = fmt.format(totalBrutto);
        }}

        function render() {{
            const grid = document.getElementById('carGrid');
            const term = document.getElementById('searchInput').value.toLowerCase();
            const make = document.getElementById('makeFilter').value;
            const yMin = parseInt(document.getElementById('yearMin').value) || 0;
            const yMax = parseInt(document.getElementById('yearMax').value) || 9999;
            const kMin = parseInt(document.getElementById('kmMin').value) || 0;
            const kMax = parseInt(document.getElementById('kmMax').value) || 9999999;
            const selectedFeatures = Array.from(document.querySelectorAll('.feature-checkbox:checked')).map(cb => cb.value.toLowerCase());

            const filtered = cars.filter(c => {{
                const matchesTerm = (c.name.toLowerCase().includes(term) || String(c.id).includes(term));
                const matchesMake = (!make || c.name.startsWith(make));
                const matchesYear = (c.year_raw >= yMin && c.year_raw <= yMax);
                const matchesKm = (c.km_raw >= kMin && c.km_raw <= kMax);
                const matchesFeature = selectedFeatures.length === 0 || selectedFeatures.every(sf => (c.ausstattung_full || []).some(af => af.toLowerCase().includes(sf)));
                return matchesTerm && matchesMake && matchesYear && matchesKm && matchesFeature;
            }});

            const sort = document.getElementById('sortOrder').value;
            filtered.sort((a, b) => {{
                if (sort === 'newest') return new Date(b.archive_date) - new Date(a.archive_date);
                if (sort === 'oldest') return new Date(a.archive_date) - new Date(b.archive_date);
                if (sort === 'price-asc') return a.bca_price - b.bca_price;
                if (sort === 'price-desc') return b.bca_price - a.bca_price;
                if (sort === 'km-asc') return a.km_raw - b.km_raw;
                if (sort === 'id-asc') return parseInt(a.id) - parseInt(b.id);
                if (sort === 'id-desc') return parseInt(b.id) - parseInt(a.id);
                return 0;
            }});

            const items = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

            grid.innerHTML = items.map(car => `
                    <div class="glass-card rounded-2xl md:rounded-3xl overflow-hidden flex flex-col shadow-sm hover:shadow-lg transition-all duration-300">
                        <div class="relative h-32 md:h-44 bg-slate-100">
                            <img src="${{car.img}}" class="w-full h-full object-cover" alt="${{car.name}}">
                            <div class="absolute top-2 left-2 bg-white/90 px-2 py-0.5 rounded-full text-[8px] md:text-[10px] font-bold text-slate-600">ID: ${{car.id}}</div>
                            <div class="absolute top-2 right-2 bg-amber-100 text-amber-600 border border-amber-200 px-2 py-0.5 rounded-full text-[8px] md:text-[10px] font-bold shadow-sm uppercase tracking-wider flex items-center gap-1"><i data-lucide="gavel" class="w-2 h-2 md:w-3 h-3"></i> AUKTION</div>
                            ${{car.expiry_date ? `<div class="absolute bottom-2 left-2 bg-slate-900/80 text-white px-2 py-0.5 rounded-md text-[9px] md:text-[11px] font-bold shadow-sm flex items-center gap-1 timer-badge" data-expiry="${{car.expiry_date}}"><i data-lucide="clock" class="w-2 h-2 md:w-3 h-3"></i> <span class="timer-text">Lade...</span></div>` : ''}}
                        </div>
                        <div class="p-3 md:p-5 flex flex-col flex-grow card-padding">
                            <div class="mb-2">
                                <h3 class="text-sm md:text-lg font-bold text-slate-800 leading-tight card-title">
                                    ${{car.name}}
                                    ${{car.raw_data?.Ausstattungsvariante && car.raw_data.Ausstattungsvariante !== 'nan' && car.raw_data.Ausstattungsvariante !== '-' ? `<span class="text-slate-800 font-bold ml-1">${{car.raw_data.Ausstattungsvariante}}</span>` : ''}}
                                </h3>
                                <p class="text-[9px] md:text-xs text-slate-500 line-clamp-1">${{car.ausfuehrung}}</p>
                            </div>
                            <div class="flex gap-2 md:gap-4 text-[10px] md:text-xs font-bold text-slate-500 uppercase mb-3 card-specs">
                                <span>${{car.ez.split('.')[2]}}</span> &bull; <span>${{car.km}} KM</span> &bull; <span>${{car.ps}} PS</span>
                            </div>
                            <div class="flex flex-wrap gap-1 mb-4">
                                ${{car.ausstattung.slice(0, 3).map(a => `<span class="ausstattung-badge px-1.5 py-0.5 rounded text-[8px] md:text-[9px]">${{a}}</span>`).join('')}}
                            </div>
                            <div class="mt-auto space-y-3">
                                <div class="flex items-end justify-between gap-2 pt-2 border-t border-slate-100">
                                    <div class="flex-1">
                                        <span class="text-[8px] md:text-[10px] font-bold text-slate-400 uppercase mb-1 block">Gebot Netto</span>
                                        <div class="relative">
                                            <input type="text" value="${{Math.round(car.bca_price).toLocaleString('de-DE')}}" oninput="formatNumberInput(this, '${{car.id}}')" class="w-full pl-2 pr-5 py-1 rounded-lg text-xs md:text-sm font-bold bg-slate-50 border border-slate-200 outline-none focus:border-blue-400 transition-colors">
                                            <span class="absolute right-1.5 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400">€</span>
                                        </div>
                                    </div>
                                    <div class="flex-1 text-right">
                                        <span class="text-[8px] md:text-[10px] font-bold text-slate-400 uppercase block mb-1">Brutto</span>
                                        <div id="mainPrice_${{car.id}}" class="text-xs md:text-lg font-bold text-blue-600 truncate">${{fmt.format(car.details.total_brutto_at)}}</div>
                                    </div>
                                </div>
                                <div class="grid grid-cols-2 gap-2">
                                    <button onclick="openDataModal('${{car.id}}', event)" class="bg-slate-50 hover:bg-slate-100 text-slate-600 font-bold py-2 md:py-3 rounded-xl transition-all text-[10px] md:text-xs flex items-center justify-center gap-1 border border-slate-200">
                                        <i data-lucide="info" class="w-3 h-3 md:w-4 h-4"></i>Fahrzeugdaten
                                    </button>
                                    <button onclick="openModal('${{car.name.replace(/'/g, "\\'")}}', '${{car.id}}', '${{car.img}}', event)" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 md:py-3 rounded-xl transition-all text-[10px] md:text-xs flex items-center justify-center gap-1 shadow-sm">
                                        <i data-lucide="message-square" class="w-3 h-3 md:w-4 h-4"></i>Anfrage
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
            lucide.createIcons();
            updateTimers();
            renderPagination(Math.ceil(filtered.length / itemsPerPage));
            // NEU: Gib dem Browser 300ms Zeit zum Aufbauen, bevor er die Höhe an Wix meldet
            setTimeout(sendSettingsToParent, 300);
        }}

        function updateTimers() {{
            const now = new Date().getTime();
            document.querySelectorAll('.timer-badge').forEach(badge => {{
                const expiry = new Date(badge.dataset.expiry).getTime();
                const diff = expiry - now;
                const textEl = badge.querySelector('.timer-text');

                if (diff <= 0) {{
                    badge.classList.remove('bg-slate-900/80');
                    badge.classList.add('bg-red-600');
                    textEl.innerText = "Beendet";
                    return;
                }}

                const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                const secs = Math.floor((diff % (1000 * 60)) / 1000);

                if (days > 0) {{
                    textEl.innerText = `${{days}}d ${{hours}}h`;
                }} else if (hours > 0) {{
                    textEl.innerText = `${{hours}}h ${{mins}}m`;
                    if (hours < 1) badge.classList.replace('bg-slate-900/80', 'bg-orange-600');
                }} else {{
                    textEl.innerText = `${{mins}}m ${{secs}}s`;
                    badge.classList.remove('bg-slate-900/80');
                    badge.classList.add('bg-orange-600');
                }}
            }});
        }}

        setInterval(updateTimers, 1000);

        function resetFilters() {{
            document.querySelectorAll('.filter-select, #searchInput').forEach(e => e.value = '');
            document.querySelectorAll('.feature-checkbox').forEach(cb => cb.checked = false);
            document.getElementById('selectedCountText').innerText = "Alle Merkmale";
            currentPage = 1;
            render();
        }}

        function sendSettingsToParent() {{
            const wrapper = document.getElementById('wixContentWrapper');
            if (wrapper) {{
                // Wir messen nur den Wrapper, nicht den Body (um Loops zu vermeiden)
                const h = Math.max(wrapper.offsetHeight, 600);
                window.parent.postMessage({{ type: 'resize', height: h }}, '*');
            }}
        }}

        function updateModalState(isOpen) {{
            if (isOpen) {{
                document.body.classList.add('modal-open');
            }} else {{
                document.body.classList.remove('modal-open');
            }}
            sendSettingsToParent();
        }}

        window.addEventListener('load', () => setTimeout(sendSettingsToParent, 300));
        window.addEventListener('resize', () => setTimeout(sendSettingsToParent, 300));

        function renderPagination(t) {{
            const pag = document.getElementById('pagination');
            if (t <= 1) {{ pag.innerHTML = ''; return; }}
            let h = `<button onclick="changePage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}} class="px-3 py-1.5 bg-white border rounded-lg text-xs font-bold disabled:opacity-50">Zurück</button>`;
            h += `<span class="text-xs font-bold px-3">Seite ${{currentPage}}</span>`;
            h += `<button onclick="changePage(${{currentPage + 1}})" ${{currentPage === t ? 'disabled' : ''}} class="px-3 py-1.5 bg-white border rounded-lg text-xs font-bold disabled:opacity-50">Weiter</button>`;
            pag.innerHTML = h;
        }}

        function changePage(p) {{ 
            currentPage = p; 
            render(); 
            window.scrollTo({{ top: 0, behavior: 'smooth' }}); 
            window.parent.postMessage({{ type: 'scroll_to_top', offset: 0 }}, '*');
        }}

        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {{
            const syncBtn = document.getElementById('syncGitHub');
            if (syncBtn) syncBtn.style.display = 'none';
        }}

        try {{
            initFilters();
            render();
        }} catch (e) {{
            console.error("Render error:", e);
            document.getElementById('carGrid').innerHTML = '<div class="col-span-full p-8 text-center text-red-500 font-bold bg-red-50 rounded-2xl">Fehler beim Laden der Fahrzeuge. Bitte Seite neu laden.</div>';
        }}
        if (window.ResizeObserver && document.body) {{
            let resizeTimer;
            const target = document.getElementById('wixContentWrapper');
            if (target) {{
                new ResizeObserver(() => {{
                    clearTimeout(resizeTimer);
                    resizeTimer = setTimeout(sendSettingsToParent, 300);
                }}).observe(target);
            }}
        }} else {{
            window.addEventListener('load', () => {{
                if (window.ResizeObserver) {{
                    const target = document.getElementById('wixContentWrapper');
                    if (target) {{
                        new ResizeObserver(() => setTimeout(sendSettingsToParent, 300)).observe(target);
                    }}
                }}
            }});
        }}
        setTimeout(sendSettingsToParent, 500);
    </script>
    </div>
</body>

</html>
    """
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"Erfolg: {os.path.abspath(output_html_path)}")
    except Exception as e:
        print(f"Fehler: {str(e)}")
if __name__ == "__main__":
    process_bca()
