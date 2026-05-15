class AutoResizingIframe extends HTMLElement {
    connectedCallback() {
        this.style.setProperty('display', 'block', 'important');
        this.style.setProperty('transition', 'height 0.3s ease', 'important');
        this.style.setProperty('min-height', '600px', 'important'); // Wichtig als Startwert

        // --- DER NEUE, SAUBERE AUSBRUCHS-HACK ---
        // Macht das Element so breit wie das Display, bleibt aber im Wix-Raster verankert!
        this.style.setProperty('width', '100vw', 'important');
        this.style.setProperty('max-width', '100vw', 'important');
        // Zieht das Element mathematisch exakt an den linken Rand des Displays:
        this.style.setProperty('margin-left', 'calc(-50vw + 50%)', 'important');
        // ----------------------------------------

        this.innerHTML = `
            <iframe 
                src="https://zsolt1988.github.io/new-era-mobility/" 
                style="width: 100%; height: 100%; border: none; overflow: hidden; display: block; margin: 0; padding: 0;" 
                scrolling="no">
            </iframe>
        `;

        // Wartet auf Nachrichten von der GitHub-Seite
        window.addEventListener('message', (event) => {
            if (!event.data) return;

            let payload = event.data;
            if (typeof payload === 'string') {
                try { payload = JSON.parse(payload); } catch (e) { return; }
            }

            // Wix-Layout zwingen, sich anzupassen
            if (payload.type === 'resize' && payload.height) {
                console.log("Wrapper setzt neue Höhe:", payload.height);
                this.style.setProperty('height', payload.height + 'px', 'important');
            }

            // Datenbank-Anfragen an Wix Velo weiterleiten
            if (payload.type === 'vehicle_inquiry') {
                this.dispatchEvent(new CustomEvent('inquiry', { detail: payload }));
            }

            // Nach oben scrollen
            if (payload.type === 'scroll_to_top') {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    }
}

customElements.define('wix-wrapper', AutoResizingIframe);
