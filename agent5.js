document.addEventListener('DOMContentLoaded', async () => {
    const carBody = document.getElementById('car-body');
    const noDataMsg = document.getElementById('no-data-msg');
    const saveBtn = document.getElementById('save-btn');
    const csvBtn = document.getElementById('csv-btn');
    const wixBtn = document.getElementById('wix-btn');

    let currentData = null;

    // Load Data
    async function loadData() {
        try {
            const response = await fetch('/extracted_cars.json');
            if (!response.ok) throw new Error('Failed to load data');
            currentData = await response.json();
            renderCards();
        } catch (error) {
            console.error('Error loading data:', error);
            noDataMsg.style.display = 'block';
        }
    }

    function renderCards() {
        const cars = currentData.cars || (currentData.title ? [currentData] : []);
        if (cars.length === 0) {
            noDataMsg.style.display = 'block';
            return;
        }

        carBody.innerHTML = '';
        const calculatedPriceStr = localStorage.getItem('lastCalculatedFinalPrice');
        const calculatedPrice = calculatedPriceStr ? Math.round(parseFloat(calculatedPriceStr)) : null;

        cars.forEach((car, index) => {
            // Fetch Agent 4 Overrides
            const agent4Title = localStorage.getItem('override_edit-title');
            const agent4Exec = localStorage.getItem('override_edit-execution');
            const agent4Mil = localStorage.getItem('override_edit-mileage');
            const agent4Reg = localStorage.getItem('override_edit-reg');
            const agent4Color = localStorage.getItem('override_edit-color');
            const agent4Power = localStorage.getItem('override_edit-power');
            const agent4Price = localStorage.getItem('override_edit-price');

            // Force Priority: 1. Agent 4 explicit overrides, 2. Agent 2 Calculation (Price), 3. agent5 saved state (car.*), 4. extracted raw state
            const displayPrice = agent4Price || calculatedPrice || car.carPrice || car.price || '';
            const displayModel = agent4Title || car.carModel || car.title || '';
            const displayExec = agent4Exec || car.carExecution || car.ausfuehrung || '';
            const displayPower = agent4Power || car.carPower || '';
            const displayMil = agent4Mil || car.carMileage || '';
            const displayReg = agent4Reg || car.carRegistration || '';
            const displayColor = agent4Color || car.carColor || '';
            
            // Assign these back to currentData object immediately so saving without modifying works correctly
            car.carPrice = displayPrice;
            car.carModel = displayModel;
            car.carExecution = displayExec;
            car.carPower = displayPower;
            car.carMileage = displayMil;
            car.carRegistration = displayReg;
            car.carColor = displayColor;
            
            const card = document.createElement('div');
            card.className = 'data-card savable';
            card.innerHTML = `
                <div class="card-header-flex">
                    <div style="display: flex; gap: 1.5rem; align-items: center;">
                        <img src="${car.carImage || ''}" style="width: 100px; height: 75px; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);" onerror="this.src='https://placehold.co/100x75?text=No+Image'">
                        <div>
                            <h3 style="margin-bottom: 0.3rem;">${car.carBrand || ''} ${displayModel}</h3>
                            <span class="badge" style="background: rgba(255,255,255,0.1); padding: 0.2rem 0.8rem; border-radius: 20px; font-size: 0.8rem;">Item #${index + 1}</span>
                        </div>
                    </div>
                    <button class="primary-btn" style="padding: 0.6rem 1rem; font-size: 0.85rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2);" onclick="window.open('${car.source || car.link}', '_blank')">🔗 Original Link</button>
                </div>
                
                <div class="grid-3col">
                    <div class="data-item">
                        <label class="data-label">Fahrzeug-Link (Agent 1)</label>
                        <input type="text" class="data-input" value="${car.source || car.link || ''}" data-field="source" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Nummer (ID)</label>
                        <input type="text" class="data-input" value="${car.carNumber || ''}" data-field="carNumber" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Hersteller</label>
                        <input type="text" class="data-input" value="${car.carBrand || ''}" data-field="carBrand" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Modell</label>
                        <input type="text" class="data-input" value="${displayModel}" data-field="carModel" data-index="${index}">
                    </div>
                    
                    <div class="data-item">
                        <label class="data-label">Ausführung</label>
                        <input type="text" class="data-input" value="${displayExec}" data-field="carExecution" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Kraftstoff</label>
                        <input type="text" class="data-input" value="${car.carFuel || ''}" data-field="carFuel" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Getriebe</label>
                        <input type="text" class="data-input" value="${car.carTransmission || ''}" data-field="carTransmission" data-index="${index}">
                    </div>

                    <div class="data-item">
                        <label class="data-label">PS</label>
                        <input type="text" class="data-input" value="${displayPower}" data-field="carPower" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">KM Stand</label>
                        <input type="text" class="data-input" value="${displayMil}" data-field="carMileage" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Erstzulassung</label>
                        <input type="text" class="data-input" value="${displayReg}" data-field="carRegistration" data-index="${index}">
                    </div>

                    <div class="data-item">
                        <label class="data-label">Farbe</label>
                        <input type="text" class="data-input" value="${displayColor}" data-field="carColor" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Farbe_Einfach</label>
                        <input type="text" class="data-input" value="${car.colorSimple || car.farbe_einfach || ''}" data-field="colorSimple" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Sofortkauf-Preis</label>
                        <input type="text" class="data-input" style="color: var(--accent); font-weight: bold; border-color: rgba(1, 253, 119, 0.3);" value="${displayPrice}" data-field="carPrice" data-index="${index}">
                    </div>
                </div>
            `;
            carBody.appendChild(card);
        });

        // Add change listeners
        document.querySelectorAll('.data-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = e.target.dataset.index;
                const field = e.target.dataset.field;
                const val = e.target.value;
                const cars = currentData.cars || [currentData];
                
                cars[idx][field] = val;
                e.target.closest('.data-card').classList.add('modified');
                
                // Sync back to localStorage so manual Agent 5 edits don't get overwritten by Agent 4 on refresh
                if (field === 'carPrice') { localStorage.setItem('override_edit-price', val); localStorage.setItem('lastCalculatedFinalPrice', val); }
                if (field === 'carModel') localStorage.setItem('override_edit-title', val);
                if (field === 'carExecution') localStorage.setItem('override_edit-execution', val);
                if (field === 'carPower') localStorage.setItem('override_edit-power', val);
                if (field === 'carMileage') localStorage.setItem('override_edit-mileage', val);
                if (field === 'carRegistration') localStorage.setItem('override_edit-reg', val);
                if (field === 'carColor') localStorage.setItem('override_edit-color', val);
            });
        });
    }

    // Save Logic
    saveBtn.addEventListener('click', async () => {
        const origText = saveBtn.innerHTML;
        saveBtn.innerHTML = 'Saving...';
        try {
            const response = await fetch('/api/save-cars', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentData)
            });
            if (!response.ok) throw new Error('Save failed');
            saveBtn.innerHTML = '✅ Saved!';
            document.querySelectorAll('.modified').forEach(tr => tr.classList.remove('modified'));
            setTimeout(() => { saveBtn.innerHTML = origText; }, 2000);
        } catch (error) {
            alert('Error: ' + error.message);
            saveBtn.innerHTML = '❌ Error';
            setTimeout(() => { saveBtn.innerHTML = origText; }, 2000);
        }
    });

    // CSV Logic
    csvBtn.addEventListener('click', async () => {
        const origText = csvBtn.innerHTML;
        csvBtn.innerHTML = 'Exporting...';
        try {
            const response = await fetch('/api/export-csv', { method: 'POST' });
            if (!response.ok) throw new Error('CSV Export failed');
            
            // Trigger actual download
            const csvTextResponse = await fetch('/aktive_sammlung.csv');
            const csvText = await csvTextResponse.text();
            const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'aktive_sammlung.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            csvBtn.innerHTML = '✅ Erfolgreich!';
            setTimeout(() => { csvBtn.innerHTML = origText; }, 2000);
        } catch (error) {
            alert('Error: ' + error.message);
            csvBtn.innerHTML = '❌ Error';
        }
    });

    // Wix Logic
    wixBtn.addEventListener('click', async () => {
        const origText = wixBtn.innerHTML;
        wixBtn.innerHTML = '⌛ Preparing Sync...';
        try {
            // Step 1: Auto-Save current data to extracted_cars.json
            const saveResp = await fetch('/api/save-cars', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentData)
            });
            if (!saveResp.ok) throw new Error('Auto-save failed before sync');
            document.querySelectorAll('.modified').forEach(tr => tr.classList.remove('modified'));

            // Step 2: Auto-Export to Csv (updates aktive_sammlung.csv which wix_sync.py reads)
            const csvResp = await fetch('/api/export-csv', { method: 'POST' });
            if (!csvResp.ok) throw new Error('CSV generation failed before sync');

            // Step 3: Run the actual Wix Sync
            wixBtn.innerHTML = '⌛ Syncing to Wix...';
            const syncResp = await fetch('/api/sync-wix', { method: 'POST' });
            if (!syncResp.ok) throw new Error('Wix Sync API failed');
            
            wixBtn.innerHTML = '✅ Auto-Saved & Synced!';
            setTimeout(() => { wixBtn.innerHTML = origText; }, 3000);
        } catch (error) {
            alert('Wix Sync Error: ' + error.message);
            wixBtn.innerHTML = '❌ Error';
            setTimeout(() => { wixBtn.innerHTML = origText; }, 3000);
        }
    });

    loadData();
});
