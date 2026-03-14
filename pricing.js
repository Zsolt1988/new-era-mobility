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
    const displayVatAt = document.getElementById('display-vat-at');
    const displayNova = document.getElementById('display-nova');
    const displayTotal = document.getElementById('display-total');

    // New inputs for NoVA
    const regYearInput = document.getElementById('reg-year');
    const co2Input = document.getElementById('co2-value');
    const marginPercentInput = document.getElementById('margin-percent');

    let currentCarData = null;

    // Register event listeners immediately so they work regardless of data source
    [basePriceInput, distanceInput, regInput, regYearInput, co2Input, marginPercentInput].forEach(input => {
        if(input) input.addEventListener('input', calculate);
    });
    const recalculateBtn = document.getElementById('recalculate-btn');
    if (recalculateBtn) {
        recalculateBtn.addEventListener('click', calculate);
    }

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

        // Attempt to parse Registration Year
        if (car.carRegistration) {
            const yearMatch = car.carRegistration.match(/\d{4}/);
            if (yearMatch) regYearInput.value = yearMatch[0];
        }

        // Attempt to parse CO2 (often looks like "110 g/km" or "60")
        if (car.specs && car.specs["CO2 WLTP"]) {
            const co2Match = car.specs["CO2 WLTP"].match(/\d+/);
            if (co2Match) co2Input.value = co2Match[0];
        }
        
        calculate();
    }

    function calculate() {
        const basePrice = parseFloat(basePriceInput.value) || 0;
        const distance = parseFloat(distanceInput.value) || 0;
        const regFee = parseFloat(regInput.value) || 0;
        const regYear = parseInt(regYearInput.value) || 2025;
        const co2 = parseInt(co2Input.value) || 0;
        
        const isBrutto = statusBadge.innerText.toLowerCase() === 'brutto';
        
        // 1. Calculate Netto
        // If it's Brutto, divide by 1.19
        const nettoValue = isBrutto ? basePrice / 1.19 : basePrice;
        
        // 2. Transport Costs
        const transportCosts = distance * 1.2;
        
        // 3. Internal Costs Total
        const internalCosts = nettoValue + transportCosts + regFee;
        
        // 4. Revenue Margin (Custom %)
        const marginPercent = (parseFloat(marginPercentInput.value) || 0) / 100;
        const margin = internalCosts * marginPercent;
        
        // 5. Margin Price (Subtotal before AT VAT)
        const subtotal = internalCosts + margin;
        
        // 6. Austrian VAT (20%)
        const atVat = subtotal * 0.20;
        
        // --- NoVA Calculation (M1 Logic for 2025/2026) ---
        const pkw_abzug = 94 - (regYear - 2025) * 3;
        const malus_grenze = 150 - (regYear - 2025) * 5;
        const malus_pro_gramm = 90 + (regYear - 2025) * 10;
        
        let nova_prozent = (co2 - pkw_abzug) / 5;
        nova_prozent = Math.min(Math.max(0, Math.round(nova_prozent)), 80);
        
        let malus_euro = 0;
        if (co2 > malus_grenze) {
            malus_euro = (co2 - malus_grenze) * malus_pro_gramm;
        }

        // NoVA is calculated from the Netto Selling Price (Subtotal), plus any fixed malus
        const novaTotal = (subtotal * (nova_prozent / 100)) + malus_euro;
        
        // 7. Final Selling Price (Brutto AT + NoVA)
        const finalPrice = subtotal + atVat + novaTotal;
        localStorage.setItem('lastCalculatedFinalPrice', finalPrice);

        // UI Updates
        displayOriginal.innerText = formatEuro(basePrice);
        displayNetto.innerText = formatEuro(nettoValue);
        displayTransport.innerText = formatEuro(transportCosts);
        displayReg.innerText = formatEuro(regFee);
        displayInternal.innerText = formatEuro(internalCosts);
        displayMargin.innerText = formatEuro(margin);
        displayVatAt.innerText = formatEuro(atVat);
        if(displayNova) displayNova.innerText = formatEuro(novaTotal) + ` (${nova_prozent}%)`;
        displayTotal.innerText = formatEuro(finalPrice);

        // --- Market Comparison Logic ---
        const marketPriceStr = localStorage.getItem('lastMarketCheapestPrice');
        const comparisonData = document.getElementById('comparison-data');
        const displayMarketPrice = document.getElementById('display-market-price');
        const displayDiff = document.getElementById('display-diff');
        const ampelContainer = document.querySelector('.ampel-container');
        const recommendationText = document.getElementById('recommendation-text');

        if (marketPriceStr && comparisonData) {
            const marketPrice = parseFloat(marketPriceStr);
            comparisonData.classList.remove('hidden');
            displayMarketPrice.innerText = formatEuro(marketPrice);

            // Difference logic: (Market - Calculated) / Market
            const diff = (marketPrice - finalPrice) / marketPrice;
            const diffPercent = (diff * 100).toFixed(2);
            displayDiff.innerText = (diff > 0 ? '+' : '') + diffPercent + '%';

            // Reset classes
            ampelContainer.classList.remove('green', 'orange', 'red');

            if (diff >= 0.02) {
                ampelContainer.classList.add('green');
                recommendationText.innerText = 'Kaufempfehlung: JA (Günstiger als Markt)';
                localStorage.setItem('lastBuyStatus', 'green');
            } else if (diff <= -0.02) {
                ampelContainer.classList.add('red');
                recommendationText.innerText = 'Kaufempfehlung: NEIN (Teurer als Markt)';
                localStorage.setItem('lastBuyStatus', 'red');
            } else {
                ampelContainer.classList.add('orange');
                recommendationText.innerText = 'Kaufempfehlung: NEUTRAL (Marktniveau)';
                localStorage.setItem('lastBuyStatus', 'orange');
            }
        } else {
            // Reset to default waiting state if no data
            if(comparisonData) comparisonData.classList.add('hidden');
            if(ampelContainer) ampelContainer.classList.remove('green', 'orange', 'red');
            if(recommendationText) recommendationText.innerText = 'Please fetch prices in Agent 3 first';
        }
    }

    function formatEuro(value) {
        return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value);
    }

});
