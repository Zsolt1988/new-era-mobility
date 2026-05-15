class AutoResizingIframe extends HTMLElement {
    connectedCallback() {
        // Grund-Styles: Block-Verhalten
        this.style.setProperty('display', 'block', 'important');
        this.style.setProperty('transition', 'height 0.3s ease', 'important');
        this.style.setProperty('min-height', '600px', 'important');

        // --- V8 BREITEN-FIX ---
        // Wir setzen die Breite auf 100% der Wix-Box. 
        // Die Zentrierung korrigieren wir im Wix-Editor (Schritt 3).
        this.style.setProperty('width', '100%', 'important');
        this.style.setProperty('max-width', '100vw', 'important');
        this.style.setProperty('margin', '0', 'important');
        this.style.setProperty('left', '0', 'important');
        // -----------------------

        this.innerHTML = `
            <iframe 
                src="https://zsolt1988.github.io/new-era-mobility/" 
                style="width: 100%; height: 100%; border: none; overflow: hidden; display: block; margin: 0; padding: 0;" 
                scrolling="no">
            </iframe>
        `;

        window.addEventListener('message', (event) => {
            if (!event.data) return;
            let payload = event.data;
            if (typeof payload === 'string') {
                try { payload = JSON.parse(payload); } catch (e) { return; }
            }

            // Die bewährte V6 Höhen-Logik
            if (payload.type === 'resize' && payload.height) {
                this.style.setProperty('height', payload.height + 'px', 'important');
            }

            if (payload.type === 'vehicle_inquiry') {
                this.dispatchEvent(new CustomEvent('inquiry', { detail: payload }));
            }

            if (payload.type === 'scroll_to_top') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }
}
customElements.define('wix-wrapper', AutoResizingIframe);
