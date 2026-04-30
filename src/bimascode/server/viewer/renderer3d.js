/**
 * 3D Three.js Renderer for BIM as Code glTF models.
 *
 * Loads and displays glTF/GLB models with orbit controls,
 * element hover highlighting, selection, and a ViewCube.
 *
 * Coordinate System:
 * - BIM as Code uses Z-up (X=East, Y=North, Z=Up)
 * - Three.js uses Y-up by default
 * - We rotate the model to match Three.js convention
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export class Renderer3D {
    /**
     * Create a new 3D renderer.
     * @param {HTMLElement} container - The container element to render into
     */
    constructor(container) {
        this.container = container;

        // Three.js objects
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.model = null;
        this.modelContainer = null; // Container for Z-up to Y-up rotation

        // Interaction state
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.hoveredObject = null;
        this.selectedObject = null;

        // ViewCube
        this.viewCube = null;
        this.viewCubeCamera = null;
        this.viewCubeScene = null;
        this.viewCubeSize = 80;

        // Callbacks
        this.onSelect = null;
        this.onHover = null;

        // Initialize
        this._init();
        this._createViewCube();
        this._setupEventListeners();
        this._animate();
    }

    /**
     * Initialize Three.js scene, camera, renderer, and controls.
     */
    _init() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a1a);

        // Model container for loaded models
        // BIM uses Z-up coordinates, Three.js uses Y-up
        // Rotate the container to transform Z-up to Y-up
        this.modelContainer = new THREE.Group();
        this.modelContainer.rotation.x = -Math.PI / 2;
        this.scene.add(this.modelContainer);

        // Camera
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100000);
        this.camera.position.set(10000, 10000, 10000);
        this.camera.up.set(0, 1, 0); // Y is up in Three.js

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.autoClear = false; // For ViewCube overlay
        this.container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.1;
        this.controls.screenSpacePanning = true;
        this.controls.minDistance = 100;
        this.controls.maxDistance = 100000;

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10000, 20000, 10000);
        this.scene.add(directionalLight);

        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.3);
        directionalLight2.position.set(-10000, 10000, -10000);
        this.scene.add(directionalLight2);

        // Add grid on XZ plane (ground plane in Y-up)
        this._addGrid();

        // Loader
        this.loader = new GLTFLoader();
    }

    /**
     * Add a grid helper to the scene.
     */
    _addGrid() {
        const gridHelper = new THREE.GridHelper(20000, 20, 0x2a2a4a, 0x1a1a2e);
        // GridHelper is already on XZ plane (Y-up), no rotation needed
        this.scene.add(gridHelper);
        this.gridHelper = gridHelper;
    }

    /**
     * Create the ViewCube (like Revit/AutoCAD).
     */
    _createViewCube() {
        // ViewCube scene
        this.viewCubeScene = new THREE.Scene();

        // ViewCube camera (orthographic for consistent size)
        this.viewCubeCamera = new THREE.OrthographicCamera(-1.5, 1.5, 1.5, -1.5, 0.1, 10);
        this.viewCubeCamera.position.set(0, 0, 3);

        // Create the cube with face labels
        const cubeSize = 1;
        const geometry = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize);

        // Create materials for each face with labels
        // Order: +X, -X, +Y, -Y, +Z, -Z (Three.js box face order)
        // In BIM coordinates (after rotation): +X=East, -X=West, +Y=Up, -Y=Down, +Z=South, -Z=North
        const faceLabels = ['EAST', 'WEST', 'TOP', 'BOTTOM', 'SOUTH', 'NORTH'];
        const faceColors = [0x3a3a5a, 0x3a3a5a, 0x4a4a6a, 0x2a2a4a, 0x3a3a5a, 0x3a3a5a];

        const materials = faceLabels.map((label, i) => {
            const canvas = document.createElement('canvas');
            canvas.width = 128;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');

            // Background
            ctx.fillStyle = `#${faceColors[i].toString(16).padStart(6, '0')}`;
            ctx.fillRect(0, 0, 128, 128);

            // Border
            ctx.strokeStyle = '#6c63ff';
            ctx.lineWidth = 3;
            ctx.strokeRect(2, 2, 124, 124);

            // Text
            ctx.fillStyle = '#e0e0e0';
            ctx.font = 'bold 20px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(label, 64, 64);

            const texture = new THREE.CanvasTexture(canvas);
            return new THREE.MeshBasicMaterial({ map: texture });
        });

        this.viewCube = new THREE.Mesh(geometry, materials);
        this.viewCubeScene.add(this.viewCube);

        // Add edge lines for better visibility
        const edges = new THREE.EdgesGeometry(geometry);
        const line = new THREE.LineSegments(
            edges,
            new THREE.LineBasicMaterial({ color: 0x6c63ff })
        );
        this.viewCube.add(line);

        // Add axis indicators
        this._addViewCubeAxes();
    }

    /**
     * Add axis indicators to the ViewCube.
     */
    _addViewCubeAxes() {
        const axisLength = 0.8;
        const axisOffset = 0.7;

        // X axis (East) - Red
        const xGeom = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(axisOffset, -axisOffset, -axisOffset),
            new THREE.Vector3(axisOffset + axisLength, -axisOffset, -axisOffset)
        ]);
        const xLine = new THREE.Line(xGeom, new THREE.LineBasicMaterial({ color: 0xff4444 }));
        this.viewCubeScene.add(xLine);

        // Y axis (North in BIM, but Z in Three.js after rotation) - Green
        const yGeom = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(axisOffset, -axisOffset, -axisOffset),
            new THREE.Vector3(axisOffset, -axisOffset, -axisOffset - axisLength)
        ]);
        const yLine = new THREE.Line(yGeom, new THREE.LineBasicMaterial({ color: 0x44ff44 }));
        this.viewCubeScene.add(yLine);

        // Z axis (Up in BIM, Y in Three.js) - Blue
        const zGeom = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(axisOffset, -axisOffset, -axisOffset),
            new THREE.Vector3(axisOffset, -axisOffset + axisLength, -axisOffset)
        ]);
        const zLine = new THREE.Line(zGeom, new THREE.LineBasicMaterial({ color: 0x4444ff }));
        this.viewCubeScene.add(zLine);
    }

    /**
     * Set up event listeners for resize and interaction.
     */
    _setupEventListeners() {
        // Resize
        const resizeObserver = new ResizeObserver(() => {
            this._onResize();
        });
        resizeObserver.observe(this.container);

        // Mouse interaction for hover/selection
        this.renderer.domElement.addEventListener('mousemove', (e) => {
            this._onMouseMove(e);
        });

        this.renderer.domElement.addEventListener('click', (e) => {
            this._onClick(e);
        });

        // Double-click to fit
        this.renderer.domElement.addEventListener('dblclick', () => {
            this.fitToModel();
        });
    }

    /**
     * Handle container resize.
     */
    _onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    /**
     * Handle mouse move for hover effects.
     */
    _onMouseMove(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);

        if (this.model) {
            const meshes = [];
            this.model.traverse((child) => {
                if (child.isMesh) {
                    meshes.push(child);
                }
            });

            const intersects = this.raycaster.intersectObjects(meshes);

            // Reset previous hover
            if (this.hoveredObject && this.hoveredObject !== this.selectedObject) {
                this._resetHighlight(this.hoveredObject);
            }

            if (intersects.length > 0) {
                const object = intersects[0].object;
                if (object !== this.hoveredObject) {
                    this.hoveredObject = object;
                    if (object !== this.selectedObject) {
                        this._setHoverHighlight(object);
                    }

                    // Callback with metadata
                    if (this.onHover) {
                        const metadata = this._getObjectMetadata(object);
                        this.onHover(metadata);
                    }
                }
                this.renderer.domElement.style.cursor = 'pointer';
            } else {
                this.hoveredObject = null;
                this.renderer.domElement.style.cursor = 'default';
                if (this.onHover) {
                    this.onHover(null);
                }
            }
        }
    }

    /**
     * Handle mouse click for selection.
     */
    _onClick(event) {
        // Check if clicking on ViewCube
        const rect = this.renderer.domElement.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // ViewCube is in top-right corner
        const cubeX = rect.width - this.viewCubeSize - 10;
        const cubeY = 10;

        if (x >= cubeX && x <= cubeX + this.viewCubeSize &&
            y >= cubeY && y <= cubeY + this.viewCubeSize) {
            this._onViewCubeClick(x - cubeX, y - cubeY);
            return;
        }

        if (!this.model) return;

        this.raycaster.setFromCamera(this.mouse, this.camera);

        const meshes = [];
        this.model.traverse((child) => {
            if (child.isMesh) {
                meshes.push(child);
            }
        });

        const intersects = this.raycaster.intersectObjects(meshes);

        // Reset previous selection
        if (this.selectedObject) {
            this._resetHighlight(this.selectedObject);
        }

        if (intersects.length > 0) {
            const object = intersects[0].object;
            this.selectedObject = object;
            this._setSelectHighlight(object);

            // Callback with metadata
            if (this.onSelect) {
                const metadata = this._getObjectMetadata(object);
                this.onSelect(metadata);
            }
        } else {
            this.selectedObject = null;
            if (this.onSelect) {
                this.onSelect(null);
            }
        }
    }

    /**
     * Handle click on ViewCube to change view.
     */
    _onViewCubeClick(localX, localY) {
        // Convert click position to normalized coordinates (-1 to 1)
        const nx = (localX / this.viewCubeSize) * 2 - 1;
        const ny = -((localY / this.viewCubeSize) * 2 - 1);

        // Raycast against ViewCube
        const mouse = new THREE.Vector2(nx, ny);
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, this.viewCubeCamera);

        const intersects = raycaster.intersectObject(this.viewCube);
        if (intersects.length > 0) {
            const faceIndex = Math.floor(intersects[0].faceIndex / 2);
            this._setViewFromFace(faceIndex);
        }
    }

    /**
     * Set camera view based on ViewCube face.
     */
    _setViewFromFace(faceIndex) {
        if (!this.model) return;

        const box = new THREE.Box3().setFromObject(this.model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;

        // Camera positions for each face
        // Face indices: 0=+X(East), 1=-X(West), 2=+Y(Top), 3=-Y(Bottom), 4=+Z(South), 5=-Z(North)
        const positions = [
            new THREE.Vector3(distance, 0, 0),  // East
            new THREE.Vector3(-distance, 0, 0), // West
            new THREE.Vector3(0, distance, 0),  // Top
            new THREE.Vector3(0, -distance, 0), // Bottom
            new THREE.Vector3(0, 0, distance),  // South
            new THREE.Vector3(0, 0, -distance)  // North
        ];

        const targetPos = center.clone().add(positions[faceIndex]);

        // Animate camera to new position
        this._animateCameraTo(targetPos, center);
    }

    /**
     * Animate camera to a new position.
     */
    _animateCameraTo(targetPosition, targetLookAt) {
        const startPos = this.camera.position.clone();
        const startTarget = this.controls.target.clone();
        const duration = 500;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const t = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - t, 3); // Ease out cubic

            this.camera.position.lerpVectors(startPos, targetPosition, eased);
            this.controls.target.lerpVectors(startTarget, targetLookAt, eased);
            this.controls.update();

            if (t < 1) {
                requestAnimationFrame(animate);
            }
        };

        animate();
    }

    /**
     * Get metadata from a mesh object.
     */
    _getObjectMetadata(object) {
        // Look for userData which contains glTF extras
        const userData = object.userData || {};

        // Try to get from parent group
        let parent = object.parent;
        while (parent && !parent.userData?.guid) {
            parent = parent.parent;
        }

        const parentData = parent?.userData || {};

        return {
            name: object.name || parentData.name || 'Unknown',
            guid: userData.guid || parentData.guid || '',
            type: userData.type || parentData.type || '',
            level: userData.level || parentData.level || '',
            ...userData
        };
    }

    /**
     * Set hover highlight on an object.
     */
    _setHoverHighlight(object) {
        if (!object.material) return;

        // Store original material
        if (!object.userData.originalMaterial) {
            object.userData.originalMaterial = object.material.clone();
        }

        // Create hover material
        object.material = object.material.clone();
        object.material.emissive = new THREE.Color(0x4444ff);
        object.material.emissiveIntensity = 0.2;
    }

    /**
     * Set selection highlight on an object.
     */
    _setSelectHighlight(object) {
        if (!object.material) return;

        // Store original material
        if (!object.userData.originalMaterial) {
            object.userData.originalMaterial = object.material.clone();
        }

        // Create selection material
        object.material = object.material.clone();
        object.material.emissive = new THREE.Color(0x6c63ff);
        object.material.emissiveIntensity = 0.4;
    }

    /**
     * Reset highlight on an object.
     */
    _resetHighlight(object) {
        if (object.userData.originalMaterial) {
            object.material = object.userData.originalMaterial;
            delete object.userData.originalMaterial;
        }
    }

    /**
     * Animation loop.
     */
    _animate() {
        requestAnimationFrame(() => this._animate());
        this.controls.update();

        // Update ViewCube rotation to match camera
        if (this.viewCube) {
            // Get camera direction relative to target
            const cameraDir = new THREE.Vector3();
            this.camera.getWorldDirection(cameraDir);

            // ViewCube should rotate opposite to camera
            this.viewCube.quaternion.copy(this.camera.quaternion).invert();
        }

        // Clear and render main scene
        this.renderer.clear();
        this.renderer.render(this.scene, this.camera);

        // Render ViewCube overlay in top-right corner
        if (this.viewCubeScene) {
            const width = this.container.clientWidth;
            const height = this.container.clientHeight;

            this.renderer.setViewport(
                width - this.viewCubeSize - 10,
                height - this.viewCubeSize - 10,
                this.viewCubeSize,
                this.viewCubeSize
            );
            this.renderer.render(this.viewCubeScene, this.viewCubeCamera);

            // Reset viewport
            this.renderer.setViewport(0, 0, width, height);
        }
    }

    /**
     * Load a glTF/GLB model from a URL.
     * @param {string} url - URL to the glTF/GLB file
     * @returns {Promise} Resolves when loaded
     */
    load(url) {
        return new Promise((resolve, reject) => {
            // Remove existing model
            if (this.model) {
                this.modelContainer.remove(this.model);
                this.model = null;
            }

            this.loader.load(
                url,
                (gltf) => {
                    this.model = gltf.scene;

                    // Convert materials for better rendering
                    this.model.traverse((child) => {
                        if (child.isMesh) {
                            // Ensure materials work with lighting
                            if (child.material) {
                                child.material.metalness = 0.1;
                                child.material.roughness = 0.8;
                            }
                        }
                    });

                    // Add to model container (which handles Z-up to Y-up rotation)
                    this.modelContainer.add(this.model);
                    this.fitToModel();
                    resolve(this.model);
                },
                (progress) => {
                    // Progress callback
                },
                (error) => {
                    console.error('Error loading glTF:', error);
                    reject(error);
                }
            );
        });
    }

    /**
     * Fit the camera to show the entire model.
     */
    fitToModel() {
        if (!this.model) return;

        // Get bounding box of the model container (includes rotation)
        const box = new THREE.Box3().setFromObject(this.modelContainer);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = this.camera.fov * (Math.PI / 180);
        const distance = maxDim / (2 * Math.tan(fov / 2)) * 1.5;

        // Position camera at isometric-ish angle
        const direction = new THREE.Vector3(1, 0.7, 1).normalize();
        this.camera.position.copy(center).add(direction.multiplyScalar(distance));

        // Update controls
        this.controls.target.copy(center);
        this.controls.update();

        // Update grid position and size
        if (this.gridHelper) {
            this.gridHelper.position.y = box.min.y;
            const gridSize = Math.max(size.x, size.z) * 1.5;
            this.gridHelper.scale.set(gridSize / 20000, 1, gridSize / 20000);
        }
    }

    /**
     * Set view to predefined angle.
     * @param {string} view - View name: 'top', 'front', 'back', 'left', 'right', 'iso'
     */
    setView(view) {
        if (!this.model) return;

        const box = new THREE.Box3().setFromObject(this.modelContainer);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;

        let position;
        switch (view) {
            case 'top':
                position = new THREE.Vector3(0, distance, 0);
                break;
            case 'bottom':
                position = new THREE.Vector3(0, -distance, 0);
                break;
            case 'front': // South in BIM
                position = new THREE.Vector3(0, 0, distance);
                break;
            case 'back': // North in BIM
                position = new THREE.Vector3(0, 0, -distance);
                break;
            case 'left': // West in BIM
                position = new THREE.Vector3(-distance, 0, 0);
                break;
            case 'right': // East in BIM
                position = new THREE.Vector3(distance, 0, 0);
                break;
            case 'iso':
            default:
                position = new THREE.Vector3(distance, distance * 0.7, distance);
                break;
        }

        const targetPos = center.clone().add(position);
        this._animateCameraTo(targetPos, center);
    }

    /**
     * Get mesh count from current model.
     */
    getMeshCount() {
        if (!this.model) return 0;

        let count = 0;
        this.model.traverse((child) => {
            if (child.isMesh) count++;
        });
        return count;
    }

    /**
     * Dispose of renderer resources.
     */
    dispose() {
        if (this.renderer) {
            this.renderer.dispose();
        }
        if (this.controls) {
            this.controls.dispose();
        }
    }
}
