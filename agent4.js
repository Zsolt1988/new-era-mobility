document.addEventListener('DOMContentLoaded', () => {
    const rawData = localStorage.getItem('lastExtractedCar');
    const finalPrice = localStorage.getItem('lastCalculatedFinalPrice');
    
    const mainUi = document.getElementById('main-ui');
    const noDataView = document.getElementById('no-data-view');
    
    if (!rawData || !finalPrice) {
        if(mainUi) mainUi.classList.add('hidden');
        if(noDataView) noDataView.classList.remove('hidden');
        return;
    }

    const data = JSON.parse(rawData);
    const car = data.cars && data.cars.length > 0 ? data.cars[0] : data;
    
    // Update labels
    document.getElementById('car-display-name').innerText = car.title || `${car.carBrand} ${car.carModel}`;
    document.getElementById('label-model').innerText = `${car.carBrand || 'BYD'} ${car.carModel || 'SEAL'}`;
    document.getElementById('label-mileage').innerText = car.carMileage || '—';
    document.getElementById('label-reg').innerText = car.carRegistration || '—';
    document.getElementById('label-color').innerText = car.carColor || '—';
    
    const formattedPrice = new Intl.NumberFormat('de-DE').format(parseInt(finalPrice)) + '€';
    document.getElementById('label-price').innerText = formattedPrice;

    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const brand = car.carBrand || "BYD";
            const model = car.carModel || "SEAL 6 Boost";
            const title = car.title || `${brand} ${model}`;
            const color = car.carColor || "sandstone (grau)";
            const price = parseInt(finalPrice);
            const formattedPriceStr = new Intl.NumberFormat('de-DE').format(price) + '€';
            
            const kw = car.carPower || "135 kW";
            const ps = Math.round(parseInt(kw) * 1.36) || "184";
            const mileage = car.carMileage || "10 km";
            const firstReg = car.carRegistration || "09/2025";
            
            const lowerSpecs = JSON.stringify(car).toLowerCase();

            // Map Interieur
            const interieur = [];
            if (lowerSpecs.includes("klima")) interieur.push("2-Zonen-Klimaautomatik");
            if (lowerSpecs.includes("sitzheizung") || lowerSpecs.includes("beheizbare sitze")) interieur.push("El. beheizbare Sitze vorne");
            if (lowerSpecs.includes("verstellbare sitze")) interieur.push("El. verstellbare Sitze vorne");
            if (lowerSpecs.includes("lederlenkrad")) interieur.push("Lederlenkrad");
            if (lowerSpecs.includes("keyless") || lowerSpecs.includes("schlüsselloses")) interieur.push("Keyless Entry");
            if (lowerSpecs.includes("carplay") || lowerSpecs.includes("android auto")) interieur.push("Android Auto / CarPlay");
            if (lowerSpecs.includes("dachreling")) interieur.push("Dachreling");
            if (lowerSpecs.includes("heckklappe") && lowerSpecs.includes("elektrisch")) interieur.push("Elektrische Heckklappe");
            
            const defaultInterieur = ["Ambientebeleuchtung", "Digitales Cockpit", "Induktives Laden", "Multifunktionslenkrad"];
            while(interieur.length < 8 && defaultInterieur.length > 0) {
                const next = defaultInterieur.shift();
                if(!interieur.includes(next)) interieur.push(next);
            }

            // Map Technologie
            const technologie = [];
            if (lowerSpecs.includes("navig") || lowerSpecs.includes("navi")) technologie.push("Navigationssystem");
            if (lowerSpecs.includes("head-up") || lowerSpecs.includes("hud")) technologie.push("Head-up display");
            if (lowerSpecs.includes("led") || lowerSpecs.includes("matrix")) technologie.push("Voll-LED Scheinwerfer");
            if (lowerSpecs.includes("kamera") || lowerSpecs.includes("360")) technologie.push("Rückfahrkamera");
            if (lowerSpecs.includes("acc") || lowerSpecs.includes("abstand")) technologie.push("Abstandstempomat");
            if (lowerSpecs.includes("totwinkel")) technologie.push("Totwinkelassistent");
            if (lowerSpecs.includes("verkehrszeichen")) technologie.push("Verkehrszeichenerkennung");
            if (lowerSpecs.includes("autonom") || lowerSpecs.includes("spurhalte")) technologie.push("Autonomes Fahren L2");
            
            const defaultTech = ["Einparkhilfe vorne/hinten", "Notbremsassistent", "Müdigkeitswarner", "Berganfahrassistent"];
            while(technologie.length < 8 && defaultTech.length > 0) {
                const next = defaultTech.shift();
                if(!technologie.includes(next)) technologie.push(next);
            }

            const html = `<!DOCTYPE html>
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
                            600: '#0c7dffff', 
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
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #3d3a3aff; color: #ffffffff; font-family: 'Plus Jakarta Sans', sans-serif; -webkit-font-smoothing: antialiased; }
        .glass-card { background: #3d3a3aff; backdrop-filter: blur(12px); border: 2px solid #ffffffff; border-radius: 24px; }
        .glass-card1 { background: #3d3a3aff; backdrop-filter: blur(12px); border: 0px none; border-radius: 24px; }
        .text-gradient { background: linear-gradient(135deg, #ffffff 0%, #2779d1ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; padding-bottom: 0.1em; margin-bottom: -0.1em; }
        .bento-item { transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
    </style>
</head>
<body class="p-4 md:p-8 lg:p-12">
    <div class="max-w-7xl mx-auto space-y-8">
        <header class="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b border-sage-800/30 pb-8">
            <div class="space-y-2 w-full md:w-auto">
                <p class="text-sage-900 font-display font-semibold tracking-widest uppercase text-xs md:text-sm">New Era Mobility</p>
                <h1 class="text-4xl md:text-6xl font-display font-bold text-gradient">${brand}</h1>
                <p class="text-xl text-sage-200 font-bold italic">${model}</p>
                <p class="text-sm md:text-base text-sage-200/70 font-light italic">${color}</p>
            </div>
            <div class="flex flex-col items-start md:items-end gap-4 w-full md:w-auto">
                <div class="flex flex-row flex-wrap justify-start md:justify-end gap-2">
                    <span class="bg-sage-900 text-sage-600 px-3 py-1 rounded-full text-[10px] md:text-sm font-medium border border-sage-600/0 whitespace-nowrap">FIXPREIS</span>
                    <span class="bg-sage-900 text-sage-600 px-3 py-1 rounded-full text-[10px] md:text-sm font-medium border border-sage-600/0 whitespace-nowrap">Gebrauchtwagen</span>
                    <span class="bg-sage-900 text-sage-600 px-3 py-1 rounded-full text-[10px] md:text-sm font-medium border border-sage-600/0">Verfügbar in ca. 5 Wochen</span>
                </div>
                <div class="text-3xl md:text-4xl font-display font-bold text-white">${formattedPriceStr}</div>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div class="lg:col-span-3 space-y-6 md:space-y-10">
                <div class="glass-card1 overflow-hidden group">
                    <div class="relative aspect-video flex items-center justify-center bg-black/20 rounded-3xl">
                        <span class="text-sage-600 font-display font-bold text-sm md:text-xl uppercase tracking-widest text-center px-4">Fahrzeugbild Platzhalter</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Leistung</span>
                        <span class="text-lg md:text-xl font-display font-bold">${kw}</span>
                        <span class="text-white/60 text-xs">(${ps} PS)</span>
                    </div>
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Laufleistung</span>
                        <span class="text-lg md:text-xl font-display font-bold">${mileage}</span>
                    </div>
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Erstzulassung</span>
                        <span class="text-lg md:text-xl font-display font-bold">${firstReg}</span>
                    </div>
                    <div class="glass-card p-4 md:p-6 bento-item flex flex-col justify-center items-center text-center">
                        <span class="text-sage-600 font-bold text-[10px] md:text-xs uppercase tracking-widest mb-1 md:mb-2">Antrieb</span>
                        <span class="text-lg md:text-xl font-display font-bold">Automatik</span>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
                    <div class="glass-card p-6 md:p-8 space-y-4 md:space-y-6">
                        <h3 class="text-lg md:text-xl font-display font-semibold text-sage-600 flex items-center gap-2">
                            <span class="w-6 md:w-8 h-[1px] bg-sage-600"></span> Interieur
                        </h3>
                        <ul class="grid grid-cols-1 gap-2 text-xs md:text-sm text-white/80">
                            ${interieur.map(f => `<li class="flex items-center gap-2"><span>•</span> ${f}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="glass-card p-6 md:p-8 space-y-4 md:space-y-6">
                        <h3 class="text-lg md:text-xl font-display font-semibold text-sage-600 flex items-center gap-2">
                            <span class="w-6 md:w-8 h-[1px] bg-sage-600"></span> Technologie
                        </h3>
                        <ul class="grid grid-cols-1 gap-2 text-xs md:text-sm text-white/80">
                            ${technologie.map(f => `<li class="flex items-center gap-2"><span>•</span> ${f}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-2 space-y-6">
                <div class="glass-card p-6 md:p-8">
                    <h3 class="text-xl md:text-2xl font-display font-bold mb-6 text-white text-center md:text-left">Leistungspaket</h3>
                    <div class="space-y-4 mb-8">
                        <div class="flex items-center gap-3 text-white/90 text-sm md:text-base">
                            <div class="min-w-[20px] h-5 rounded-full bg-sage-50/30 flex items-center justify-center text-[10px] text-sage-300">✓</div>
                            <span>Import & Transport</span>
                        </div>
                        <div class="flex items-center gap-3 text-white/90 text-sm md:text-base">
                            <div class="min-w-[20px] h-5 rounded-full bg-sage-50/30 flex items-center justify-center text-[10px] text-sage-300">✓</div>
                            <span>NoVA & Umsatzsteuer</span>
                        </div>
                        <div class="flex items-center gap-3 text-white/90 text-sm md:text-base">
                            <div class="min-w-[20px] h-5 rounded-full bg-sage-50/30 flex items-center justify-center text-[10px] text-sage-300">✓</div>
                            <span>Vollständige Abwicklung</span>
                        </div>
                    </div>
                    <div class="p-4 bg-white/5 rounded-xl border border-white/5 mb-8 text-center md:text-left">
                        <p class="text-[10px] text-sage-600 uppercase tracking-[0.1em] mb-2 font-bold">Optional zubuchbar</p>
                        <p class="text-xs md:text-sm text-sage-100">12 - 36 Monate Basisgarantie</p>
                        <p class="text-xs md:text-sm text-sage-100">Lieferung bis vor die Haustür</p>
                    </div>
                    <button onclick="window.open('https://google.com', '_blank')" class="w-full bg-sage-600 hover:bg-sage-500 text-white font-display font-bold py-4 md:py-5 rounded-2xl transition-all duration-300 shadow-lg flex items-center justify-center gap-2 group text-sm md:text-base">
                        Jetzt anfragen
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                        </svg>
                    </button>
                </div>

                <div class="glass-card p-6 md:p-8 space-y-6">
                    <h4 class="text-xs font-display font-bold text-sage-600 uppercase tracking-[0.2em]">Fahrzeug-Details</h4>
                    <div class="space-y-3">
                        <div class="flex justify-between items-start py-2 border-b border-white/5 gap-4">
                            <span class="text-sage-600 text-xs md:text-sm">Karosserie</span>
                            <span class="text-white font-medium text-xs md:text-sm text-right">Touring (Kombi)</span>
                        </div>
                        <div class="flex justify-between items-start py-2 border-b border-white/5 gap-4">
                            <span class="text-sage-600 text-xs md:text-sm">Variante</span>
                            <span class="text-white font-medium text-xs md:text-sm text-right">${model.split(' ').pop()}</span>
                        </div>
                        <div class="flex justify-between items-start py-2 border-b border-white/5 gap-4">
                            <span class="text-sage-600 text-xs md:text-sm">Türen/Sitze</span>
                            <span class="text-white font-medium text-xs md:text-sm text-right">5 / 5</span>
                        </div>
                        <div class="flex justify-between items-start py-2 border-b border-white/5 gap-4">
                            <span class="text-sage-600 text-xs md:text-sm">Standort</span>
                            <span class="text-white font-medium text-xs md:text-sm text-right">Pfaffstätt, OÖ</span>
                        </div>
                        <div class="flex justify-between items-start py-2 gap-4">
                            <span class="text-sage-600 text-xs md:text-sm whitespace-nowrap">Quelle</span>
                            <span class="text-white font-medium text-xs md:text-sm text-right">DE Händler</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>`;

            // 1. Open in new tab using Blob
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
            
            // 2. Also offer download just in case popup is blocked
            const a = document.createElement('a');
            a.href = url;
            a.download = `homepage_${brand.toLowerCase()}_${model.toLowerCase().replace(/\s+/g, '_')}.html`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            // Update button text to give feedback
            const origText = generateBtn.innerHTML;
            generateBtn.innerHTML = '✅ Homepage Generated & Downloaded!';
            setTimeout(() => { generateBtn.innerHTML = origText; }, 3000);
        });
    }
});
