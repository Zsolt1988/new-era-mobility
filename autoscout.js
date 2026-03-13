document.addEventListener('DOMContentLoaded', async () => {
    // Basic Info Inputs
    const brandInput = document.getElementById('brand');
    const modelInput = document.getElementById('model');
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
    const allInputs = [brandInput, modelInput, regFromInput, regToInput, mileageFromInput, mileageInput, fuelSelect, ...eqCheckboxes];
    allInputs.forEach(input => {
        if(input) input.addEventListener('change', generateUrl);
        if(input && input.type === 'text' || input.type === 'number') input.addEventListener('keyup', generateUrl);
    });
    
    if(generateBtn) generateBtn.addEventListener('click', generateUrl);

    let currentCarData = null;

    // Load Data Phase
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
                regFromInput.value = year - 1; // Range
                regToInput.value = year + 1;
            }
        }

        // 4. Map Mileage
        if (car.carMileage) {
             let kmMatch = car.carMileage.match(/\d+/g);
             if(kmMatch) {
                 let km = parseInt(kmMatch.join(''));
                 mileageFromInput.value = Math.max(0, km - 5000); // e.g. 5000 km below current
                 mileageInput.value = km < 10000 ? 15000 : km + 10000;
             }
        } else {
             mileageFromInput.value = 0;
             mileageInput.value = 25000; // default
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

        generateUrl();
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

        urlOutput.innerText = url;
        openLinkBtn.href = url;
    }
});
