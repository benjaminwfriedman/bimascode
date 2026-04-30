/**
 * Main Viewer Controller for BIM as Code Preview.
 *
 * Manages WebSocket connection, coordinates 2D and 3D renderers,
 * and handles UI interactions.
 */

import { Renderer2D } from './renderer2d.js';
import { Renderer3D } from './renderer3d.js';

class Viewer {
    constructor() {
        // DOM elements
        this.viewSelect = document.getElementById('view-select');
        this.statusDot = document.getElementById('status-dot');
        this.statusText = document.getElementById('status-text');
        this.footerStatus = document.getElementById('footer-status');
        this.errorOverlay = document.getElementById('error-overlay');
        this.errorMessage = document.getElementById('error-message');
        this.errorTraceback = document.getElementById('error-traceback');
        this.errorClose = document.getElementById('error-close');
        this.empty2d = document.getElementById('empty-2d');
        this.empty3d = document.getElementById('empty-3d');
        this.info2d = document.getElementById('info-2d');
        this.info3d = document.getElementById('info-3d');
        this.btnFit2d = document.getElementById('btn-fit-2d');
        this.btnFit3d = document.getElementById('btn-fit-3d');
        this.btnDownloadIfc = document.getElementById('btn-download-ifc');
        this.divider = document.getElementById('divider');
        this.pane2d = document.getElementById('pane-2d');
        this.pane3d = document.getElementById('pane-3d');

        // State
        this.currentView = null;
        this.viewData = {};
        this.modelUrl = null;
        this.ws = null;
        this.reconnectTimer = null;

        // Initialize renderers
        this.renderer2d = new Renderer2D(document.getElementById('canvas-2d'));
        this.renderer3d = new Renderer3D(document.getElementById('container-3d'));

        // Set up 3D renderer callbacks
        this.renderer3d.onSelect = (metadata) => {
            if (metadata) {
                this.footerStatus.textContent = `Selected: ${metadata.type} - ${metadata.name || metadata.guid?.slice(0, 8)}`;
            } else {
                this.footerStatus.textContent = 'Ready';
            }
        };

        this.renderer3d.onHover = (metadata) => {
            // Could show hover info in UI
        };

        // Set up event listeners
        this._setupEventListeners();

        // Connect to WebSocket
        this._connect();
    }

    /**
     * Set up UI event listeners.
     */
    _setupEventListeners() {
        // View selection
        this.viewSelect.addEventListener('change', (e) => {
            this._selectView(e.target.value);
        });

        // Fit buttons
        this.btnFit2d.addEventListener('click', () => {
            this.renderer2d.fitToView();
        });

        this.btnFit3d.addEventListener('click', () => {
            this.renderer3d.fitToModel();
        });

        // IFC download
        this.btnDownloadIfc.addEventListener('click', () => {
            this._requestIfcExport();
        });

        // Error overlay close
        this.errorClose.addEventListener('click', () => {
            this._hideError();
        });

        // Split pane resizer
        this._setupDivider();
    }

