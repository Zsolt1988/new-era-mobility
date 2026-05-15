class AutoResizingIframe extends HTMLElement {
    connectedCallback() {
        // Die !important Methode zwingt Wix auf der Live-Seite, die volle Breite zu nutzen
        this.setAttribute('style', 'display: block !important; width: 100% !important; max-width: 100% !important; margin: 0 auto !important; padding: 0 !important; box-sizing: border-box !important;');
        this.style.minHeight = '600px';
        this.style.transition = 'height 0.3s ease';

        this.innerHTML = `
            <iframe 
                src="https://zsolt1988.github.io/new-era-mobility/" 
                style="width: 110%; height: 100%; border: none; overflow: hidden; display: block;" 
                scrolling="no">
            </iframe>
        `;

        // 3. Wartet auf Nachrichten von der GitHub-Seite
        window.addEventListener('message', (event) => {
            if (!event.data) return;

            let payload = event.data;
            if (typeof payload === 'string') {
                try { payload = JSON.parse(payload); } catch (e) { return; }
            }

            if (payload.type === 'resize' && payload.height) {
                console.log("Wrapper setzt neue Höhe:", payload.height);
                this.style.height = payload.height + 'px';
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
