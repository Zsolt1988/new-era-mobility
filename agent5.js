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
            renderTable();
        } catch (error) {
            console.error('Error loading data:', error);
            noDataMsg.style.display = 'block';
        }
    }

    function renderTable() {
        const cars = currentData.cars || (currentData.title ? [currentData] : []);
        if (cars.length === 0) {
            noDataMsg.style.display = 'block';
            return;
        }

        carBody.innerHTML = '';
        cars.forEach((car, index) => {
            const row = document.createElement('tr');
            row.classList.add('savable');
            row.innerHTML = `
                <td><img src="${car.carImage || ''}" style="width: 60px; height: 40px; object-fit: cover; border-radius: 4px;" onerror="this.src='https://placehold.co/60x40?text=No+Image'"></td>
                <td><input type="text" value="${car.carBrand || ''}" data-field="carBrand" data-index="${index}"></td>
                <td><input type="text" value="${car.carModel || car.title || ''}" data-field="carModel" data-index="${index}"></td>
                <td><input type="text" value="${car.carExecution || car.ausfuehrung || ''}" data-field="carExecution" data-index="${index}"></td>
                <td><input type="text" value="${car.carFuel || ''}" data-field="carFuel" data-index="${index}"></td>
                <td><input type="text" value="${car.carTransmission || ''}" data-field="carTransmission" data-index="${index}"></td>
                <td><input type="text" value="${car.carPower || ''}" data-field="carPower" data-index="${index}"></td>
                <td><input type="text" value="${car.carMileage || ''}" data-field="carMileage" data-index="${index}"></td>
                <td><input type="text" value="${car.carRegistration || ''}" data-field="carRegistration" data-index="${index}"></td>
                <td><input type="text" value="${car.carColor || ''}" data-field="carColor" data-index="${index}"></td>
                <td><input type="text" value="${car.colorSimple || car.farbe_einfach || ''}" data-field="colorSimple" data-index="${index}"></td>
                <td><input type="text" value="${car.carPrice || car.price || ''}" data-field="carPrice" data-index="${index}"></td>
                <td style="text-align: center;"><button class="primary-btn" style="padding: 0.5rem; font-size: 0.7rem; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);" onclick="window.open('${car.source || car.link}', '_blank')">🔗</button></td>
            `;
            carBody.appendChild(row);
        });

        // Add change listeners
        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = e.target.dataset.index;
                const field = e.target.dataset.field;
                const cars = currentData.cars || [currentData];
                cars[idx][field] = e.target.value;
                e.target.closest('tr').classList.add('modified');
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
        wixBtn.innerHTML = '⌛ Syncing...';
        try {
            const response = await fetch('/api/sync-wix', { method: 'POST' });
            if (!response.ok) throw new Error('Wix Sync failed');
            wixBtn.innerHTML = '✅ Synced!';
            setTimeout(() => { wixBtn.innerHTML = origText; }, 3000);
        } catch (error) {
            alert('Wix Error: ' + error.message);
            wixBtn.innerHTML = '❌ Error';
            setTimeout(() => { wixBtn.innerHTML = origText; }, 3000);
        }
    });

    loadData();
});