    /**
     * Set up the split pane divider drag behavior.
     */
    _setupDivider() {
        let isDragging = false;
        let startX = 0;
        let startWidthLeft = 0;

        this.divider.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startWidthLeft = this.pane2d.offsetWidth;
            this.divider.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const dx = e.clientX - startX;
            const containerWidth = this.pane2d.parentElement.offsetWidth;
            const newLeftWidth = Math.max(200, Math.min(containerWidth - 200, startWidthLeft + dx));
            const newRightWidth = containerWidth - newLeftWidth - 4; // 4px divider

            this.pane2d.style.flex = 'none';
            this.pane3d.style.flex = 'none';
            this.pane2d.style.width = newLeftWidth + 'px';
            this.pane3d.style.width = newRightWidth + 'px';

            // Trigger resize on renderers
            this.renderer2d.resize();
            this.renderer3d._onResize();
        });

        document.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                this.divider.classList.remove('dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    /**
     * Connect to the WebSocket server.
     */
    _connect() {
        // Determine WebSocket port (HTTP port - 1)
        const httpPort = parseInt(location.port) || 8766;
        const wsPort = httpPort - 1;
        const wsUrl = `ws://${location.hostname}:${wsPort}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this._setConnected(true);
            clearTimeout(this.reconnectTimer);
        };

        this.ws.onclose = () => {
            this._setConnected(false);
            // Reconnect after 2 seconds
            this.reconnectTimer = setTimeout(() => this._connect(), 2000);
        };

        this.ws.onerror = () => {
            this.statusText.textContent = 'Connection error';
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this._handleMessage(data);
        };
    }

    /**
     * Update connection status UI.
     */
    _setConnected(connected) {
        if (connected) {
            this.statusDot.classList.add('connected');
            this.statusText.textContent = 'Connected';
        } else {
            this.statusDot.classList.remove('connected');
            this.statusText.textContent = 'Disconnected';
        }
    }

    /**
     * Handle incoming WebSocket message.
     */
    _handleMessage(data) {
        if (data.type === 'error') {
            this._showError(data.message, data.traceback);
            this.footerStatus.textContent = 'Error in script';
            return;
        }

        if (data.type === 'update') {
            this._hideError();
            this._updateViews(data.views);

            // Load 3D model if URL provided
            if (data.model_url) {
                this._loadModel(data.model_url);
            }

            // Auto-select first view if none selected
            const viewNames = Object.keys(data.views);
            if (viewNames.length > 0 && !this.currentView) {
                this._selectView(viewNames[0]);
            } else if (this.currentView && this.viewData[this.currentView]) {
                this._renderCurrentView();
            }

            this.footerStatus.textContent = `Updated at ${new Date().toLocaleTimeString()}`;
        }

        if (data.type === 'ifc_ready' && data.ifc_url) {
            // Trigger IFC download
            this._downloadFile(data.ifc_url, 'building.ifc');
        }
    }

    /**
     * Update the view selector with available views.
     */
    _updateViews(views) {
        this.viewData = views;

        // Update selector
        this.viewSelect.innerHTML = '<option value="">-- Select View --</option>';
        for (const name of Object.keys(views)) {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            if (name === this.currentView) {
                option.selected = true;
            }
            this.viewSelect.appendChild(option);
        }
    }

    /**
     * Select and render a view.
     */
    _selectView(name) {
        this.currentView = name;

        if (name && this.viewData[name]) {
            this._renderCurrentView();
            this.empty2d.classList.add('hidden');
        } else {
            this.empty2d.classList.remove('hidden');
        }
    }

    /**
     * Render the currently selected view.
     */
    _renderCurrentView() {
        if (!this.currentView || !this.viewData[this.currentView]) return;

        const data = this.viewData[this.currentView];
        this.renderer2d.render(data);
        this.info2d.textContent = `${data.total_geometry_count || 0} items`;
    }

    /**
     * Load 3D model from URL.
     */
    async _loadModel(url) {
        if (url === this.modelUrl) return;

        this.modelUrl = url;
        this.empty3d.classList.remove('hidden');
        this.empty3d.querySelector('span:last-child').textContent = 'Loading model...';

        try {
            await this.renderer3d.load(url);
            this.empty3d.classList.add('hidden');
            this.info3d.textContent = `${this.renderer3d.getMeshCount()} meshes`;
            this.btnDownloadIfc.disabled = false;
        } catch (error) {
            this.empty3d.querySelector('span:last-child').textContent = 'Failed to load model';
            console.error('Failed to load 3D model:', error);
        }
    }

    /**
     * Request IFC export from server.
     */
    _requestIfcExport() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'export_ifc' }));
            this.footerStatus.textContent = 'Exporting IFC...';
        }
    }

    /**
     * Download a file from URL.
     */
    _downloadFile(url, filename) {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        this.footerStatus.textContent = 'IFC downloaded';
    }

    /**
     * Show error overlay.
     */
    _showError(message, traceback) {
        this.errorMessage.textContent = message;
        this.errorTraceback.textContent = traceback || '';
        this.errorOverlay.classList.add('visible');
    }

    /**
     * Hide error overlay.
     */
    _hideError() {
        this.errorOverlay.classList.remove('visible');
    }
}

// Initialize viewer when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.viewer = new Viewer();
});
