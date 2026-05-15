class AutoResizingIframe extends HTMLElement {
    connectedCallback() {
        // Grund-Styles: Block-Verhalten
        this.style.setProperty('display', 'block', 'important');
        this.style.setProperty('transition', 'height 0.3s ease', 'important');
        this.style.setProperty('min-height', '600px', 'important');
        this.style.setProperty('background-color', '#f8fafc', 'important'); // Gleicht den Hintergrund an

        // --- V9 BREITEN-HACK (FULL VIEWPORT) ---
        // Diese Formel bricht aus jedem Wix-Container aus und nutzt 100% der Displaybreite
        this.style.setProperty('width', '100vw', 'important');
        this.style.setProperty('position', 'relative', 'important');
        this.style.setProperty('margin-left', '50%', 'important');
        this.style.setProperty('transform', 'translateX(-50%)', 'important');
        // ---------------------------------------

        this.innerHTML = `
            <iframe 
                src="https://zsolt1988.github.io/new-era-mobility/?v=1.1" 
                style="width: 100vw; height: 100%; border: none; overflow: hidden; display: block; margin: 0; padding: 0;" 
                scrolling="no">
            </iframe>
        `;

        window.addEventListener('message', (event) => {
            if (!event.data) return;
            let payload = event.data;
            if (typeof payload === 'string') {
                try { payload = JSON.parse(payload); } catch (e) { return; }
            }

            // Deine funktionierende Höhen-Logik
            if (payload.type === 'resize' && payload.height) {
                // Bei V9 setzen wir die Höhe explizit für das Element
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
