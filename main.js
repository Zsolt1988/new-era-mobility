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
                // Call the new backend extraction API with the user's URL using an absolute URL
                const response = await fetch('http://localhost:8080/api/extract', {
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
                
                updateExtractedData(displayData);
            } catch (error) {
                console.error('Error fetching data:', error);
                
                let errorMsg = "Failed to load actual data from extracted_cars.json.";
                if (window.location.protocol === 'file:') {
                    errorMsg += " IMPORTANT: Browsers block reading local JSON files for security (CORS) when opening HTML files directly. You must run a local web server (e.g., 'python -m http.server') to view this.";
                }
                
                statusText.innerText = 'Error loading data.';
                // alert(error.message); // removed alert to be less annoying
                
                // Fallback to error display
                updateExtractedData({
                    status: "error",
                    message: errorMsg,
                    technical_details: error.message
                });
            }
        }, 1000);
    });

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

    // This listener would be hit when the AI manually updates the UI
    window.updateExtractedData = (data) => {
        setLoading(false);
        resultsContainer.classList.remove('hidden');
        statusText.innerText = 'Task Completed';
        jsonOutput.innerText = JSON.stringify(data, null, 4);
        
        const btnGotoPricing = document.getElementById('btn-goto-pricing');
        if (data && data.status !== 'error') {
            // Save to localStorage for Agent 2
            try {
                localStorage.setItem('lastExtractedCar', JSON.stringify(data));
                // Clear stale market/buy data for the new car
                localStorage.removeItem('lastMarketCheapestPrice');
                localStorage.removeItem('lastBuyStatus');
                console.log('Saved extracted data and cleared stale market data');
            } catch (e) {
                console.warn('Failed to save to localStorage', e);
            }
            // Show the next step button
            if (btnGotoPricing) {
                btnGotoPricing.classList.remove('hidden');
            }
        } else {
            // Hide button if error
            if (btnGotoPricing) {
                btnGotoPricing.classList.add('hidden');
            }
        }

        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    };
});
