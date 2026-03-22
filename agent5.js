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
        cars.forEach((car, index) => {
            const card = document.createElement('div');
            card.className = 'data-card savable';
            card.innerHTML = `
                <div class="card-header-flex">
                    <div style="display: flex; gap: 1.5rem; align-items: center;">
                        <img src="${car.carImage || ''}" style="width: 100px; height: 75px; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);" onerror="this.src='https://placehold.co/100x75?text=No+Image'">
                        <div>
                            <h3 style="margin-bottom: 0.3rem;">${car.carBrand || ''} ${car.carModel || car.title || ''}</h3>
                            <span class="badge" style="background: rgba(255,255,255,0.1); padding: 0.2rem 0.8rem; border-radius: 20px; font-size: 0.8rem;">Item #${index + 1}</span>
                        </div>
                    </div>
                    <button class="primary-btn" style="padding: 0.6rem 1rem; font-size: 0.85rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2);" onclick="window.open('${car.source || car.link}', '_blank')">🔗 Original Link</button>
                </div>
                
                <div class="grid-3col">
                    <div class="data-item">
                        <label class="data-label">Bild_Gallery1 (URL)</label>
                        <input type="text" class="data-input" value="${car.carImage || ''}" data-field="carImage" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Hersteller</label>
                        <input type="text" class="data-input" value="${car.carBrand || ''}" data-field="carBrand" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Modell</label>
                        <input type="text" class="data-input" value="${car.carModel || car.title || ''}" data-field="carModel" data-index="${index}">
                    </div>
                    
                    <div class="data-item">
                        <label class="data-label">Ausführung</label>
                        <input type="text" class="data-input" value="${car.carExecution || car.ausfuehrung || ''}" data-field="carExecution" data-index="${index}">
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
                        <input type="text" class="data-input" value="${car.carPower || ''}" data-field="carPower" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">KM Stand</label>
                        <input type="text" class="data-input" value="${car.carMileage || ''}" data-field="carMileage" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Erstzulassung</label>
                        <input type="text" class="data-input" value="${car.carRegistration || ''}" data-field="carRegistration" data-index="${index}">
                    </div>

                    <div class="data-item">
                        <label class="data-label">Farbe</label>
                        <input type="text" class="data-input" value="${car.carColor || ''}" data-field="carColor" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Farbe_Einfach</label>
                        <input type="text" class="data-input" value="${car.colorSimple || car.farbe_einfach || ''}" data-field="colorSimple" data-index="${index}">
                    </div>
                    <div class="data-item">
                        <label class="data-label">Sofortkauf-Preis</label>
                        <input type="text" class="data-input" style="color: var(--accent); font-weight: bold; border-color: rgba(1, 253, 119, 0.3);" value="${car.carPrice || car.price || ''}" data-field="carPrice" data-index="${index}">
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
                const cars = currentData.cars || [currentData];
                cars[idx][field] = e.target.value;
                e.target.closest('.data-card').classList.add('modified');
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
