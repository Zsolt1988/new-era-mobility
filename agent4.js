document.addEventListener('DOMContentLoaded', () => {
    const rawData = localStorage.getItem('lastExtractedCar');
    const finalPrice = localStorage.getItem('lastCalculatedFinalPrice');
    
    const mainUi = document.getElementById('main-ui');
    const noDataView = document.getElementById('no-data-view');
    
    // CSV Export Logic (Always initialized)
    const wixButtons = [document.getElementById('wix-btn'), document.getElementById('wix-btn-empty')];
    wixButtons.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', async () => {
                const origText = btn.innerHTML;
                btn.innerHTML = '⌛ Syncing...';
                try {
                    const response = await fetch('/api/sync-wix', {
                        method: 'POST'
                    });
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.message || 'Sync failed');
                    }
                    btn.innerHTML = '✅ Synced!';
                    setTimeout(() => { btn.innerHTML = origText; }, 3000);
                } catch (error) {
                    console.error('Wix Sync Error:', error);
                    btn.innerHTML = '❌ Error';
                    alert('Fehler bei der Wix-Synchronisation: ' + error.message);
                    setTimeout(() => { btn.innerHTML = origText; }, 5000);
                }
            });
        }
    });

    const csvButtons = [document.getElementById('csv-btn'), document.getElementById('csv-btn-empty')];
    console.log('CSV Buttons found:', csvButtons.filter(b => b !== null).map(b => b.id));
    
    csvButtons.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', async (e) => {
                console.log('CSV Button clicked:', btn.id);
                e.preventDefault();
                const origText = btn.innerHTML;
                btn.innerHTML = '⌛ Exporting...';
                
                try {
                    const response = await fetch('/api/export-csv', {
                        method: 'POST'
                    });
                    console.log('Export response status:', response.status);
                    
                    if (!response.ok) throw new Error('Export failed on server');
                    
                    // Fetch the generated CSV and force a download via Blob
                    const csvResponse = await fetch('/aktive_sammlung.csv?t=' + Date.now());
                    const csvText = await csvResponse.text();
                    const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
                    const url = URL.createObjectURL(blob);
                    
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'aktive_sammlung.csv';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    
                    btn.innerHTML = '✅ Ready!';
                    setTimeout(() => { btn.innerHTML = origText; }, 3000);
                } catch (error) {
                    console.error('CSV Export Error:', error);
                    btn.innerHTML = '❌ Error';
                    alert('Failed to export CSV: ' + error.message);
                    setTimeout(() => { btn.innerHTML = origText; }, 3000);
                }
            });
        }
    });

    if (!rawData || !finalPrice) {
        if(mainUi) mainUi.classList.add('hidden');
        if(noDataView) noDataView.classList.remove('hidden');
        return;
    }

    const data = JSON.parse(rawData);
    const car = data.cars && data.cars.length > 0 ? data.cars[0] : data;
    
    // Initial Population
    const initialTitle = car.title || `${car.carBrand} ${car.carModel}`;
    document.getElementById('edit-title').value = initialTitle;
    document.getElementById('edit-execution').value = car.carExecution || '';
    document.getElementById('edit-mileage').value = car.carMileage || '—';
    document.getElementById('edit-reg').value = car.carRegistration || '—';
    document.getElementById('edit-color').value = car.carColor || '—';
    document.getElementById('edit-power').value = car.carPower || '—';
    document.getElementById('edit-price').value = parseInt(finalPrice) || 0;

    // Feature Mapping Helpers
    function mapFeatures(carObj) {
        const lowerSpecs = JSON.stringify(carObj).toLowerCase();
        
        const interieur = [];
        if (lowerSpecs.includes("klima")) interieur.push("2-Zonen-Klimaautomatik");
        if (lowerSpecs.includes("sitzheizung")) interieur.push("El. beheizbare Sitze vorne");
        if (lowerSpecs.includes("verstellbare sitze")) interieur.push("El. verstellbare Sitze vorne");
        if (lowerSpecs.includes("lederlenkrad")) interieur.push("Lederlenkrad");
        if (lowerSpecs.includes("keyless")) interieur.push("Keyless Entry");
        if (lowerSpecs.includes("carplay") || lowerSpecs.includes("android auto")) interieur.push("Android Auto / CarPlay");
        if (lowerSpecs.includes("dachreling")) interieur.push("Dachreling");
        if (lowerSpecs.includes("heckklappe") && lowerSpecs.includes("elektrisch")) interieur.push("Elektrische Heckklappe");
        
        const defaultInterieur = ["Ambientebeleuchtung", "Digitales Cockpit", "Induktives Laden", "Multifunktionslenkrad"];
        while(interieur.length < 8 && defaultInterieur.length > 0) {
            const next = defaultInterieur.shift();
            if(!interieur.includes(next)) interieur.push(next);
        }

        const technologie = [];
        if (lowerSpecs.includes("navig") || lowerSpecs.includes("navi")) technologie.push("Navigationssystem");
        if (lowerSpecs.includes("head-up") || lowerSpecs.includes("hud")) technologie.push("Head-up display");
        if (lowerSpecs.includes("led") || lowerSpecs.includes("matrix")) technologie.push("Voll-LED Scheinwerfer");
        if (lowerSpecs.includes("kamera") || lowerSpecs.includes("360")) technologie.push("360° Kamera-System");
        if (lowerSpecs.includes("acc") || lowerSpecs.includes("abstand")) technologie.push("Abstandstempomat (ACC)");
        if (lowerSpecs.includes("totwinkel")) technologie.push("Totwinkelassistent");
        if (lowerSpecs.includes("verkehrszeichen")) technologie.push("Verkehrszeichenerkennung");
        if (lowerSpecs.includes("autonom") || lowerSpecs.includes("spurhalte")) technologie.push("Spurhalteassistent");
        
        if (carObj.specs && carObj.specs["Batteriekapazität"]) {
            technologie.push(`Batterie: ${carObj.specs["Batteriekapazität"]}`);
        }
        
        const defaultTech = ["Einparkhilfe vorne/hinten", "Notbremsassistent", "Müdigkeitswarner", "Berganfahrassistent"];
        while(technologie.length < 8 && defaultTech.length > 0) {
            const next = defaultTech.shift();
            if(!technologie.includes(next)) technologie.push(next);
        }

        return { interieur, technologie };
    }

    const initialFeatures = mapFeatures(car);
    document.getElementById('edit-interieur').value = initialFeatures.interieur.join('\n');
    document.getElementById('edit-technologie').value = initialFeatures.technologie.join('\n');
    
    // Map Schäden (Damages)
    let initialSchaeden = [];
    const damageSource = (car.schaeden && car.schaeden.length > 0) ? car.schaeden : (car.schäden || []);
    if (damageSource && damageSource.length > 0) {
        initialSchaeden = damageSource.map(s => {
            if (s.Bauteil) {
                return `${s.Bauteil} (${s.Position || ''}): ${s.Beschreibung}`.replace('(): ', ': ');
            }
            return s.Beschreibung;
        });
    }
    document.getElementById('edit-schaeden').value = initialSchaeden.join('\n');

    function getGeneratedHtml() {
        // Read from UI inputs instead of car object/localStorage
        const title = document.getElementById('edit-title').value;
        const execution = document.getElementById('edit-execution').value;
        const mileage = document.getElementById('edit-mileage').value;
        const registration = document.getElementById('edit-reg').value;
        const color = document.getElementById('edit-color').value;
        const kw = document.getElementById('edit-power').value;
        const price = parseInt(document.getElementById('edit-price').value);
        
        const ps = Math.round(parseInt(kw) * 1.36) || "—";
        const formattedPriceStr = new Intl.NumberFormat('de-DE').format(price) + '€';
        
        const interieurLines = document.getElementById('edit-interieur').value.split('\n').filter(l => l.trim() !== '');
        const technologieLines = document.getElementById('edit-technologie').value.split('\n').filter(l => l.trim() !== '');
        const schaedenLines = document.getElementById('edit-schaeden').value.split('\n').filter(l => l.trim() !== '');

        // Extract Brand/Model from title if possible for the footer
        const titleParts = title.split(' ');
        const brand = titleParts[0] || "Vehicle";
        const model = titleParts.slice(1).join(' ') || "Specification";

        return `<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} | New Era Mobility</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        sage: {
                            50: '#01fd77ff',
                            100: '#e6ede6',
                            200: '#ceddce',
                            300: '#a8c2a8',
                            400: '#7fa17f',
                            500: '#24d9edff',
                            600: '#0c7dffff', // Base Sage
                            700: '#3f563f',
                            800: '#344634',
                            900: '#ffffffff',
                        },
                        premium: '#1a1a1a',
                        accent: '#ceed21ff'
                    },
                    fontFamily: {
                        display: ['Outfit', 'sans-serif'],
                        body: ['Plus Jakarta Sans', 'sans-serif'],
                    },
                    keyframes: {
                        fadeIn: {
                            '0%': { opacity: '0' },
                            '100%': { opacity: '1' },
                        }
                    },
                    animation: {
                        'fade-in': 'fadeIn 0.8s ease-out',
                    }
                }
            }
        }
    </script>
    <style>
        body {
            background-color: #404040;
            color: #ffffffff;
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased;
        }
        .glass-card {
            background: #404040;
            backdrop-filter: blur(12px);
            border: 2px solid #ffffffff;
            border-radius: 24px;
        }
        .bento-item {
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .bento-item:hover {
            transform: translateY(-4px);
            background: rgba(255, 255, 255, 0.03);
            border-color: rgba(255, 255, 255, 0.8);
        }
        .text-gradient { 
            background: linear-gradient(135deg, #ffffff 0%, #0c7dffff 100%); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
        }
    </style>
</head>
<body class="p-4 md:p-8 lg:p-12">

    <div class="max-w-7xl mx-auto space-y-8 md:space-y-12 animate-fade-in">

        <!-- CONTENT GRID -->
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-6 md:gap-8 items-start">
            
            <!-- LEFT SIDE: STATS & FEATURES (Spans 3) -->
            <div class="lg:col-span-3 space-y-6 md:space-y-8">
                
                <!-- KEY STATS GRID -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Leistung</span>
                        <span class="text-lg md:text-xl font-display font-bold">${kw} kW</span>
                        <span class="text-white/60 text-[10px] md:text-xs">(${ps} PS)</span>
                    </div>
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Laufleistung</span>
                        <span class="text-lg md:text-xl font-display font-bold">${mileage}</span>
                    </div>
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Erstzulassung</span>
                        <span class="text-lg md:text-xl font-display font-bold">${registration}</span>
                    </div>
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Antrieb</span>
                        <span class="text-lg md:text-xl font-display font-bold">Automatik</span>
                    </div>
                </div>

                <!-- DETAILED FEATURES -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                    <div class="glass-card p-6 md:p-8 space-y-4 md:space-y-6 border-white/10">
                        <h3 class="text-lg md:text-xl font-display font-semibold text-sage-600 flex items-center gap-2">
                            <span class="w-6 md:w-8 h-[1px] bg-sage-600"></span> Interieur
                        </h3>
                        <ul class="space-y-2 md:space-y-3 text-xs md:text-sm text-white/80">
                            ${interieurLines.map(f => `<li class="flex items-start gap-2"><span>•</span> ${f}</li>`).join('')}
                        </ul>
                    </div>

                    <div class="glass-card p-6 md:p-8 space-y-4 md:space-y-6 border-white/10">
                        <h3 class="text-lg md:text-xl font-display font-semibold text-sage-600 flex items-center gap-2">
                            <span class="w-6 md:w-8 h-[1px] bg-sage-600"></span> Technologie
                        </h3>
                        <ul class="space-y-2 md:space-y-3 text-xs md:text-sm text-white/80">
                            ${technologieLines.map(f => `<li class="flex items-start gap-2"><span>•</span> ${f}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>

            <!-- RIGHT SIDE: ACTION AREA (Spans 2) -->
            <div class="lg:col-span-2 space-y-6">
                <div class="glass-card p-6 md:p-8 border-white/20 lg:sticky lg:top-8">
                    <h3 class="text-xl md:text-2xl font-display font-bold mb-6 text-white text-center md:text-left">Leistungspaket</h3>
                    <div class="space-y-4 mb-8">
                        <div class="flex items-center gap-3 text-white/90 text-sm md:text-base">
                            <div class="min-w-[20px] h-5 w-5 rounded-full bg-sage-400 flex items-center justify-center text-[10px] text-sage-100">✓</div>
                            <span>Import & Transport</span>
                        </div>
                        <div class="flex items-center gap-3 text-white/90 text-sm md:text-base">
                            <div class="min-w-[20px] h-5 w-5 rounded-full bg-sage-400 flex items-center justify-center text-[10px] text-sage-100">✓</div>
                            <span>NoVA & Umsatzsteuer</span>
                        </div>
                        <div class="flex items-center gap-3 text-white/90 text-sm md:text-base">
                            <div class="min-w-[20px] h-5 w-5 rounded-full bg-sage-400 flex items-center justify-center text-[10px] text-sage-100">✓</div>
                            <span>Vollständige Abwicklung</span>
                        </div>
                    </div>

                    <div class="p-4 md:p-5 bg-white/5 rounded-2xl border border-white/5 mb-8 text-center md:text-left">
                        <p class="text-[10px] text-sage-600 uppercase font-bold tracking-[0.1em] mb-2">Optional zubuchbar</p>
                        <ul class="space-y-1 text-xs md:text-sm text-white/70">
                            <li>12 - 36 Monate Basisgarantie</li>
                            <li>Haustür-Lieferung</li>
                        </ul>
                    </div>

                    <button onclick="window.open('https://google.com', '_blank')" class="w-full bg-sage-600 hover:bg-sage-500 text-white font-display font-bold py-4 md:py-5 rounded-2xl transition-all duration-300 shadow-xl shadow-sage-600/20 flex items-center justify-center gap-2 group text-sm md:text-base">
                        Jetzt anfragen
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>

        <!-- FOOTER / DISCLAIMER -->
        <footer class="pt-8 md:pt-12 pb-6 border-t border-white/10">
            <p class="text-[10px] leading-relaxed text-white/40 uppercase tracking-[0.15em] text-center max-w-3xl mx-auto">
                Hinweis: Alle Angaben basieren auf den vorliegenden Fahrzeugdaten und werden nach bestem Wissen erstellt. Irrtümer und Zwischenverkauf vorbehalten.
            </p>
        </footer>

    </div>
</body>
</html>`;
    }

    function saveGeneratedHtml() {
        try {
            const html = getGeneratedHtml();
            if (html && html.length > 100) {
                localStorage.setItem('generatedHtml', html);
                console.log('✅ HTML generated and saved to localStorage (Length: ' + html.length + ')');
            } else {
                console.warn('⚠️ Generated HTML seems too short, not saving.');
            }
        } catch (e) {
            console.error('❌ Failed to generate or save HTML:', e);
        }
    }

    const inputs = ['edit-title', 'edit-execution', 'edit-mileage', 'edit-reg', 'edit-color', 'edit-power', 'edit-price', 'edit-interieur', 'edit-technologie', 'edit-schaeden'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            // Check for previous overrides in this session
            const saved = localStorage.getItem(`override_${id}`);
            if (saved) el.value = saved;

            el.addEventListener('input', () => {
                localStorage.setItem(`override_${id}`, el.value);
                saveGeneratedHtml();
            });
        }
    });

    // Initial Save of HTML
    saveGeneratedHtml();

    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const html = getGeneratedHtml();
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        });
    }

    const downloadBtn = document.getElementById('download-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const titleInput = document.getElementById('edit-title');
            const title = titleInput ? titleInput.value : 'untitled';
            const html = getGeneratedHtml();
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `homepage_${title.toLowerCase().replace(/\s+/g, '_')}.html`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            const origText = downloadBtn.innerHTML;
            downloadBtn.innerHTML = '✅ Downloaded!';
            setTimeout(() => { downloadBtn.innerHTML = origText; }, 3000);
        });
    }

});
