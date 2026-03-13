document.addEventListener('DOMContentLoaded', async () => {
    const basePriceInput = document.getElementById('base-price');
    const distanceInput = document.getElementById('distance');
    const regInput = document.getElementById('registration');
    const carNameTitle = document.getElementById('car-name');
    const statusBadge = document.getElementById('price-status-badge');
    
    const displayOriginal = document.getElementById('display-original');
    const displayNetto = document.getElementById('display-netto');
    const displayTransport = document.getElementById('display-transport');
    const displayReg = document.getElementById('display-reg');
    const displayInternal = document.getElementById('display-internal');
    const displayMargin = document.getElementById('display-margin');
    const displayTotal = document.getElementById('display-total');

    let currentCarData = null;

    // Try to load data from localStorage first (pushed by Agent 1)
    try {
        const storedData = localStorage.getItem('lastExtractedCar');
        if (storedData) {
            const data = JSON.parse(storedData);
            console.log('Loaded data from localStorage');
            // Data from localStorage might already be the single car object from main.js logic, 
            // but let's handle both in case it's the full API response
            currentCarData = data.cars && data.cars.length > 0 ? data.cars[0] : data;
            
            // Check if it's a valid car object before proceeding
            if (currentCarData && !currentCarData.status && (currentCarData.price || currentCarData.carPrice)) {
                initCalculator(currentCarData);
                return; // Exit early if we successfully loaded from localStorage
            }
        }
    } catch (e) {
        console.warn('Could not load data from localStorage:', e);
    }

    // Fallback: Load data from extracted_cars.json via API/fetch
    try {
        const response = await fetch('extracted_cars.json?nc=' + new Date().getTime());
        if (!response.ok) throw new Error('No data');
        const data = await response.json();
        
        if (data.cars && data.cars.length > 0) {
            currentCarData = data.cars[0];
            initCalculator(currentCarData);
        } else {
            showNoData();
        }
    } catch (e) {
        console.warn('Could not load data from fetch:', e);
        showNoData();
    }

    function showNoData() {
        document.getElementById('calculator-ui').classList.add('hidden');
        document.getElementById('no-data-warning').classList.remove('hidden');
    }

    function initCalculator(car) {
        carNameTitle.innerText = car.title || `${car.carBrand} ${car.carModel}`;
        
        let price = parseFloat(car.price || car.carPrice);
        basePriceInput.value = price;
        
        const status = (car.price_status || 'brutto').toLowerCase();
        statusBadge.innerText = status;
        statusBadge.className = `badge-status badge-${status}`;
        
        calculate();
    }

    function calculate() {
        const basePrice = parseFloat(basePriceInput.value) || 0;
        const distance = parseFloat(distanceInput.value) || 0;
        const regFee = parseFloat(regInput.value) || 0;
        
        const isBrutto = statusBadge.innerText.toLowerCase() === 'brutto';
        
        // 1. Calculate Netto
        // If it's Brutto, divide by 1.19
        const nettoValue = isBrutto ? basePrice / 1.19 : basePrice;
        
        // 2. Transport Costs
        const transportCosts = distance * 1.2;
        
        // 3. Internal Costs Total
        const internalCosts = nettoValue + transportCosts + regFee;
        
        // 4. Revenue Margin (7%)
        const margin = internalCosts * 0.07;
        
        // 5. Margin Price (Subtotal before AT VAT)
        const subtotal = internalCosts + margin;
        
        // 6. Austrian VAT (20%)
        const atVat = subtotal * 0.20;
        
        // 7. Final Selling Price (Brutto AT)
        const finalPrice = subtotal + atVat;

        // UI Updates
        displayOriginal.innerText = formatEuro(basePrice);
        displayNetto.innerText = formatEuro(nettoValue);
        displayTransport.innerText = formatEuro(transportCosts);
        displayReg.innerText = formatEuro(regFee);
        displayInternal.innerText = formatEuro(internalCosts);
        displayMargin.innerText = formatEuro(margin);
        document.getElementById('display-vat-at').innerText = formatEuro(atVat);
        displayTotal.innerText = formatEuro(finalPrice);
    }

    function formatEuro(value) {
        return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value);
    }

    // Event Listeners
    [basePriceInput, distanceInput, regInput].forEach(input => {
        input.addEventListener('input', calculate);
    });

    const recalculateBtn = document.getElementById('recalculate-btn');
    if (recalculateBtn) {
        recalculateBtn.addEventListener('click', calculate);
    }
});
