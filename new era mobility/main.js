document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('url-input');
    const extractBtn = document.getElementById('extract-btn');
    const resultsContainer = document.getElementById('results-container');
    const jsonOutput = document.getElementById('json-output');
    const statusText = document.getElementById('status-text');
    const loaderIcon = extractBtn.querySelector('.loader-icon');
    const btnText = extractBtn.querySelector('span');

    extractBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        
        if (!url) {
            alert('Please enter a valid URL');
            return;
        }

        // UI Feedback: Start
        setLoading(true);
        statusText.innerText = 'Analyzing page structure...';
        
        console.log('Extraction initiated for:', url);

        // Simulate extraction process delay for UI feedback, then load actual JSON
        setTimeout(async () => {
            try {
                // Call the new backend extraction API with the user's URL using a relative URL
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ url: url })
                });
                
                if (!response.ok) {
                    const errtext = await response.text();
                    throw new Error(`Extraction failed on backend. Server returned ${response.status}: ${errtext}`);
                }
                const data = await response.json();
                
                statusText.innerText = 'Data extracted successfully!';
                
                // Use the first car object if inside 'cars' array, or return the whole object depending on what's expected
                const displayData = data.cars && data.cars.length > 0 ? data.cars[0] : data;
                
                updateExtractedData(displayData, true);
            } catch (error) {
                console.error('Error fetching data:', error);
                
                let errorMsg = "Failed to load actual data from extracted_cars.json.";
                if (window.location.protocol === 'file:') {
                    errorMsg += " IMPORTANT: Browsers block reading local JSON files for security (CORS) when opening HTML files directly. You must run a local web server (e.g., 'python -m http.server') to view this.";
                }
                
                statusText.innerText = 'Error loading data.';
                
                // Fallback to error display
                updateExtractedData({
                    status: "error",
                    message: errorMsg,
                    technical_details: error.message
                }, true);
            }
        }, 1000);
    });

    // PDF Upload Logic
    const pdfUploadZone = document.getElementById('pdf-upload-zone');
    const pdfInput = document.getElementById('pdf-input');
    const pdfStatus = document.getElementById('pdf-status');
    
    if (pdfUploadZone) {
        pdfUploadZone.addEventListener('click', () => pdfInput.click());
        
        pdfUploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            pdfUploadZone.classList.add('dragover');
        });
        
        pdfUploadZone.addEventListener('dragleave', () => {
            pdfUploadZone.classList.remove('dragover');
        });
        
        pdfUploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            pdfUploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'application/pdf') {
                handlePdfUpload(files[0]);
            } else {
                showPdfStatus('Bitte wählen Sie eine gültige PDF Datei aus.', 'error');
            }
        });
    }
    
    if (pdfInput) {
        pdfInput.addEventListener('change', () => {
            if (pdfInput.files.length > 0) {
                handlePdfUpload(pdfInput.files[0]);
            }
        });
    }
    
    async function handlePdfUpload(file) {
        setLoading(true);
        showPdfStatus(`Lade PDF hoch: ${file.name}...`, 'info');
        statusText.innerText = 'Analysiere PDF Datenblatt...';
        
        const formData = new FormData();
        formData.append('pdf', file);
        
        try {
            const response = await fetch('/api/extract-pdf', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                let errorMsg = 'PDF Extraktion fehlgeschlagen';
                try {
                    const err = await response.json();
                    errorMsg = err.message || errorMsg;
                } catch(e) {}
                throw new Error(errorMsg);
            }
            
            const data = await response.json();
            showPdfStatus('PDF erfolgreich analysiert!', 'success');
            
            // Handle consistent car data return
            const displayData = data.cars && data.cars.length > 0 ? data.cars[0] : data;
            
            // Add a flag that this was from PDF
            displayData.extraction_method = 'pdf';
            
            window.updateExtractedData(displayData, true);
            
        } catch (error) {
            console.error('PDF Upload Error:', error);
            showPdfStatus(`Fehler: ${error.message}`, 'error');
            statusText.innerText = 'Fehler bei PDF Analyse.';
            setLoading(false);
        }
    }
    
    function showPdfStatus(message, type) {
        if (!pdfStatus) return;
        pdfStatus.innerText = message;
        pdfStatus.className = 'helper-text ' + type;
        pdfStatus.style.display = 'block';
    }

    function setLoading(isLoading) {
        if (isLoading) {
            extractBtn.disabled = true;
            loaderIcon.classList.remove('hidden');
            btnText.innerText = 'Processing...';
        } else {
            extractBtn.disabled = false;
            loaderIcon.classList.add('hidden');
            btnText.innerText = 'Start Extraction';
        }
    }

    // Define the update function
    window.updateExtractedData = (data, isNew = false) => {
        setLoading(false);
        resultsContainer.classList.remove('hidden');
        if (!isNew) statusText.innerText = 'Restored session data';
        else statusText.innerText = 'Task Completed';
        
        jsonOutput.innerText = typeof data === 'string' ? data : JSON.stringify(data, null, 4);
        
        if (data && data.status !== 'error') {
            if (isNew) {
                // Save to localStorage only for NEW extractions
                try {
                    localStorage.setItem('lastExtractedCar', JSON.stringify(data));
                    
                    // Clear overrides and stale states for the new car
                    localStorage.removeItem('lastMarketCheapestPrice');
                    localStorage.removeItem('lastBuyStatus');
                    localStorage.removeItem('pricingState');
                    localStorage.removeItem('autoscoutState');
                    localStorage.removeItem('autoscoutLastPrices');
                    
                    // Clear Agent 4 overrides
                    const inputs = ['edit-title', 'edit-execution', 'edit-mileage', 'edit-reg', 'edit-color', 'edit-power', 'edit-price', 'edit-interieur', 'edit-technologie'];
                    inputs.forEach(id => localStorage.removeItem(`override_${id}`));

                    console.log('Saved new extracted data and cleared all stale states & overrides');
                } catch (e) {
                    console.warn('Failed to save to localStorage', e);
                }
            }
        } 
        
        // Scroll to results if new
        if (isNew) {
            resultsContainer.scrollIntoView({ behavior: 'smooth' });
        }
    };

    // Persistence: Load previous data on startup (AFTER function is defined)
    const savedCar = localStorage.getItem('lastExtractedCar');
    if (savedCar) {
        try {
            const data = JSON.parse(savedCar);
            statusText.innerText = 'Restored previous extraction';
            window.updateExtractedData(data);
        } catch (e) {
            console.warn('Failed to restore previous car data', e);
        }
    }
});
