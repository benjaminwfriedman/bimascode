/**
 * 2D Canvas Renderer for BIM as Code ViewResult data.
 *
 * Renders lines, arcs, polylines, hatches, dimensions, and text
 * from ViewResult JSON to a 2D canvas.
 */

export class Renderer2D {
    /**
     * Create a new 2D renderer.
     * @param {HTMLCanvasElement} canvas - The canvas element to render to
     */
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // View transform state
        this.scale = 1;
        this.offsetX = 0;
        this.offsetY = 0;

        // Pan/zoom state
        this.isPanning = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;

        // Current view data
        this.viewData = null;
        this.bounds = null;

        // Setup event listeners
        this._setupEventListeners();
    }

    /**
     * Set up canvas event listeners for pan and zoom.
     */
    _setupEventListeners() {
        // Pan: click and drag
        this.canvas.addEventListener('mousedown', (e) => {
            if (e.button === 0) { // Left mouse button
                this.isPanning = true;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this.canvas.style.cursor = 'grabbing';
            }
        });

        this.canvas.addEventListener('mousemove', (e) => {
            if (this.isPanning) {
                const dx = e.clientX - this.lastMouseX;
                const dy = e.clientY - this.lastMouseY;
                this.offsetX += dx;
                this.offsetY += dy;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this._render();
            }
        });

        this.canvas.addEventListener('mouseup', () => {
            this.isPanning = false;
            this.canvas.style.cursor = 'default';
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.isPanning = false;
            this.canvas.style.cursor = 'default';
        });

        // Zoom: scroll wheel
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();

            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            // Calculate zoom
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = this.scale * zoomFactor;

            // Limit zoom range
            if (newScale < 0.01 || newScale > 100) return;

            // Adjust offset to zoom toward mouse position
            this.offsetX = mouseX - (mouseX - this.offsetX) * zoomFactor;
            this.offsetY = mouseY - (mouseY - this.offsetY) * zoomFactor;
            this.scale = newScale;

            this._render();
        });

        // Fit to view: double-click
        this.canvas.addEventListener('dblclick', () => {
            this.fitToView();
        });

        // Handle resize
        const resizeObserver = new ResizeObserver(() => {
            this.resize();
        });
        resizeObserver.observe(this.canvas.parentElement);
    }

    /**
     * Resize the canvas to match its container.
     */
    resize() {
        const container = this.canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;

        this.canvas.width = container.clientWidth * dpr;
        this.canvas.height = container.clientHeight * dpr;
        this.canvas.style.width = container.clientWidth + 'px';
        this.canvas.style.height = container.clientHeight + 'px';

        this.ctx.scale(dpr, dpr);

        if (this.viewData) {
            this._render();
        }
    }

    /**
     * Render a ViewResult to the canvas.
     * @param {Object} viewData - ViewResult JSON data
     */
    render(viewData) {
        this.viewData = viewData;
        this.bounds = this._calculateBounds(viewData);
        this.fitToView();
    }

    /**
     * Fit the view to show all geometry.
     */
    fitToView() {
        if (!this.bounds) return;

        const container = this.canvas.parentElement;
        const canvasWidth = container.clientWidth;
        const canvasHeight = container.clientHeight;

        const padding = 40;
        const viewWidth = this.bounds.maxX - this.bounds.minX;
        const viewHeight = this.bounds.maxY - this.bounds.minY;

        if (viewWidth <= 0 || viewHeight <= 0) return;

        const scaleX = (canvasWidth - padding * 2) / viewWidth;
        const scaleY = (canvasHeight - padding * 2) / viewHeight;
        this.scale = Math.min(scaleX, scaleY);

        // Center the view
        const scaledWidth = viewWidth * this.scale;
        const scaledHeight = viewHeight * this.scale;

        this.offsetX = (canvasWidth - scaledWidth) / 2 - this.bounds.minX * this.scale;
        this.offsetY = (canvasHeight + scaledHeight) / 2 + this.bounds.minY * this.scale;

        this._render();
    }

    /**
     * Calculate bounds of all geometry.
     * @param {Object} data - ViewResult data
     * @returns {Object|null} Bounds object or null if empty
     */
    _calculateBounds(data) {
        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;

        const updateBounds = (x, y) => {
            minX = Math.min(minX, x);
            minY = Math.min(minY, y);
            maxX = Math.max(maxX, x);
            maxY = Math.max(maxY, y);
        };

        // Lines
        for (const line of data.lines || []) {
            updateBounds(line.start.x, line.start.y);
            updateBounds(line.end.x, line.end.y);
        }

        // Polylines
        for (const polyline of data.polylines || []) {
            for (const pt of polyline.points) {
                updateBounds(pt.x, pt.y);
            }
        }

        // Arcs
        for (const arc of data.arcs || []) {
            const r = arc.radius;
            updateBounds(arc.center.x - r, arc.center.y - r);
            updateBounds(arc.center.x + r, arc.center.y + r);
        }

        // Hatches
        for (const hatch of data.hatches || []) {
            for (const pt of hatch.boundary) {
                updateBounds(pt.x, pt.y);
            }
        }

        // Dimensions
        for (const dim of data.dimensions || []) {
            updateBounds(dim.start.x, dim.start.y);
            updateBounds(dim.end.x, dim.end.y);
        }

        // Tags
        for (const tag of [...(data.door_tags || []), ...(data.window_tags || []), ...(data.room_tags || [])]) {
            if (tag.insertion_point) {
                updateBounds(tag.insertion_point.x, tag.insertion_point.y);
            }
        }

        if (minX === Infinity) return null;

        // Add margin
        const margin = Math.max(maxX - minX, maxY - minY) * 0.05;
        return {
            minX: minX - margin,
            minY: minY - margin,
            maxX: maxX + margin,
            maxY: maxY + margin
        };
    }

    /**
     * Internal render method.
     */
    _render() {
        if (!this.viewData) return;

        const container = this.canvas.parentElement;
        const ctx = this.ctx;

        // Clear canvas
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, container.clientWidth, container.clientHeight);

        // Set up transform (flip Y for CAD coordinates)
        ctx.save();
        ctx.translate(this.offsetX, this.offsetY);
        ctx.scale(this.scale, -this.scale);

        // Draw hatches first (fill areas)
        ctx.globalAlpha = 0.3;
        for (const hatch of this.viewData.hatches || []) {
            this._drawHatch(ctx, hatch);
        }
        ctx.globalAlpha = 1;

        // Draw lines
        for (const line of this.viewData.lines || []) {
            this._drawLine(ctx, line);
        }

        // Draw polylines
        for (const polyline of this.viewData.polylines || []) {
            this._drawPolyline(ctx, polyline);
        }

        // Draw arcs
        for (const arc of this.viewData.arcs || []) {
            this._drawArc(ctx, arc);
        }

        // Draw dimensions
        for (const dim of this.viewData.dimensions || []) {
            this._drawDimension(ctx, dim);
        }

        // Draw chain dimensions
        for (const chain of this.viewData.chain_dimensions || []) {
            this._drawChainDimension(ctx, chain);
        }

        ctx.restore();

        // Draw tags in screen space (after restore)
        ctx.save();
        for (const tag of this.viewData.door_tags || []) {
            this._drawDoorTag(ctx, tag);
        }
        for (const tag of this.viewData.window_tags || []) {
            this._drawWindowTag(ctx, tag);
        }
        for (const tag of this.viewData.room_tags || []) {
            this._drawRoomTag(ctx, tag);
        }
        ctx.restore();

        // Draw text notes
        ctx.save();
        for (const text of this.viewData.text_notes || []) {
            this._drawTextNote(ctx, text);
        }
        ctx.restore();
    }

    /**
     * Get line width based on style.
     */
    _getLineWidth(style) {
        if (!style || !style.weight) return 1;
        const widthMm = style.weight.width_mm || 0.25;
        return Math.max(0.5, widthMm * 2) / this.scale;
    }

    /**
     * Get line color based on style.
     */
    _getLineColor(style) {
        if (style && style.color) {
            return `rgb(${style.color[0]}, ${style.color[1]}, ${style.color[2]})`;
        }
        if (style && style.is_cut) {
            return '#e0e0e0';
        }
        return '#808090';
    }

    /**
     * Set line dash pattern from style.
     */
    _setLineDash(ctx, style) {
        if (!style || !style.type || style.type.name === 'CONTINUOUS') {
            ctx.setLineDash([]);
            return;
        }

        const pattern = style.type.pattern || [];
        if (pattern.length === 0) {
            ctx.setLineDash([]);
            return;
        }

        // Scale pattern to current view scale
        const scaledPattern = pattern.map(v => Math.max(1, v / this.scale));
        ctx.setLineDash(scaledPattern);
    }

    /**
     * Draw a line segment.
     */
    _drawLine(ctx, line) {
        ctx.beginPath();
        ctx.moveTo(line.start.x, line.start.y);
        ctx.lineTo(line.end.x, line.end.y);
        ctx.strokeStyle = this._getLineColor(line.style);
        ctx.lineWidth = this._getLineWidth(line.style);
        this._setLineDash(ctx, line.style);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    /**
     * Draw a polyline.
     */
    _drawPolyline(ctx, polyline) {
        if (polyline.points.length < 2) return;

        ctx.beginPath();
        ctx.moveTo(polyline.points[0].x, polyline.points[0].y);
        for (let i = 1; i < polyline.points.length; i++) {
            ctx.lineTo(polyline.points[i].x, polyline.points[i].y);
        }
        if (polyline.closed) {
            ctx.closePath();
        }
        ctx.strokeStyle = this._getLineColor(polyline.style);
        ctx.lineWidth = this._getLineWidth(polyline.style);
        this._setLineDash(ctx, polyline.style);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    /**
     * Draw an arc.
     */
    _drawArc(ctx, arc) {
        ctx.beginPath();
        // Note: Canvas arc goes counterclockwise for positive sweep
        ctx.arc(arc.center.x, arc.center.y, arc.radius, arc.start_angle, arc.end_angle);
        ctx.strokeStyle = this._getLineColor(arc.style);
        ctx.lineWidth = this._getLineWidth(arc.style);
        this._setLineDash(ctx, arc.style);
        ctx.stroke();
        ctx.setLineDash([]);
    }

    /**
     * Draw a hatch (filled region).
     */
    _drawHatch(ctx, hatch) {
        if (hatch.boundary.length < 3) return;

        ctx.beginPath();
        ctx.moveTo(hatch.boundary[0].x, hatch.boundary[0].y);
        for (let i = 1; i < hatch.boundary.length; i++) {
            ctx.lineTo(hatch.boundary[i].x, hatch.boundary[i].y);
        }
        ctx.closePath();

        if (hatch.color) {
            ctx.fillStyle = `rgb(${hatch.color[0]}, ${hatch.color[1]}, ${hatch.color[2]})`;
        } else {
            ctx.fillStyle = '#3a3a5a';
        }
        ctx.fill();
    }

    /**
     * Draw a linear dimension.
     */
    _drawDimension(ctx, dim) {
        // Calculate dimension line position
        const dx = dim.end.x - dim.start.x;
        const dy = dim.end.y - dim.start.y;
        const angle = Math.atan2(dy, dx);
        const perpAngle = angle + Math.PI / 2;

        const offsetX = dim.offset * Math.cos(perpAngle);
        const offsetY = dim.offset * Math.sin(perpAngle);

        const dimStart = { x: dim.start.x + offsetX, y: dim.start.y + offsetY };
        const dimEnd = { x: dim.end.x + offsetX, y: dim.end.y + offsetY };

        // Draw extension lines
        ctx.strokeStyle = '#6c63ff';
        ctx.lineWidth = 0.5 / this.scale;
        ctx.setLineDash([]);

        ctx.beginPath();
        ctx.moveTo(dim.start.x, dim.start.y);
        ctx.lineTo(dimStart.x, dimStart.y);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(dim.end.x, dim.end.y);
        ctx.lineTo(dimEnd.x, dimEnd.y);
        ctx.stroke();

        // Draw dimension line
        ctx.beginPath();
        ctx.moveTo(dimStart.x, dimStart.y);
        ctx.lineTo(dimEnd.x, dimEnd.y);
        ctx.stroke();

        // Draw arrow heads
        const arrowSize = 100 / this.scale;
        this._drawArrow(ctx, dimStart.x, dimStart.y, angle);
        this._drawArrow(ctx, dimEnd.x, dimEnd.y, angle + Math.PI);

        // Draw dimension text
        const distance = Math.sqrt(dx * dx + dy * dy);
        const text = dim.text === '<>' ? Math.round(distance * (dim.dimlfac || 1)).toString() : dim.text;

        const midX = (dimStart.x + dimEnd.x) / 2;
        const midY = (dimStart.y + dimEnd.y) / 2;

        // Convert to screen coordinates for text
        const screenX = midX * this.scale + this.offsetX;
        const screenY = -midY * this.scale + this.offsetY;

        ctx.save();
        ctx.resetTransform();
        ctx.fillStyle = '#6c63ff';
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, screenX, screenY - 8);
        ctx.restore();
    }

    /**
     * Draw a chain dimension.
     */
    _drawChainDimension(ctx, chain) {
        // Chain dimensions are just multiple linear dimensions
        // The to_dict should provide the individual segments
        // For now, draw using the points directly
        const points = chain.points || [];
        if (points.length < 2) return;

        for (let i = 0; i < points.length - 1; i++) {
            const segment = {
                start: points[i],
                end: points[i + 1],
                offset: chain.offset,
                text: chain.text,
                dimlfac: chain.dimlfac || 1
            };
            this._drawDimension(ctx, segment);
        }
    }

    /**
     * Draw an arrow head.
     */
    _drawArrow(ctx, x, y, angle) {
        const size = 80 / this.scale;
        const halfAngle = Math.PI / 8;

        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(
            x - size * Math.cos(angle - halfAngle),
            y - size * Math.sin(angle - halfAngle)
        );
        ctx.moveTo(x, y);
        ctx.lineTo(
            x - size * Math.cos(angle + halfAngle),
            y - size * Math.sin(angle + halfAngle)
        );
        ctx.stroke();
    }

    /**
     * Draw a door tag.
     */
    _drawDoorTag(ctx, tag) {
        const pos = this._toScreen(tag.insertion_point);
        const size = (tag.style?.size || 300) * this.scale;

        // Draw hexagon
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI / 3) - Math.PI / 6;
            const x = pos.x + (size / 2) * Math.cos(angle);
            const y = pos.y + (size / 2) * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();
        ctx.strokeStyle = '#6c63ff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Draw text (scales with model like DXF)
        ctx.fillStyle = '#e0e0e0';
        ctx.font = `${size * 0.4}px -apple-system, BlinkMacSystemFont, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(tag.text || '', pos.x, pos.y);
    }

    /**
     * Draw a window tag.
     */
    _drawWindowTag(ctx, tag) {
        const pos = this._toScreen(tag.insertion_point);
        const radius = ((tag.style?.size || 300) * this.scale) / 2;

        // Draw circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = '#1a1a2e';
        ctx.fill();
        ctx.strokeStyle = '#4ecdc4';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Draw text (scales with model like DXF)
        ctx.fillStyle = '#e0e0e0';
        ctx.font = `${radius * 0.8}px -apple-system, BlinkMacSystemFont, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(tag.text || '', pos.x, pos.y);
    }

    /**
     * Draw a room tag.
     */
    _drawRoomTag(ctx, tag) {
        const pos = this._toScreen(tag.insertion_point);
        const height = (tag.style?.size || 400) * this.scale;
        const width = (tag.calculated_width || tag.style?.size || 400) * this.scale;

        // Draw rectangle
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(pos.x - width / 2, pos.y - height / 2, width, height);
        ctx.strokeStyle = '#f9ca24';
        ctx.lineWidth = 1;
        ctx.strokeRect(pos.x - width / 2, pos.y - height / 2, width, height);

        // Draw name and number (scales with model like DXF)
        ctx.fillStyle = '#e0e0e0';
        const fontSize = height * 0.25;
        ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
        ctx.textAlign = 'center';

        if (tag.name_text && tag.number_text) {
            ctx.fillText(tag.name_text, pos.x, pos.y - fontSize * 0.3);
            ctx.fillText(tag.number_text, pos.x, pos.y + fontSize * 0.7);
        } else {
            ctx.textBaseline = 'middle';
            ctx.fillText(tag.text || '', pos.x, pos.y);
        }
    }

    /**
     * Draw a text note.
     */
    _drawTextNote(ctx, text) {
        const pos = this._toScreen(text.position);

        // Text scales with model like DXF
        ctx.fillStyle = '#e0e0e0';
        const fontSize = (text.height || 100) * this.scale;
        ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;

        // Handle alignment
        switch (text.alignment) {
            case 'TOP_LEFT':
            case 'MIDDLE_LEFT':
            case 'BOTTOM_LEFT':
                ctx.textAlign = 'left';
                break;
            case 'TOP_CENTER':
            case 'MIDDLE_CENTER':
            case 'BOTTOM_CENTER':
                ctx.textAlign = 'center';
                break;
            case 'TOP_RIGHT':
            case 'MIDDLE_RIGHT':
            case 'BOTTOM_RIGHT':
                ctx.textAlign = 'right';
                break;
            default:
                ctx.textAlign = 'left';
        }

        ctx.textBaseline = 'middle';

        // Handle multiline text
        const lines = (text.content || '').split('\n');
        const lineHeight = fontSize * 1.2;
        const startY = pos.y - ((lines.length - 1) * lineHeight) / 2;

        for (let i = 0; i < lines.length; i++) {
            ctx.fillText(lines[i], pos.x, startY + i * lineHeight);
        }
    }

    /**
     * Convert model coordinates to screen coordinates.
     */
    _toScreen(point) {
        return {
            x: point.x * this.scale + this.offsetX,
            y: -point.y * this.scale + this.offsetY
        };
    }

    /**
     * Get geometry count from current view data.
     */
    getGeometryCount() {
        if (!this.viewData) return 0;
        return this.viewData.total_geometry_count || 0;
    }
}
