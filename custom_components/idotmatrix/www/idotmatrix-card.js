class IDotMatrixCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.layers = [
            { id: "time", type: "text", content: "{{ now().strftime('%H:%M') }}", is_template: true, x: 0, y: 8, color: [0, 255, 0], font_size: 10 }
        ];
    }

    setConfig(config) {
        this.config = config;
        this.render();
    }

    set hass(hass) {
        this._hass = hass;
    }

    render() {
        if (!this.config) return;

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    padding: 16px;
                    background-color: var(--card-background-color);
                    border-radius: var(--ha-card-border-radius, 4px);
                    box-shadow: var(--ha-card-box-shadow, 0 2px 2px 0 rgba(0, 0, 0, 0.14), 0 1px 5px 0 rgba(0, 0, 0, 0.12), 0 3px 1px -2px rgba(0, 0, 0, 0.2));
                }
                .card-header {
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 16px;
                    color: var(--primary-text-color);
                }
                .container {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }
                .canvas-container {
                    background: #000;
                    width: 320px;
                    height: 320px;
                    margin: 0 auto;
                    position: relative;
                    border: 4px solid #333;
                    image-rendering: pixelated;
                }
                canvas {
                     width: 100%;
                     height: 100%;
                }
                .controls {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .layer-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: var(--secondary-background-color);
                    padding: 8px;
                    border-radius: 4px;
                }
                input[type="text"] {
                    flex-grow: 1;
                    padding: 4px;
                }
                input[type="number"] {
                    width: 50px;
                }
                button {
                    cursor: pointer;
                    background: var(--primary-color);
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                .save-btn {
                    margin-top: 16px;
                    width: 100%;
                    padding: 12px;
                    font-size: 16px;
                }
            </style>
            
            <div class="card-header">iDotMatrix Designer</div>
            <div class="container">
                <div class="canvas-container">
                    <canvas id="preview" width="32" height="32"></canvas>
                </div>
                
                <div class="controls" id="layers-list">
                    <!-- Layers rendered here -->
                </div>
                
                <button id="add-text-btn">Add Text Layer</button>
                <button class="save-btn" id="save-btn">Save to Device</button>
            </div>
        `;

        this.renderLayers();
        this.drawCanvas();

        this.shadowRoot.getElementById('add-text-btn').addEventListener('click', () => {
            this.layers.push({
                id: Date.now(),
                type: "text",
                content: "Text",
                x: 0,
                y: 0,
                color: [255, 255, 255],
                font_size: 10
            });
            this.render();
        });

        this.shadowRoot.getElementById('save-btn').addEventListener('click', () => {
            this.saveConfig();
        });
    }

    renderLayers() {
        const list = this.shadowRoot.getElementById('layers-list');
        list.innerHTML = '';

        this.layers.forEach((layer, index) => {
            const div = document.createElement('div');
            div.className = 'layer-item';
            div.innerHTML = `
                <span>${index + 1}.</span>
                <input type="text" value="${layer.content}" data-idx="${index}" class="content-input">
                <input type="number" value="${layer.x}" data-idx="${index}" data-prop="x">
                <input type="number" value="${layer.y}" data-idx="${index}" data-prop="y">
                <input type="color" value="${this.rgbToHex(layer.color)}" data-idx="${index}" class="color-input">
                <button data-idx="${index}" class="del-btn">X</button>
            `;

            // Bind events
            div.querySelector('.content-input').addEventListener('input', (e) => {
                this.layers[index].content = e.target.value;
                this.drawCanvas();
            });
            div.querySelectorAll('input[type="number"]').forEach(inp => {
                inp.addEventListener('input', (e) => {
                    this.layers[index][e.target.dataset.prop] = parseInt(e.target.value);
                    this.drawCanvas();
                });
            });
            div.querySelector('.color-input').addEventListener('input', (e) => {
                this.layers[index].color = this.hexToRgb(e.target.value);
                this.drawCanvas();
            });
            div.querySelector('.del-btn').addEventListener('click', () => {
                this.layers.splice(index, 1);
                this.render();
            });

            list.appendChild(div);
        });
    }

    drawCanvas() {
        const canvas = this.shadowRoot.getElementById('preview');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = "#000000";
        ctx.fillRect(0, 0, 32, 32); // Assume 32x32 for now

        this.layers.forEach(layer => {
            ctx.fillStyle = `rgb(${layer.color[0]}, ${layer.color[1]}, ${layer.color[2]})`;
            if (layer.type === "text") {
                // Approximate generic font
                ctx.font = `${layer.font_size}px overflow`;
                // Note: Canvas text rendering is very different from PIL.
                // We just approximate position/color here.
                ctx.fillText(layer.content, layer.x, layer.y + layer.font_size);
            }
        });
    }

    saveConfig() {
        if (!this._hass) return;
        this._hass.callService('idotmatrix', 'set_face', {
            face: {
                layers: this.layers
            }
        });
        alert("Config sent to device!");
    }

    rgbToHex(rgb) {
        return "#" + rgb.map(x => {
            const hex = x.toString(16);
            return hex.length === 1 ? "0" + hex : hex;
        }).join("");
    }

    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? [
            parseInt(result[1], 16),
            parseInt(result[2], 16),
            parseInt(result[3], 16)
        ] : [255, 255, 255];
    }

    getCardSize() {
        return 8;
    }
}

customElements.define('idotmatrix-card', IDotMatrixCard);

window.customCards = window.customCards || [];
window.customCards.push({
    type: "idotmatrix-card",
    name: "iDotMatrix Card",
    description: "A custom designer card for iDotMatrix",
});
