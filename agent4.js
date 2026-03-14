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

    // Handle Generation
    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) {
        generateBtn.addEventListener('click', () => {
            console.log("Launching Homepage Generation...");
            // Reuse the existing generator logic via the proxy
            window.location.href = 'homepage_preview.html';
        });
    }
});
