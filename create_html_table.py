import pandas as pd
from bs4 import BeautifulSoup
import re
import math
import argparse
import sys
import os
import json

def parse_args():
    parser = argparse.ArgumentParser(description='BCA Daten Mergen')
    parser.add_argument('--xls', type=str, default='BCAGermanyCheetah_20260425..xls')
    parser.add_argument('--html', type=str, default='bca_komplett.html')
    parser.add_argument('--out', type=str, default='index.html')
    return parser.parse_args()

# Transportkosten inklusive LCV-Kategorie (Kastenwagen)
# Hinweis: LCV-Preise sind aktuell auf SUV-Niveau + 50€ geschätzt. Bitte bei Bedarf anpassen.
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
    
    # LCV Check (Kastenwagen)
    is_lcv = any(word in karosserie_low for word in ['kasten', 'lcv', 'transporter', 'van', 'pritsche', 'pick-up'])
    # SUV Check
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
    total_netto = netto_preis + auction_percent + auction_fix + transport_cost + import_fee
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

def process_bca():
    args = parse_args()
    xls_path = args.xls
    html_path = args.html
    output_html_path = args.out

    try:
        # 1. Excel laden
        df = pd.read_excel(xls_path)
        
        # 2. HTML laden und parsen
        with open(html_path, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()
            
        # RTF/HTML Cleaning
        content = content.replace('\\<', '<').replace('\\>', '>').replace('\\"', '"').replace('\\/', '/')
        content = re.sub(r"\\'([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), content)
        
        # Listings extrahieren
        listings = re.split(r'(?=<div class="listing")', content)
        extracted_html_data = []
        for l in listings:
            if '<div class="listing"' not in l: continue
            
            lot_match = re.search(r'Katalognummer\s*([0-9]+)', l)
            img_match = re.search(r'<img[^>]+src="([^"]+)"', l)
            
            if lot_match:
                img_url = img_match.group(1) if img_match else ""
                if img_url.startswith('//'): img_url = 'https:' + img_url
                if img_url and 'width=' not in img_url:
                    img_url += '&minwidth=600&width=600'
                
                extracted_html_data.append({
                    "Katalognummer": int(lot_match.group(1)),
                    "BCA_Bild_URL": img_url,
                    "BCA_Standort": "Unbekannt" # Default, wird unten verfeinert
                })
                
                # Standort extrahieren (nach Flagge)
                loc_match = re.search(r'flag--[A-Z]{2}[^>]*></i>.*?<span>(.*?),', l)
                if loc_match:
                    loc_raw = loc_match.group(1).split('(')[-1].split(';')[0].replace('Austria)', '').strip()
                    extracted_html_data[-1]["BCA_Standort"] = loc_raw

        df_html = pd.DataFrame(extracted_html_data).drop_duplicates(subset=['Katalognummer'])
        
        # Mergen
        df['Katalognummer_Num'] = pd.to_numeric(df['Katalognummer'], errors='coerce')
        final_df = pd.merge(df, df_html, left_on='Katalognummer_Num', right_on='Katalognummer', how='left')
        
        js_data = []
        for _, row in final_df.iterrows():
            # Preis parsen
            p_raw = str(row.get('Aktuelles Gebot', '0'))
            p_netto = float(re.sub(r'[^\d.]', '', p_raw.replace('.', '').replace(',', '.')) or 0)
            
            # KM parsen
            km = row.get('KM Stand', 0)
            km_str = f"{int(km*1000) if km < 1000 else int(km):,}".replace(',', '.') if not pd.isna(km) else "-"
            
            # PS/Leistung
            ps = str(row.get('PS', '-')).split('.')[0]
            
            # Ausstattung Mergen
            aus1 = str(row.get('Ausstattung', '')).replace('nan', '')
            aus2 = str(row.get('Ausstattung 2', '')).replace('nan', '')
            aus_full = [a.strip() for a in (aus1 + (", " + aus2 if aus2 else "")).split(',') if a.strip()]
            
            # Raw values for filtering
            km_raw = 0
            try:
                if not pd.isna(km):
                    km_raw = int(km*1000) if km < 1000 else int(km)
            except: pass
            
            year_raw = 0
            try:
                ez_str = str(row.get('Erstzulassung', ''))
                year_match = re.search(r'20\d{2}', ez_str)
                if year_match: year_raw = int(year_match.group(0))
            except: pass

            calc = calculate_final_price_data(p_netto, row.get('BCA_Standort', ''), row.get('Karosserietyp', ''))
            
            js_data.append({
                "id": str(row.get('Katalognummer_Num', '')).split('.')[0],
                "name": f"{row.get('Hersteller', '')} {row.get('Modell', '')}".strip(),
                "ausfuehrung": str(row.get('Ausführung', '')).replace('nan', ''),
                "img": row.get('BCA_Bild_URL', ''),
                "ez": str(row.get('Erstzulassung', '-')).replace('nan', '-'),
                "km": km_str,
                "km_raw": km_raw,
                "year_raw": year_raw,
                "ps": ps,
                "kraftstoff": str(row.get('Kraftstoff', '-'))[:20],
                "ausstattung": aus_full[:6],
                "ausstattung_full": aus_full,
                "location": row.get('BCA_Standort', 'Unbekannt'),
                "car_type": calc['car_type'],
                "bca_price": p_netto,
                "transport": calc['transport'],
                "details": calc
            })

        html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BCA Premium Portfolio</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Outfit', sans-serif; background-color: #f8fafc; }}
            .glass-card {{ background: white; border: 1px solid #e2e8f0; }}
            .price-input {{ border: 1px solid #cbd5e1; }}
            .calc-box {{ background: #f1f5f9; border: 1px dashed #cbd5e1; }}
            .ausstattung-badge {{ background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
            .title-section {{ min-height: 52px; }}
            .specs-section {{ min-height: 28px; }}
            .ausstattung-section {{ min-height: 92px; align-content: start; }}
            .filter-select {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 8px 12px; font-size: 14px; outline: none; transition: border-color 0.2s; }}
            .filter-select:focus {{ border-color: #3b82f6; }}
            .pagination-btn {{ 
                transition: all 0.2s;
                background: white;
                border: 1px solid #e2e8f0;
            }}
            .pagination-btn:hover:not(:disabled) {{ background: #f1f5f9; border-color: #cbd5e1; }}
            .pagination-btn.active {{ background: #3b82f6; color: white; border-color: #3b82f6; }}
            .pagination-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
            
            .sync-btn {{ background: #059669; color: white; transition: all 0.3s; }}
            .sync-btn:hover {{ background: #047857; transform: translateY(-1px); }}
            .sync-btn:active {{ transform: translateY(0); }}
        </style>
    </head>
    <body class="p-8">
        <div class="max-w-7xl mx-auto">
            <header class="mb-10">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
                    <div>
                        <h1 class="text-4xl font-bold text-slate-800 mb-2">BCA Premium Portfolio</h1>
                        <p class="text-slate-500">Max. 50 Fahrzeuge pro Seite</p>
                    </div>
                    <div class="flex items-center gap-4">
                        <button id="syncGitHub" onclick="syncToGitHub()" class="sync-btn px-6 py-3 rounded-xl font-bold text-sm shadow-lg flex items-center gap-2">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                            Live-Update (GitHub)
                        </button>
                        <input type="text" id="searchInput" placeholder="Suche..." class="px-4 py-3 border rounded-xl outline-none w-full sm:w-64">
                    </div>
                </div>
                
                <div class="flex flex-wrap items-end gap-6 p-5 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <div class="flex flex-col gap-1.5">
                        <label class="text-[10px] font-bold text-slate-400 uppercase ml-1">Marke</label>
                        <select id="makeFilter" class="filter-select min-w-[160px]">
                            <option value="">Alle Marken</option>
                        </select>
                    </div>
                    
                    <div class="flex flex-col gap-1.5">
                        <label class="text-[10px] font-bold text-slate-400 uppercase ml-1">Baujahr</label>
                        <div class="flex items-center gap-2">
                            <input type="number" id="yearMin" placeholder="von" class="filter-select w-20 px-2 py-1.5">
                            <span class="text-slate-300">-</span>
                            <input type="number" id="yearMax" placeholder="bis" class="filter-select w-20 px-2 py-1.5">
                        </div>
                    </div>

                    <div class="flex flex-col gap-1.5">
                        <label class="text-[10px] font-bold text-slate-400 uppercase ml-1">Laufleistung (km)</label>
                        <div class="flex items-center gap-2">
                            <input type="number" id="kmMin" placeholder="von" class="filter-select w-24 px-2 py-1.5">
                            <span class="text-slate-300">-</span>
                            <input type="number" id="kmMax" placeholder="bis" class="filter-select w-24 px-2 py-1.5">
                        </div>
                    </div>
                    
                    <button onclick="resetFilters()" class="text-xs text-blue-500 font-bold hover:text-blue-600 mb-2.5">Reset</button>
                </div>
            </header>
            
            <div id="carGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-12"></div>
            
            <div id="pagination" class="flex justify-center items-center gap-2 pb-12"></div>
        </div>

        <script>
            const cars = {json.dumps(js_data)};
            const fmt = new Intl.NumberFormat('de-DE', {{ style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }});
            
            let currentPage = 1;
            const itemsPerPage = 50;

            function initFilters() {{
                const makes = [...new Set(cars.map(c => c.name.split(' ')[0]))].sort();
                const mFilter = document.getElementById('makeFilter');
                makes.forEach(m => {{
                    const opt = document.createElement('option');
                    opt.value = m; opt.innerText = m;
                    mFilter.appendChild(opt);
                }});
                
                ['makeFilter', 'yearMin', 'yearMax', 'kmMin', 'kmMax'].forEach(id => {{
                    document.getElementById(id).addEventListener('input', () => {{ currentPage = 1; render(); }});
                }});
            }}

            function resetFilters() {{
                document.getElementById('searchInput').value = '';
                document.getElementById('makeFilter').value = '';
                document.getElementById('yearMin').value = '';
                document.getElementById('yearMax').value = '';
                document.getElementById('kmMin').value = '';
                document.getElementById('kmMax').value = '';
                currentPage = 1;
                render();
            }}
            
            async function syncToGitHub() {{
                const btn = document.getElementById('syncGitHub');
                const oldContent = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = 'Synchronisiere...';
                
                try {{
                    const response = await fetch('http://localhost:8085/api/push-github');
                    const data = await response.json();
                    if (data.status === 'success') {{
                        alert('Erfolgreich! Deine WIX-Seite wird in Kürze aktualisiert.');
                    }} else {{
                        alert('Fehler: ' + data.message);
                    }}
                }} catch (e) {{
                    alert('Verbindung zum lokalen Server fehlgeschlagen. Läuft server.py?');
                }} finally {{
                    btn.disabled = false;
                    btn.innerHTML = oldContent;
                }}
            }}

            function updateCalc(id, val) {{
                const car = cars.find(c => c.id === id);
                if (!car) return;
                const netto = parseFloat(val) || 0;
                const auctionPct = (netto * 1.19) * 0.035;
                const totalNetto = netto + auctionPct + 140 + car.transport + 800;
                const totalBrutto = totalNetto * 1.20;
                
                const elPct = document.getElementById(`auctionPct_${{id}}`);
                const elNet = document.getElementById(`totalNetto_${{id}}`);
                const elMain = document.getElementById(`mainPrice_${{id}}`);
                if(elPct) elPct.innerText = fmt.format(auctionPct + 140);
                if(elNet) elNet.innerText = fmt.format(totalNetto);
                if(elMain) elMain.innerText = fmt.format(totalBrutto);
            }}

            function render() {{
                const grid = document.getElementById('carGrid');
                const term = document.getElementById('searchInput').value.toLowerCase();
                const makeVal = document.getElementById('makeFilter').value;
                const yMin = parseInt(document.getElementById('yearMin').value) || 0;
                const yMax = parseInt(document.getElementById('yearMax').value) || 9999;
                const kMin = parseInt(document.getElementById('kmMin').value) || 0;
                const kMax = parseInt(document.getElementById('kmMax').value) || 9999999;

                const filtered = cars.filter(c => {{
                    const matchSearch = c.name.toLowerCase().includes(term) || c.id.includes(term) || c.ausfuehrung.toLowerCase().includes(term);
                    const matchMake = !makeVal || c.name.startsWith(makeVal);
                    const matchYear = c.year_raw >= yMin && c.year_raw <= yMax;
                    const matchKm = c.km_raw >= kMin && c.km_raw <= kMax;
                    return matchSearch && matchMake && matchYear && matchKm;
                }});
                
                const totalPages = Math.ceil(filtered.length / itemsPerPage);
                const start = (currentPage - 1) * itemsPerPage;
                const pageItems = filtered.slice(start, start + itemsPerPage);

                grid.innerHTML = pageItems.map(car => `
                    <div class="glass-card rounded-3xl overflow-hidden flex flex-col shadow-sm hover:shadow-xl transition-all duration-300">
                        <div class="relative h-56 bg-slate-100">
                            <img src="${{car.img || 'https://via.placeholder.com/400'}}" class="w-full h-full object-cover" alt="${{car.name}}">
                            <div class="absolute top-4 left-4 bg-white/90 backdrop-blur px-3 py-1 rounded-full text-[10px] font-bold text-slate-600 shadow-sm">
                                ID: ${{car.id}}
                            </div>
                            <div class="absolute top-4 right-4 bg-blue-600 px-3 py-1 rounded-full text-[10px] font-bold text-white shadow-sm">
                                ${{car.car_type}}
                            </div>
                        </div>
                        
                        <div class="p-5 flex flex-col flex-grow">
                            <div class="title-section mb-3">
                                <h3 class="text-lg font-bold text-slate-800 leading-tight">${{car.name}}</h3>
                                <p class="text-sm text-slate-500">${{car.ausfuehrung}}</p>
                            </div>
                            
                            <div class="specs-section flex gap-4 text-xs font-bold text-slate-400 uppercase mb-4">
                                <span>${{car.ez}}</span>
                                <span>${{car.km}} KM</span>
                                <span>${{car.kraftstoff}}</span>
                            </div>

                            <div class="ausstattung-section flex flex-wrap gap-1.5 mb-6">
                                ${{car.ausstattung.map(a => `<span class="ausstattung-badge px-2 py-0.5 rounded text-[10px]">${{a}}</span>`).join('')}}
                            </div>

                            <div class="mt-auto">
                                <div class="flex items-center justify-between mb-4">
                                    <div class="flex flex-col">
                                        <span class="text-[10px] font-bold text-slate-400 uppercase">BCA Netto</span>
                                        <input type="number" 
                                               value="${{car.bca_price}}" 
                                               oninput="updateCalc('${{car.id}}', this.value)"
                                               class="price-input w-24 px-2 py-1 rounded-lg text-sm font-bold bg-slate-50">
                                    </div>
                                    <div class="text-right">
                                        <span class="text-[10px] font-bold text-slate-400 uppercase">Endpreis AT Brutto</span>
                                        <div id="mainPrice_${{car.id}}" class="text-xl font-bold text-blue-600">
                                            ${{fmt.format(car.details.total_brutto_at)}}
                                        </div>
                                    </div>
                                </div>

                                <div class="calc-box p-3 rounded-2xl text-[11px] text-slate-600 space-y-1">
                                    <div class="flex justify-between">
                                        <span>BCA Gebühren:</span>
                                        <span id="auctionPct_${{car.id}}">${{fmt.format(car.details.auction_percent + car.details.auction_fix)}}</span>
                                    </div>
                                    <div class="flex justify-between">
                                        <span>Transport:</span>
                                        <span>${{fmt.format(car.details.transport)}}</span>
                                    </div>
                                    <div class="flex justify-between font-bold pt-1 border-t border-slate-200">
                                        <span>Gesamt Netto:</span>
                                        <span id="totalNetto_${{car.id}}">${{fmt.format(car.details.total_netto)}}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
                
                renderPagination(totalPages);
            }}

            function renderPagination(totalPages) {{
                const pag = document.getElementById('pagination');
                if (totalPages <= 1) {{ pag.innerHTML = ''; return; }}
                
                let html = `
                    <button onclick="changePage(${{currentPage - 1}})" 
                            ${{currentPage === 1 ? 'disabled' : ''}} 
                            class="pagination-btn px-4 py-2 rounded-xl text-sm font-bold">Zurück</button>
                `;
                
                for (let i = 1; i <= totalPages; i++) {{
                    html += `
                        <button onclick="changePage(${{i}})" 
                                class="pagination-btn w-10 h-10 rounded-xl text-sm font-bold ${{currentPage === i ? 'active' : ''}}">
                            ${{i}}
                        </button>
                    `;
                }}
                
                html += `
                    <button onclick="changePage(${{currentPage + 1}})" 
                            ${{currentPage === totalPages ? 'disabled' : ''}} 
                            class="pagination-btn px-4 py-2 rounded-xl text-sm font-bold">Weiter</button>
                `;
                
                pag.innerHTML = html;
            }}

            function changePage(p) {{
                currentPage = p;
                render();
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }}

            document.getElementById('searchInput').addEventListener('input', () => {{ currentPage = 1; render(); }});
            initFilters();
            render();
        </script>
    </body>
    </html>
    """

        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
            
        print(f"Erfolg: {os.path.abspath(output_html_path)}")

    except Exception as e:
        print(f"Fehler: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_bca()
