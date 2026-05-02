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
        df_temp = pd.read_excel(xls_path, header=None)
        header_idx = 0
        for i, row in df_temp.iterrows():
            if "Katalognummer" in row.values:
                header_idx = i
                break
        df = pd.read_excel(xls_path, header=header_idx)
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(html_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
        content = content.replace('\\<', '<').replace('\\>', '>').replace('\\"', '"').replace('\\/', '/')
        content = re.sub(r"\\'([0-9a-f]{2})", lambda m: chr(int(m.group(1), 16)), content)
        
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
                    "BCA_HTML_Price": 0.0
                })
                p_match = re.search(r'>\s*([\d.]+)\s*(?:€|\x80|â‚¬|EUR)', l)
                if p_match: extracted_html_data[-1]["BCA_HTML_Price"] = float(p_match.group(1).replace('.', ''))
                loc_match = re.search(r'flag--[A-Z]{2}[^>]*></i>.*?<span>(.*?),', l)
                if not loc_match: loc_match = re.search(r'<span>\s*([^<,]+?)\s*,\s*Katalognummer', l)
                if loc_match:
                    loc_raw = loc_match.group(1).split('(')[-1].split(';')[0].replace('Austria)', '').replace('GERMANY -', '').strip()
                    extracted_html_data[-1]["BCA_Standort"] = loc_raw

        df_html = pd.DataFrame(extracted_html_data).drop_duplicates(subset=['Katalognummer'])
        df['Katalognummer_Num'] = pd.to_numeric(df['Katalognummer'], errors='coerce')
        final_df = pd.merge(df, df_html, left_on='Katalognummer_Num', right_on='Katalognummer', how='left')
        
        js_data = []
        for _, row in final_df.iterrows():
            html_price = row.get('BCA_HTML_Price', 0.0)
            if not pd.isna(html_price) and html_price > 0:
                p_netto = float(html_price)
            else:
                p_raw = str(row.get('Aktuelles Gebot') or row.get('Netto-Preis') or row.get('BCA Netto') or row.get('Ist-Preis') or row.get('Startpreis') or '0')
                p_netto = float(re.sub(r'[^\d.]', '', p_raw.replace('.', '').replace(',', '.')) or 0)
            km = row.get('KM Stand', 0)
            km_str = f"{int(km*1000) if km < 1000 else int(km):,}".replace(',', '.') if not pd.isna(km) else "-"
            ps = str(row.get('PS', '-')).split('.')[0]
            aus1 = str(row.get('Ausstattung', '')).replace('nan', '')
            aus2 = str(row.get('Ausstattung 2', '')).replace('nan', '')
            aus_full = [a.strip() for a in (aus1 + (", " + aus2 if aus2 else "")).split(',') if a.strip()]
            km_raw = 0
            try:
                if not pd.isna(km): km_raw = int(km*1000) if km < 1000 else int(km)
            except: pass
            year_raw = 0
            try:
                ez_str = str(row.get('Erstzulassung', ''))
                year_match = re.search(r'20\d{2}', ez_str)
                if year_match: year_raw = int(year_match.group(0))
            except: pass
            calc = calculate_final_price_data(p_netto, row.get('BCA_Standort', ''), row.get('Karosserietyp', ''))
            def clean_val(val, default=""):
                if pd.isna(val): return default
                return val
            js_data.append({
                "id": str(clean_val(row.get('Katalognummer_Num', ''), '')).split('.')[0],
                "name": f"{clean_val(row.get('Hersteller', ''))} {clean_val(row.get('Modell', ''))}".strip(),
                "ausfuehrung": str(clean_val(row.get('Ausführung', ''))).replace('nan', ''),
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
                "details": calc
            })

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
            body {{ font-family: 'Outfit', sans-serif; background-color: #f8fafc; position: relative; min-height: 100vh; }}
            .glass-card {{ background: white; border: 1px solid #e2e8f0; }}
            .calc-box {{ background: #f1f5f9; border: 1px dashed #cbd5e1; }}
            .ausstattung-badge {{ background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
            .filter-select {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 8px 12px; }}
            .glass-modal {{ background: white; backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.3); }}
            #toast {{ position: fixed; bottom: 2rem; right: 2rem; padding: 1rem 1.5rem; border-radius: 1rem; background: white; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; display: none; z-index: 9999; animation: slideUp 0.3s ease-out; }}
            @keyframes slideUp {{ from {{ transform: translateY(100%); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
            .sync-btn {{ background: #059669; color: white; transition: all 0.3s; cursor: pointer; }}
            .sync-btn:hover {{ background: #047857; transform: translateY(-1px); }}
        </style>
    </head>
    <body class="p-4 sm:p-8 bg-slate-50 text-slate-800">
        <div id="toast" onclick="this.style.display='none'">
            <div class="flex items-center gap-3">
                <div id="toastIcon"></div>
                <div id="toastMessage" class="text-sm font-bold"></div>
            </div>
        </div>

        <!-- Anfrage Modal -->
        <div id="modalBackdrop" class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] hidden flex items-start justify-center p-4 transition-opacity duration-300 opacity-0 min-h-full">
            <div id="modalContainer" class="max-w-xl w-full glass-modal rounded-3xl shadow-2xl overflow-hidden transform transition-all duration-300 scale-95 opacity-0 flex flex-col my-8">
                <div class="relative h-48 bg-slate-100 flex-shrink-0">
                    <img id="modalCarImg" src="" class="w-full h-full object-cover" alt="Auto">
                    <div class="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent"></div>
                    <button onclick="closeModal()" class="absolute top-4 right-4 p-2 bg-white/80 hover:bg-white rounded-full text-slate-600 shadow-sm transition-colors">
                        <i data-lucide="x" class="w-6 h-6"></i>
                    </button>
                </div>

                <div class="p-8 pt-2 overflow-y-auto">
                    <div class="flex items-center gap-3 mb-4">
                        <div class="p-2 bg-blue-50 rounded-lg text-blue-600">
                            <i data-lucide="info" class="w-5 h-5"></i>
                        </div>
                        <h3 class="text-xl font-bold text-slate-800">Fahrzeuganfrage</h3>
                    </div>
                    
                    <p class="text-lg text-slate-700 leading-relaxed mb-6">
                        Sie interessieren sich für den <span id="modalCarName" class="font-bold text-blue-600">...</span>, 
                        ID: <span id="modalCarId" class="font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">...</span>.
                    </p>

                    <div class="space-y-4">
                        <div class="space-y-3">
                            <label class="flex items-start gap-4 p-4 rounded-2xl hover:bg-slate-50 cursor-pointer transition-all border border-slate-100 hover:border-blue-200 group">
                                <div class="flex items-center h-6"><input type="checkbox" id="checkEmail" onchange="toggleExtraFields(this.checked); validateForm()" class="w-5 h-5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 cursor-pointer"></div>
                                <div class="flex flex-col">
                                    <span class="text-slate-800 font-semibold group-hover:text-blue-600 transition-colors">Technischer Zustandsbericht</span>
                                    <span class="text-sm text-slate-500">Bericht per E-Mail erhalten.</span>
                                </div>
                            </label>
                            <div id="extraFields" class="hidden opacity-0 translate-y-[-10px] transition-all duration-300 px-4 py-2 space-y-3">
                                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <input type="text" id="userName" placeholder="Ihr Name" class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500">
                                    <input type="email" id="userEmail" placeholder="Ihre E-Mail Adresse" class="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500">
                                </div>
                            </div>
                        </div>

                        <div class="flex items-start gap-4 p-4 rounded-2xl hover:bg-slate-50 transition-all border border-slate-100 hover:border-blue-200 group">
                            <div class="flex items-center h-6 pt-1"><input type="checkbox" id="checkLimit" onchange="toggleLimitInput(this.checked); validateForm()" class="w-5 h-5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 cursor-pointer"></div>
                            <div class="flex flex-col w-full">
                                <label for="checkLimit" class="text-slate-800 font-semibold cursor-pointer group-hover:text-blue-600 transition-colors">Gebotslimit prüfen</label>
                                <div class="flex items-center gap-2 mt-2">
                                    <span class="text-sm text-slate-500">Limit von</span>
                                    <div class="relative w-28">
                                        <input type="number" id="limitInput" disabled placeholder="0.00" class="w-full pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50">
                                        <span class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-bold">€</span>
                                    </div>
                                    <span class="text-sm text-slate-500">prüfen.</span>
                                </div>
                            </div>
                        </div>

                        <label class="flex items-start gap-4 p-4 rounded-2xl hover:bg-slate-50 cursor-pointer transition-all border border-slate-100 hover:border-blue-200 group">
                            <div class="flex items-center h-6"><input type="checkbox" id="checkImport" onchange="validateForm()" class="w-5 h-5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 cursor-pointer"></div>
                            <div class="flex flex-col">
                                <span class="text-slate-800 font-semibold group-hover:text-blue-600 transition-colors">Allgemeine Frage</span>
                                <span class="text-sm text-slate-500">Frage zum Import-Ablauf.</span>
                            </div>
                        </label>
                    </div>
                </div>

                <div class="p-6 bg-slate-50/50 flex flex-col sm:flex-row gap-3 flex-shrink-0">
                    <button id="btnSubmitInquiry" disabled onclick="sendInquiry()" class="flex-[2] bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white font-bold py-4 rounded-2xl shadow-xl transition-all flex items-center justify-center gap-2 group">
                        <i data-lucide="send" class="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform"></i>
                        <span id="btnText">Anfrage senden</span>
                    </button>
                    <button onclick="closeModal()" class="flex-1 bg-white hover:bg-slate-100 text-slate-600 font-bold py-4 rounded-2xl border border-slate-200 transition-colors">Abbrechen</button>
                </div>
            </div>
        </div>

        <div id="mainContainer" class="max-w-7xl mx-auto">
            <header class="mb-10">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6">
                    <div>
                        <h1 class="text-4xl font-bold text-slate-800 mb-2">Auktionsfahrzeuge</h1>
                    </div>
                    <div class="flex items-center gap-4">
                        <button id="syncGitHub" onclick="syncToGitHub()" class="sync-btn px-6 py-3 rounded-xl font-bold text-sm shadow-lg flex items-center gap-2">
                            <i data-lucide="refresh-cw" class="w-5 h-5"></i>
                            Live-Update
                        </button>
                        <input type="text" id="searchInput" placeholder="Suche..." class="px-4 py-3 border rounded-xl outline-none w-full sm:w-64">
                    </div>
                </div>
                
                <div class="flex flex-wrap items-end gap-6 p-5 bg-white rounded-2xl border border-slate-200 shadow-sm">
                    <div class="flex flex-col gap-1.5">
                        <label class="text-[10px] font-bold text-slate-400 uppercase ml-1">Marke</label>
                        <select id="makeFilter" class="filter-select min-w-[160px] outline-none">
                            <option value="">Alle Marken</option>
                        </select>
                    </div>
                    <div class="flex flex-col gap-1.5">
                        <label class="text-[10px] font-bold text-slate-400 uppercase ml-1">Baujahr</label>
                        <div class="flex items-center gap-2">
                            <input type="number" id="yearMin" placeholder="von" class="filter-select w-20 px-2 py-1.5 outline-none">
                            <input type="number" id="yearMax" placeholder="bis" class="filter-select w-20 px-2 py-1.5 outline-none">
                        </div>
                    </div>
                    <button onclick="resetFilters()" class="text-xs text-blue-500 font-bold mb-2.5 transition-colors">Reset</button>
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

            async function syncToGitHub() {{
                const btn = document.getElementById('syncGitHub');
                const oldContent = btn.innerHTML;
                btn.disabled = true;
                btn.innerHTML = 'Synchronisiere...';
                
                try {{
                    const response = await fetch('http://localhost:8085/api/push-github');
                    const data = await response.json();
                    
                    if (data.status === 'success') {{
                        showToast('Erfolgreich! Deine WIX-Seite wird in Kürze aktualisiert.', 'success');
                    }} else {{
                        showToast('Fehler: ' + data.message, 'error');
                    }}
                }} catch (e) {{
                    showToast('Verbindung zum lokalen Server fehlgeschlagen. Läuft server.py?', 'error');
                }} finally {{
                    btn.disabled = false;
                    btn.innerHTML = oldContent;
                    lucide.createIcons();
                }}
            }}

            function initFilters() {{
                lucide.createIcons();
                const makes = [...new Set(cars.map(c => c.name.split(' ')[0]))].sort();
                const mFilter = document.getElementById('makeFilter');
                makes.forEach(m => {{ const opt = document.createElement('option'); opt.value = m; opt.innerText = m; mFilter.appendChild(opt); }});
                ['makeFilter', 'yearMin', 'yearMax', 'searchInput'].forEach(id => {{ 
                    const el = document.getElementById(id);
                    if(el) el.addEventListener('input', () => {{ currentPage = 1; render(); }}); 
                }});
            }}

            function showToast(msg, type) {{
                const toast = document.getElementById('toast');
                document.getElementById('toastMessage').innerText = msg;
                document.getElementById('toastIcon').innerHTML = type === 'success' ? '<i data-lucide="check-circle" class="w-5 h-5 text-emerald-500"></i>' : '<i data-lucide="alert-circle" class="w-5 h-5 text-red-500"></i>';
                lucide.createIcons();
                toast.style.display = 'block';
                setTimeout(() => {{ toast.style.display = 'none'; }}, 4000);
            }}

            function openModal(name, id, img) {{
                document.getElementById('modalCarName').innerText = name;
                document.getElementById('modalCarId').innerText = id;
                document.getElementById('modalCarImg').src = img || 'https://via.placeholder.com/600x400';
                
                const backdrop = document.getElementById('modalBackdrop');
                backdrop.classList.remove('hidden');
                
                // WICHTIG: Als String senden, da WIX oft Probleme mit rohen Objekten hat
                window.parent.postMessage(JSON.stringify({{ type: 'scroll_to_top' }}), '*');

                setTimeout(() => {{ 
                    backdrop.classList.add('opacity-100'); 
                    document.getElementById('modalContainer').classList.add('scale-100', 'opacity-100'); 
                }}, 10);
                validateForm();
            }}
            
            function closeModal() {{
                const backdrop = document.getElementById('modalBackdrop');
                backdrop.classList.remove('opacity-100');
                document.getElementById('modalContainer').classList.remove('scale-100', 'opacity-100');
                setTimeout(() => {{ backdrop.classList.add('hidden'); toggleExtraFields(false); }}, 300);
            }}

            function toggleExtraFields(s) {{
                const e = document.getElementById('extraFields');
                if(s) {{ 
                    e.classList.remove('hidden'); 
                    setTimeout(() => e.classList.add('opacity-100', 'translate-y-0'), 10); 
                }}
                else {{ 
                    e.classList.remove('opacity-100', 'translate-y-0'); 
                    setTimeout(() => e.classList.add('hidden'), 300); 
                }}
            }}

            function toggleLimitInput(c) {{ document.getElementById('limitInput').disabled = !c; if(c) document.getElementById('limitInput').focus(); }}

            function validateForm() {{
                const any = ['checkEmail', 'checkLimit', 'checkImport'].some(id => document.getElementById(id).checked);
                document.getElementById('btnSubmitInquiry').disabled = !any;
            }}

            function sendInquiry() {{
                const data = {{
                    type: 'vehicle_inquiry',
                    carName: document.getElementById('modalCarName').innerText,
                    carId: document.getElementById('modalCarId').innerText,
                    options: {{
                        report: document.getElementById('checkEmail').checked,
                        limit: document.getElementById('checkLimit').checked,
                        import: document.getElementById('checkImport').checked
                    }},
                    userData: {{
                        name: document.getElementById('userName').value,
                        email: document.getElementById('userEmail').value,
                        limitAmount: document.getElementById('limitInput').value
                    }},
                    recipient: 'office@newera-mobility.at'
                }};

                // Als String senden
                window.parent.postMessage(JSON.stringify(data), "*");
                
                document.getElementById('btnSubmitInquiry').disabled = true;
                document.getElementById('btnText').innerText = "Anfrage wird gesendet...";
                
                showToast("Anfrage wurde übermittelt!", "success");
                setTimeout(closeModal, 1500);
                setTimeout(() => {{ 
                    document.getElementById('btnText').innerText = "Anfrage senden";
                    validateForm();
                }}, 2000);
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
                const filtered = cars.filter(c => {{
                    return (c.name.toLowerCase().includes(term) || c.id.includes(term)) && (!makeVal || c.name.startsWith(makeVal)) && (c.year_raw >= yMin && c.year_raw <= yMax);
                }});
                const pageItems = filtered.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);
                grid.innerHTML = pageItems.map(car => `
                    <div class="glass-card rounded-3xl overflow-hidden flex flex-col shadow-sm hover:shadow-xl transition-all duration-300">
                        <div class="relative h-48 bg-slate-100">
                            <img src="${{car.img || 'https://via.placeholder.com/400'}}" class="w-full h-full object-cover" alt="${{car.name}}">
                            <div class="absolute top-3 left-3 bg-white/90 backdrop-blur px-3 py-1 rounded-full text-[10px] font-bold text-slate-600 shadow-sm">ID: ${{car.id}}</div>
                            <div class="absolute top-3 right-3 bg-blue-600 px-3 py-1 rounded-full text-[10px] font-bold text-white shadow-sm">${{car.car_type}}</div>
                        </div>
                        <div class="p-5 flex flex-col flex-grow">
                            <div class="title-section mb-3"><h3 class="text-lg font-bold text-slate-800 leading-tight">${{car.name}}</h3><p class="text-xs text-slate-500">${{car.ausfuehrung}}</p></div>
                            <div class="specs-section flex gap-4 text-[10px] font-bold text-slate-400 uppercase mb-4"><span>${{car.ez}}</span> &bull; <span>${{car.km}} KM</span></div>
                            <div class="ausstattung-section flex flex-wrap gap-1.5 mb-6">${{car.ausstattung.map(a => `<span class="ausstattung-badge px-2 py-0.5 rounded text-[10px]">${{a}}</span>`).join('')}}</div>
                            <div class="mt-auto space-y-4">
                                <div class="flex items-end justify-between">
                                    <div class="flex flex-col"><span class="text-[10px] font-bold text-slate-400 uppercase">Gebot Netto</span><input type="number" value="${{car.bca_price}}" oninput="updateCalc('${{car.id}}', this.value)" class="w-24 px-2 py-1 rounded-lg text-sm font-bold bg-slate-50 border outline-none focus:border-blue-300"></div>
                                    <div class="text-right"><span class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Endpreis AT Brutto</span><div id="mainPrice_${{car.id}}" class="text-xl font-bold text-blue-600">${{fmt.format(car.details.total_brutto_at)}}</div></div>
                                </div>
                                <div class="calc-box p-3 rounded-2xl text-[11px] text-slate-600 space-y-1">
                                    <div class="flex justify-between"><span>BCA Gebühren:</span><span id="auctionPct_${{car.id}}">${{fmt.format(car.details.auction_percent + car.details.auction_fix)}}</span></div>
                                    <div class="flex justify-between font-bold pt-1 border-t"><span>Gesamt Netto:</span><span id="totalNetto_${{car.id}}">${{fmt.format(car.details.total_netto)}}</span></div>
                                </div>
                                <button onclick="openModal('${{car.name.replace(/'/g, "\\'")}}', '${{car.id}}', '${{car.img}}')" class="w-full bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-600 font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2 text-sm group"><i data-lucide="message-square" class="w-4 h-4 group-hover:scale-110 transition-transform"></i>Anfrage senden</button>
                            </div>
                        </div>
                    </div>
                `).join('');
                lucide.createIcons();
                renderPagination(Math.ceil(filtered.length / itemsPerPage));
                sendHeightToWix();
            }}

            function sendHeightToWix() {{
                const c = document.getElementById('mainContainer');
                if (c) {{ window.parent.postMessage({{ type: 'resize', height: Math.ceil(c.getBoundingClientRect().height) + 100 }}, '*'); }}
            }}
            
            function renderPagination(t) {{
                const pag = document.getElementById('pagination');
                if (t <= 1) {{ pag.innerHTML = ''; return; }}
                let h = `<button onclick="changePage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}} class="pagination-btn px-4 py-2 rounded-xl text-sm font-bold">Zurück</button>`;
                for (let i = 1; i <= t; i++) h += `<button onclick="changePage(${{i}})" class="pagination-btn w-10 h-10 rounded-xl text-sm font-bold ${{currentPage === i ? 'active' : ''}}">${{i}}</button>`;
                h += `<button onclick="changePage(${{currentPage + 1}})" ${{currentPage === t ? 'disabled' : ''}} class="pagination-btn px-4 py-2 rounded-xl text-sm font-bold">Weiter</button>`;
                pag.innerHTML = h;
            }}
            function changePage(p) {{ currentPage = p; render(); window.scrollTo(0,0); }}
            initFilters(); render();
            
            // Hide sync button on live site (GitHub/Wix) but keep it on local file:// or localhost
            const isLocal = window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
            if (!isLocal) {{
                const syncBtn = document.getElementById('syncGitHub');
                if (syncBtn) syncBtn.style.display = 'none';
            }}

            if (window.ResizeObserver) {{ new ResizeObserver(() => sendHeightToWix()).observe(document.getElementById('mainContainer')); }}
            setTimeout(sendHeightToWix, 1000);
        </script>
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
