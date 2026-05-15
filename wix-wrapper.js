class AutoResizingIframe extends HTMLElement {
    connectedCallback() {
        // Erstellt das iFrame, das auf deine GitHub-Seite zeigt
        this.innerHTML = `
            <iframe 
                src="https://zsolt1988.github.io/new-era-mobility/" 
                style="width: 100%; height: 100%; border: none; overflow: hidden;" 
                scrolling="no">
            </iframe>
        `;
        
        // Hört auf die Nachrichten (Höhe & Datenbank-Anfragen) von deiner index.html
        window.addEventListener('message', (event) => {
            if (!event.data) return;

            let payload = event.data;
            if (typeof payload === 'string') {
                try { payload = JSON.parse(payload); } catch (e) { return; }
            }

            // 1. Wix-Layout zwingen, sich anzupassen
            if (payload.type === 'resize') {
                // Ändert die Höhe dieses Elements, wodurch Wix den Streifen verschiebt!
                this.style.height = payload.height + 'px';
                this.style.display = 'block';
            }

            // 2. Datenbank-Anfragen an Wix Velo weiterleiten
            if (payload.type === 'vehicle_inquiry') {
                this.dispatchEvent(new CustomEvent('inquiry', { detail: payload }));
            }
            
            // 3. Nach oben scrollen
            if (payload.type === 'scroll_to_top') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }
}

customElements.define('wix-wrapper', AutoResizingIframe);
