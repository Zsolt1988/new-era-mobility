document.addEventListener('DOMContentLoaded', async () => {
    // Basic Info Inputs
    const brandInput = document.getElementById('brand');
    const modelInput = document.getElementById('model');
    const versionInput = document.getElementById('version');
    const regFromInput = document.getElementById('reg-from');
    const regToInput = document.getElementById('reg-to');
    const mileageFromInput = document.getElementById('mileage-from');
    const mileageInput = document.getElementById('mileage');
    const fuelSelect = document.getElementById('fuel-type');
    
    // UI Elements
    const carNameTitle = document.getElementById('car-name');
    const urlOutput = document.getElementById('url-output');
    const openLinkBtn = document.getElementById('open-link-btn');
    const generateBtn = document.getElementById('generate-btn');

    // Equipment Checkboxes
    const eqCheckboxes = [
        document.getElementById('eq-11'),
        document.getElementById('eq-20'),
        document.getElementById('eq-34'),
        document.getElementById('eq-50'),
        document.getElementById('eq-133'),
        document.getElementById('eq-140'),
        document.getElementById('eq-123')
    ];

    // Event Listeners for live updates
    function generateAndFetch() {
        const newUrl = generateUrl();
        triggerPriceFetch(newUrl);
    }

    const allInputs = [brandInput, modelInput, versionInput, regFromInput, regToInput, mileageFromInput, mileageInput, fuelSelect, ...eqCheckboxes];
    allInputs.forEach(input => {
        if(input) input.addEventListener('change', generateAndFetch);
        if(input && input.type === 'text' || input.type === 'number') input.addEventListener('keyup', () => {
             // For text/number inputs on keyup, let's just generate the URL so it feels live, but maybe don't hammer the fetch API.
             // Actually, user expects fetch when URL changes, so let's debounce or omit fetch on keyup to prevent spam.
             generateUrl();
        });
    });
    
    // ---- Fetch Prices from backend ----
    const fetchPricesBtn = document.getElementById('fetch-prices-btn');
    const priceList = document.getElementById('price-list');
    const priceStatusMsg = document.getElementById('price-status-msg');

    function setPriceRowsLoading() {
        const rows = priceList.querySelectorAll('.price-row');
        rows.forEach(row => {
            row.classList.add('loading');
            row.querySelector('.price-value').textContent = 'Fetching…';
        });
        priceStatusMsg.textContent = '';
    }

    function setPriceRows(prices) {
        const rows = priceList.querySelectorAll('.price-row');
        rows.forEach((row, i) => {
            row.classList.remove('loading');
            const valEl = row.querySelector('.price-value');
            if (prices[i]) {
                valEl.textContent = prices[i].formatted;
            } else {
                valEl.textContent = '—';
            }
        });
    }

    async function triggerPriceFetch(overrideUrl = null) {
        const searchUrl = overrideUrl || urlOutput.innerText.trim();
        if (!searchUrl || searchUrl.startsWith('https://www.autoscout24.at/lst/...')) {
            if(priceStatusMsg) priceStatusMsg.textContent = '⚠️ Please configure the search first.';
            return;
        }

        // Append dealer-only filter
        const dealerUrl = searchUrl + '&custtype=D';

        setPriceRowsLoading();
        if(fetchPricesBtn) {
            fetchPricesBtn.disabled = true;
            fetchPricesBtn.textContent = 'Fetching…';
        }

        try {
            // Use relative URL to match the current running port
            const apiUrl = `/api/autoscout-prices?url=${encodeURIComponent(dealerUrl)}`;
            const resp = await fetch(apiUrl);
            const data = await resp.json();

            if (data.status === 'ok' && data.prices && data.prices.length > 0) {
                setPriceRows(data.prices);
                if(priceStatusMsg) priceStatusMsg.textContent = '';
                
                // Save the cheapest price (rank 1) for Agent 2 consumption
                const cheapest = data.prices[0].price;
                localStorage.setItem('lastMarketCheapestPrice', cheapest);
                
                // Save full price list for persistence in Agent 3 UI
                localStorage.setItem('autoscoutLastPrices', JSON.stringify(data.prices));
                console.log("Saved prices to localStorage");
            } else {
                setPriceRows([]);
                if(priceStatusMsg) priceStatusMsg.textContent = '⚠️ ' + (data.message || 'No prices found.');
            }
        } catch (err) {
            setPriceRows([]);
            if(priceStatusMsg) priceStatusMsg.textContent = '⚠️ Could not reach backend. Is the server running?';
        }

        if(fetchPricesBtn) {
            fetchPricesBtn.disabled = false;
            fetchPricesBtn.textContent = '🔍 Fetch Prices';
        }
    }

    if (fetchPricesBtn) {
        fetchPricesBtn.addEventListener('click', () => {
            // Read fresh URL directly from the generated field
            const freshUrl = urlOutput.innerText.trim();
            console.log("Fetching prices for explicitly read URL:", freshUrl);
            triggerPriceFetch(freshUrl);
        });
    }

    // Load Data Phase
    if (loadState()) {
        console.log('Loaded saved autoscout state');
        const storedData = localStorage.getItem('lastExtractedCar');
        if (storedData) {
            try {
                const data = JSON.parse(storedData);
                currentCarData = data.cars && data.cars.length > 0 ? data.cars[0] : data;
                if (currentCarData && carNameTitle) {
                    carNameTitle.innerText = currentCarData.title || `${currentCarData.carBrand} ${currentCarData.carModel}`;
                }
            } catch(e) {}
        }
        generateUrl();
        return;
    }

    try {
        const storedData = localStorage.getItem('lastExtractedCar');
        if (storedData) {
            const data = JSON.parse(storedData);
            currentCarData = data.cars && data.cars.length > 0 ? data.cars[0] : data;
            
            if (currentCarData && !currentCarData.status && (currentCarData.carBrand || currentCarData.title)) {
                initForm(currentCarData);
                return;
            }
        }
    } catch (e) {
        console.warn('Could not load data from localStorage:', e);
    }

    // Fallback Fetch
    try {
        const response = await fetch('extracted_cars.json?nc=' + new Date().getTime());
        if (response.ok) {
            const data = await response.json();
            if (data.cars && data.cars.length > 0) {
                currentCarData = data.cars[0];
                initForm(currentCarData);
                return;
            }
        }
        showNoData();
    } catch (e) {
        console.warn('Could not load data from fetch:', e);
        showNoData();
    }

    function showNoData() {
        document.getElementById('configurator-ui').classList.add('hidden');
        document.getElementById('no-data-warning').classList.remove('hidden');
    }

    function initForm(car) {
        carNameTitle.innerText = car.title || `${car.carBrand} ${car.carModel}`;

        // 1. Map Brand & Model
        brandInput.value = formatForUrl(car.carBrand || "");
        
        // Model mapping: strip trim descriptors if possible, or just lower-kebab it
        // Example: "SEAL U DM-i 18.3 kWh FWD Boost" -> "seal-u" or "seal"
        // Since models can be complex, we'll try to just take the first word or user can edit
        let modelStr = car.carModel || "";
        if (modelStr) {
            // Very naive split for BYD SEAL 6, etc.
            let parts = modelStr.split(' ');
            if(parts.length > 0) {
                // Keep the first two chunks usually (e.g. Model 3, SEAL U, Golf VII)
                modelInput.value = formatForUrl(parts.slice(0, 2).join('-'));
            } else {
                modelInput.value = formatForUrl(modelStr);
            }
        }

        // 2. Map Fuel
        const fuelStr = (car.carFuel || "").toLowerCase();
        if (fuelStr.includes("plug-in") || fuelStr.includes("phev")) {
            fuelSelect.value = "2";
        } else if (fuelStr.includes("elektro") || fuelStr.includes("electric")) {
            fuelSelect.value = "E";
        } else if (fuelStr.includes("diesel")) {
            fuelSelect.value = "D";
        } else if (fuelStr.includes("benzin") || fuelStr.includes("petrol")) {
            fuelSelect.value = "B";
        }

        // 3. Map Registration Year
        if (car.carRegistration) {
            const yearMatch = car.carRegistration.match(/\d{4}/);
            if (yearMatch) {
                const year = parseInt(yearMatch[0]);
                regFromInput.value = year;
                regToInput.value = year;
            }
        }

        // 4. Map Mileage
        if (car.carMileage) {
             let kmMatch = car.carMileage.match(/\d+/g);
             if(kmMatch) {
                 let km = parseInt(kmMatch.join(''));
                 mileageFromInput.value = Math.max(0, Math.floor((km - 10000) / 10000) * 10000);
                 mileageInput.value = Math.ceil((km + 10000) / 10000) * 10000;
             }
        } else {
             mileageFromInput.value = 0;
             mileageInput.value = 30000; // default
        }

        // 5. Map Equipment (Searching the features block)
        const allText = JSON.stringify(car.features || {}) + JSON.stringify(car.highlights || []) + JSON.stringify(car.specs || {});
        const lowerText = allText.toLowerCase();

        // Allrad (11)
        if (lowerText.includes("allrad") || lowerText.includes("4x4") || lowerText.includes("awd")) document.getElementById('eq-11').checked = true;
        // Anhängerkupplung (20)
        if (lowerText.includes("anhängerkupplung") || lowerText.includes("ahk")) document.getElementById('eq-20').checked = true;
        // Sitzheizung (34)
        if (lowerText.includes("sitzheitzung") || lowerText.includes("sitzheizung") || lowerText.includes("beheizbare sitze")) document.getElementById('eq-34').checked = true;
        // Panoramadach (50)
        if (lowerText.includes("panoramadach") || lowerText.includes("schiebedach")) document.getElementById('eq-50').checked = true;
        // ACC (133)
        if (lowerText.includes("abstandstempomat") || lowerText.includes("acc")) document.getElementById('eq-133').checked = true;
        // Matrix LED (140)
        if (lowerText.includes("matrix") && lowerText.includes("led")) document.getElementById('eq-140').checked = true;
        // HUD (123)
        if (lowerText.includes("headupdisplay") || lowerText.includes("hud") || lowerText.includes("head-up")) document.getElementById('eq-123').checked = true;

        const initialUrl = generateUrl();
        // Trigger fetch immediately with the guaranteed correct URL
        triggerPriceFetch(initialUrl);
    }

    function formatForUrl(str) {
        return str.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    }

    function generateUrl() {
        const brand = formatForUrl(brandInput.value);
        const model = formatForUrl(modelInput.value);
        
        let url = `https://www.autoscout24.at/lst`;
        if (brand) url += `/${brand}`;
        if (model) url += `/${model}`;
        
        url += `?atype=C&cy=A&damaged_listing=exclude&desc=0`;

        const eqValues = eqCheckboxes.filter(cb => cb.checked).map(cb => cb.value);
        if (eqValues.length > 0) {
            url += `&eq=${eqValues.join('%2C')}`;
        }

        const fregfrom = regFromInput.value;
        if (fregfrom) url += `&fregfrom=${fregfrom}`;

        const fregto = regToInput.value;
        if (fregto) url += `&fregto=${fregto}`;

        const fuel = fuelSelect.value;
        if (fuel) url += `&fuel=${fuel}`;

        const kmfrom = mileageFromInput.value;
        if (kmfrom) url += `&kmfrom=${kmfrom}`;

        const kmto = mileageInput.value;
        if (kmto) url += `&kmto=${kmto}`;

        url += `&powertype=kw&sort=price&ustate=N%2CU`;

        const version = versionInput.value.trim();
        if (version) url += `&version0=${encodeURIComponent(version)}`;

        urlOutput.innerText = url;
        openLinkBtn.href = url;
        
        saveState();
        return url;
    }

    function saveState() {
        const state = {
            brand: brandInput ? brandInput.value : '',
            model: modelInput ? modelInput.value : '',
            version: versionInput ? versionInput.value : '',
            regFrom: regFromInput ? regFromInput.value : '',
            regTo: regToInput ? regToInput.value : '',
            mileageFrom: mileageFromInput ? mileageFromInput.value : '',
            mileageTo: mileageInput ? mileageInput.value : '',
            fuel: fuelSelect ? fuelSelect.value : '',
            equipment: eqCheckboxes.map(cb => ({ id: cb.id, checked: cb.checked }))
        };
        localStorage.setItem('autoscoutState', JSON.stringify(state));
    }

    function loadState() {
        const stored = localStorage.getItem('autoscoutState');
        if (stored) {
            const state = JSON.parse(stored);
            if(brandInput) brandInput.value = state.brand;
            if(modelInput) modelInput.value = state.model;
            if(versionInput) versionInput.value = state.version || '';
            if(regFromInput) regFromInput.value = state.regFrom;
            if(regToInput) regToInput.value = state.regTo;
            if(mileageFromInput) mileageFromInput.value = state.mileageFrom;
            if(mileageInput) mileageInput.value = state.mileageTo;
            if(fuelSelect) fuelSelect.value = state.fuel;
            state.equipment.forEach(eq => {
                const cb = document.getElementById(eq.id);
                if (cb) cb.checked = eq.checked;
            });

            // Restore last fetched prices if they exist
            const savedPrices = localStorage.getItem('autoscoutLastPrices');
            if (savedPrices) {
                try {
                    setPriceRows(JSON.parse(savedPrices));
                } catch(e) {}
            }

            return true;
        }
        return false;
    }

    if(generateBtn) {
        generateBtn.addEventListener('click', () => {
            const newUrl = generateUrl();
            console.log("Auto-fetching with strictly returned URL:", newUrl);
            triggerPriceFetch(newUrl);
        });
    }
});

