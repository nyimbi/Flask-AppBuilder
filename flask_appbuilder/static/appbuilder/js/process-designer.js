/**
 * Process Designer - Visual Workflow Builder
 * 
 * Provides drag-and-drop interface for creating business process workflows
 * with node creation, connection management, and property editing.
 */

class ProcessDesigner {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.svg = document.getElementById('canvas-svg');
        this.propertiesPanel = document.getElementById('properties-panel');
        
        this.options = {
            definitionId: null,
            initialGraph: { nodes: [], edges: [] },
            saveUrl: null,
            validateUrl: null,
            gridSize: 20,
            ...options
        };
        
        // State management
        this.nodes = new Map();
        this.edges = new Map();
        this.selectedNode = null;
        this.draggedNode = null;
        this.connecting = false;
        this.connectionStart = null;
        this.nextNodeId = 1;
        this.nextEdgeId = 1;
        
        // History management
        this.history = [];
        this.historyIndex = -1;
        
        // Event handlers
        this.handlers = {
            mousedown: this.onMouseDown.bind(this),
            mousemove: this.onMouseMove.bind(this),
            mouseup: this.onMouseUp.bind(this),
            click: this.onClick.bind(this),
            contextmenu: this.onContextMenu.bind(this)
        };
        
        // Node type configurations
        this.nodeTypes = {
            task: {
                width: 120,
                height: 80,
                color: '#007bff',
                icon: 'fa-tasks',
                shape: 'rectangle'
            },
            gateway: {
                width: 80,
                height: 80,
                color: '#ffc107',
                icon: 'fa-diamond',
                shape: 'diamond'
            },
            event: {
                width: 60,
                height: 60,
                color: '#28a745',
                icon: 'fa-circle',
                shape: 'circle'
            },
            approval: {
                width: 120,
                height: 80,
                color: '#dc3545',
                icon: 'fa-check-square',
                shape: 'rectangle'
            }
        };
    }
    
    initialize() {
        this.setupEventListeners();
        this.setupPalette();
        this.loadGraph(this.options.initialGraph);
        this.saveState();
    }
    
    setupEventListeners() {
        // Canvas event listeners
        Object.entries(this.handlers).forEach(([event, handler]) => {
            this.canvas.addEventListener(event, handler);
        });
        
        // Prevent context menu on canvas
        this.canvas.addEventListener('contextmenu', e => e.preventDefault());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', this.onKeyDown.bind(this));
    }
    
    setupPalette() {
        const paletteNodes = document.querySelectorAll('.palette-node');
        
        paletteNodes.forEach(node => {
            node.addEventListener('dragstart', this.onPaletteDragStart.bind(this));
            node.addEventListener('dragend', this.onPaletteDragEnd.bind(this));
            node.draggable = true;
        });
        
        // Make canvas a drop zone
        this.canvas.addEventListener('dragover', e => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
        });
        
        this.canvas.addEventListener('drop', this.onCanvasDrop.bind(this));
    }
    
    onPaletteDragStart(e) {
        const nodeType = e.target.dataset.nodeType;
        const nodeSubtype = e.target.dataset.nodeSubtype;
        
        e.dataTransfer.setData('text/plain', JSON.stringify({
            type: nodeType,
            subtype: nodeSubtype
        }));
        
        e.target.classList.add('dragging');
    }
    
    onPaletteDragEnd(e) {
        e.target.classList.remove('dragging');
    }
    
    onCanvasDrop(e) {
        e.preventDefault();
        
        try {
            const data = JSON.parse(e.dataTransfer.getData('text/plain'));
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            this.createNode(data.type, data.subtype, x, y);
        } catch (error) {
            console.error('Error dropping node:', error);
        }
    }
    
    createNode(type, subtype, x, y, data = {}) {
        const nodeId = `node_${this.nextNodeId++}`;
        const config = this.nodeTypes[type];
        
        // Snap to grid
        x = Math.round(x / this.options.gridSize) * this.options.gridSize;
        y = Math.round(y / this.options.gridSize) * this.options.gridSize;
        
        const nodeData = {
            id: nodeId,
            type: type,
            subtype: subtype,
            x: x,
            y: y,
            width: config.width,
            height: config.height,
            label: data.label || this.getDefaultLabel(type, subtype),
            properties: data.properties || this.getDefaultProperties(type, subtype),
            inputs: [],
            outputs: []
        };
        
        this.nodes.set(nodeId, nodeData);
        this.renderNode(nodeData);
        this.saveState();
        
        return nodeData;
    }
    
    renderNode(node) {
        const config = this.nodeTypes[node.type];
        const element = document.createElement('div');
        
        element.className = `canvas-node ${node.type}`;
        element.id = node.id;
        element.style.left = `${node.x}px`;
        element.style.top = `${node.y}px`;
        element.style.width = `${node.width}px`;
        element.style.height = `${node.height}px`;
        element.style.borderColor = config.color;
        
        // Add shape-specific styles
        if (config.shape === 'circle') {
            element.style.borderRadius = '50%';
        } else if (config.shape === 'diamond') {
            element.style.borderRadius = '50%';
            element.style.transform = 'rotate(45deg)';
        }
        
        element.innerHTML = `
            <div class="node-title">${node.label}</div>
            <div class="node-type">${node.subtype}</div>
            <div class="connection-point input" data-direction="input"></div>
            <div class="connection-point output" data-direction="output"></div>
        `;
        
        // Add event listeners
        element.addEventListener('mousedown', this.onNodeMouseDown.bind(this));
        element.addEventListener('click', this.onNodeClick.bind(this));
        
        // Add connection point listeners
        const connectionPoints = element.querySelectorAll('.connection-point');
        connectionPoints.forEach(point => {
            point.addEventListener('mousedown', this.onConnectionMouseDown.bind(this));
        });
        
        this.canvas.appendChild(element);
    }
    
    onNodeMouseDown(e) {
        if (e.target.classList.contains('connection-point')) {
            return; // Let connection handler deal with it
        }
        
        e.stopPropagation();
        const nodeId = e.currentTarget.id;
        const node = this.nodes.get(nodeId);
        
        if (!node) return;
        
        this.draggedNode = {
            node: node,
            startX: e.clientX - node.x,
            startY: e.clientY - node.y
        };
        
        this.selectNode(nodeId);
    }
    
    onNodeClick(e) {
        e.stopPropagation();
        const nodeId = e.currentTarget.id;
        this.selectNode(nodeId);
    }
    
    onConnectionMouseDown(e) {
        e.stopPropagation();
        
        const nodeElement = e.target.closest('.canvas-node');
        const nodeId = nodeElement.id;
        const direction = e.target.dataset.direction;
        
        this.connecting = true;
        this.connectionStart = {
            nodeId: nodeId,
            direction: direction,
            element: e.target
        };
        
        // Create temporary connection line
        this.createTempConnectionLine(e.clientX, e.clientY);
    }
    
    onMouseMove(e) {
        if (this.draggedNode) {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left - this.draggedNode.startX;
            const y = e.clientY - rect.top - this.draggedNode.startY;
            
            // Snap to grid
            const snapX = Math.round(x / this.options.gridSize) * this.options.gridSize;
            const snapY = Math.round(y / this.options.gridSize) * this.options.gridSize;
            
            this.moveNode(this.draggedNode.node.id, snapX, snapY);
        }
        
        if (this.connecting && this.tempLine) {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            this.updateTempConnectionLine(x, y);
        }
    }
    
    onMouseUp(e) {
        if (this.draggedNode) {
            this.saveState();
            this.draggedNode = null;
        }
        
        if (this.connecting) {
            const target = e.target;
            
            if (target.classList.contains('connection-point')) {
                const targetNode = target.closest('.canvas-node');
                const targetDirection = target.dataset.direction;
                
                this.createConnection(
                    this.connectionStart.nodeId,
                    this.connectionStart.direction,
                    targetNode.id,
                    targetDirection
                );
            }
            
            this.connecting = false;
            this.connectionStart = null;
            this.removeTempConnectionLine();
        }
    }
    
    onClick(e) {
        // Deselect node if clicking on empty canvas
        if (e.target === this.canvas) {
            this.deselectNode();
        }
    }
    
    onContextMenu(e) {
        if (e.target.classList.contains('canvas-node')) {
            this.showContextMenu(e, e.target.id);
        }
    }
    
    onKeyDown(e) {
        switch (e.key) {
            case 'Delete':
            case 'Backspace':
                if (this.selectedNode) {
                    this.deleteNode(this.selectedNode);
                }
                break;
            case 'z':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    if (e.shiftKey) {
                        this.redo();
                    } else {
                        this.undo();
                    }
                }
                break;
            case 's':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.saveProcess();
                }
                break;
        }
    }
    
    moveNode(nodeId, x, y) {
        const node = this.nodes.get(nodeId);
        if (!node) return;
        
        node.x = x;
        node.y = y;
        
        const element = document.getElementById(nodeId);
        if (element) {
            element.style.left = `${x}px`;
            element.style.top = `${y}px`;
        }
        
        // Update connected edges
        this.updateNodeConnections(nodeId);
    }
    
    selectNode(nodeId) {
        this.deselectNode();
        
        const element = document.getElementById(nodeId);
        const node = this.nodes.get(nodeId);
        
        if (element && node) {
            element.classList.add('selected');
            this.selectedNode = nodeId;
            this.showNodeProperties(node);
        }
    }
    
    deselectNode() {
        if (this.selectedNode) {
            const element = document.getElementById(this.selectedNode);
            if (element) {
                element.classList.remove('selected');
            }
            this.selectedNode = null;
            this.hideNodeProperties();
        }
    }
    
    deleteNode(nodeId) {
        const node = this.nodes.get(nodeId);
        if (!node) return;
        
        // Remove connected edges
        const connectedEdges = Array.from(this.edges.values()).filter(
            edge => edge.source === nodeId || edge.target === nodeId
        );
        
        connectedEdges.forEach(edge => {
            this.deleteEdge(edge.id);
        });
        
        // Remove node
        this.nodes.delete(nodeId);
        const element = document.getElementById(nodeId);
        if (element) {
            element.remove();
        }
        
        if (this.selectedNode === nodeId) {
            this.deselectNode();
        }
        
        this.saveState();
    }
    
    createConnection(sourceId, sourceDir, targetId, targetDir) {
        // Validate connection
        if (sourceId === targetId) return; // Can't connect to self
        if (sourceDir === 'input' && targetDir === 'input') return; // Invalid connection
        if (sourceDir === 'output' && targetDir === 'output') return; // Invalid connection
        
        // Check for existing connection
        const existing = Array.from(this.edges.values()).find(
            edge => (edge.source === sourceId && edge.target === targetId) ||
                   (edge.source === targetId && edge.target === sourceId)
        );
        
        if (existing) return; // Connection already exists
        
        const edgeId = `edge_${this.nextEdgeId++}`;
        const edge = {
            id: edgeId,
            source: sourceDir === 'output' ? sourceId : targetId,
            target: sourceDir === 'output' ? targetId : sourceId,
            label: '',
            properties: {}
        };
        
        this.edges.set(edgeId, edge);
        this.renderEdge(edge);
        this.saveState();
        
        return edge;
    }
    
    renderEdge(edge) {
        const sourceNode = this.nodes.get(edge.source);
        const targetNode = this.nodes.get(edge.target);
        
        if (!sourceNode || !targetNode) return;
        
        const path = this.createConnectionPath(sourceNode, targetNode);
        const pathElement = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        
        pathElement.setAttribute('id', edge.id);
        pathElement.setAttribute('d', path);
        pathElement.setAttribute('class', 'connection-line');
        
        // Add click handler for edge selection
        pathElement.addEventListener('click', () => {
            this.selectEdge(edge.id);
        });
        
        this.svg.appendChild(pathElement);
    }
    
    createConnectionPath(sourceNode, targetNode) {
        const sourceX = sourceNode.x + sourceNode.width;
        const sourceY = sourceNode.y + sourceNode.height / 2;
        const targetX = targetNode.x;
        const targetY = targetNode.y + targetNode.height / 2;
        
        // Create curved path
        const controlOffset = Math.abs(targetX - sourceX) / 3;
        const controlX1 = sourceX + controlOffset;
        const controlY1 = sourceY;
        const controlX2 = targetX - controlOffset;
        const controlY2 = targetY;
        
        return `M ${sourceX} ${sourceY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${targetX} ${targetY}`;
    }
    
    updateNodeConnections(nodeId) {
        const connectedEdges = Array.from(this.edges.values()).filter(
            edge => edge.source === nodeId || edge.target === nodeId
        );
        
        connectedEdges.forEach(edge => {
            const pathElement = document.getElementById(edge.id);
            if (pathElement) {
                const sourceNode = this.nodes.get(edge.source);
                const targetNode = this.nodes.get(edge.target);
                const path = this.createConnectionPath(sourceNode, targetNode);
                pathElement.setAttribute('d', path);
            }
        });
    }
    
    createTempConnectionLine(x, y) {
        this.tempLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        this.tempLine.setAttribute('class', 'temp-connection');
        this.tempLine.setAttribute('stroke', '#007bff');
        this.tempLine.setAttribute('stroke-width', '2');
        this.tempLine.setAttribute('stroke-dasharray', '5,5');
        
        const startPoint = this.connectionStart.element.getBoundingClientRect();
        const canvasRect = this.canvas.getBoundingClientRect();
        
        this.tempLine.setAttribute('x1', startPoint.left - canvasRect.left + 5);
        this.tempLine.setAttribute('y1', startPoint.top - canvasRect.top + 5);
        this.tempLine.setAttribute('x2', x);
        this.tempLine.setAttribute('y2', y);
        
        this.svg.appendChild(this.tempLine);
    }
    
    updateTempConnectionLine(x, y) {
        if (this.tempLine) {
            this.tempLine.setAttribute('x2', x);
            this.tempLine.setAttribute('y2', y);
        }
    }
    
    removeTempConnectionLine() {
        if (this.tempLine) {
            this.tempLine.remove();
            this.tempLine = null;
        }
    }
    
    showNodeProperties(node) {
        const propertiesHtml = this.generatePropertiesForm(node);
        document.getElementById('node-properties').innerHTML = propertiesHtml;
        
        // Bind property change handlers
        this.bindPropertyHandlers(node);
    }
    
    hideNodeProperties() {
        document.getElementById('node-properties').innerHTML = 
            '<p class="text-muted">Select a node to edit its properties</p>';
    }
    
    generatePropertiesForm(node) {
        const config = this.nodeTypes[node.type];
        
        let html = `
            <div class="form-group">
                <label for="node-label">Label</label>
                <input type="text" id="node-label" class="form-control" value="${node.label}">
            </div>
        `;
        
        // Add type-specific properties
        switch (node.type) {
            case 'task':
                html += this.getTaskProperties(node);
                break;
            case 'gateway':
                html += this.getGatewayProperties(node);
                break;
            case 'event':
                html += this.getEventProperties(node);
                break;
            case 'approval':
                html += this.getApprovalProperties(node);
                break;
        }
        
        html += `
            <div class="form-group">
                <button type="button" class="btn btn-sm btn-danger" onclick="designer.deleteSelectedNode()">
                    <i class="fa fa-trash"></i> Delete Node
                </button>
            </div>
        `;
        
        return html;
    }
    
    getTaskProperties(node) {
        const props = node.properties;
        
        return `
            <div class="form-group">
                <label for="task-assignee">Assignee</label>
                <input type="text" id="task-assignee" class="form-control" 
                       value="${props.assignee || ''}" placeholder="User or role">
            </div>
            <div class="form-group">
                <label for="task-form">Form Key</label>
                <input type="text" id="task-form" class="form-control" 
                       value="${props.form_key || ''}" placeholder="Form identifier">
            </div>
            <div class="form-group">
                <label for="task-due-date">Due Date Expression</label>
                <input type="text" id="task-due-date" class="form-control" 
                       value="${props.due_date || ''}" placeholder="PT1H, P1D, etc.">
            </div>
        `;
    }
    
    getGatewayProperties(node) {
        const props = node.properties;
        
        return `
            <div class="form-group">
                <label for="gateway-condition">Default Condition</label>
                <textarea id="gateway-condition" class="form-control" rows="3" 
                         placeholder="JavaScript expression">${props.condition || ''}</textarea>
            </div>
        `;
    }
    
    getEventProperties(node) {
        const props = node.properties;
        
        if (node.subtype === 'timer') {
            return `
                <div class="form-group">
                    <label for="timer-duration">Duration</label>
                    <input type="text" id="timer-duration" class="form-control" 
                           value="${props.duration || ''}" placeholder="PT5M, PT1H, P1D">
                </div>
            `;
        }
        
        return '';
    }
    
    getApprovalProperties(node) {
        const props = node.properties;
        
        return `
            <div class="form-group">
                <label for="approval-approvers">Approvers</label>
                <textarea id="approval-approvers" class="form-control" rows="3" 
                         placeholder="Comma-separated list of users or roles">${props.approvers || ''}</textarea>
            </div>
            <div class="form-group">
                <label for="approval-threshold">Approval Threshold</label>
                <input type="number" id="approval-threshold" class="form-control" 
                       value="${props.threshold || 1}" min="1">
            </div>
        `;
    }
    
    bindPropertyHandlers(node) {
        // Label change handler
        const labelInput = document.getElementById('node-label');
        if (labelInput) {
            labelInput.addEventListener('input', () => {
                node.label = labelInput.value;
                this.updateNodeLabel(node.id, labelInput.value);
            });
        }
        
        // Type-specific handlers
        const propertyInputs = document.querySelectorAll('#node-properties input, #node-properties textarea');
        propertyInputs.forEach(input => {
            if (input.id === 'node-label') return; // Already handled
            
            input.addEventListener('input', () => {
                const propertyName = input.id.split('-').slice(1).join('_');
                node.properties[propertyName] = input.value;
            });
        });
    }
    
    updateNodeLabel(nodeId, label) {
        const element = document.getElementById(nodeId);
        if (element) {
            const titleElement = element.querySelector('.node-title');
            if (titleElement) {
                titleElement.textContent = label;
            }
        }
    }
    
    getDefaultLabel(type, subtype) {
        const labels = {
            task: {
                user: 'User Task',
                service: 'Service Task',
                script: 'Script Task',
                manual: 'Manual Task'
            },
            gateway: {
                exclusive: 'Exclusive Gateway',
                parallel: 'Parallel Gateway',
                inclusive: 'Inclusive Gateway'
            },
            event: {
                start: 'Start',
                end: 'End',
                timer: 'Timer',
                message: 'Message'
            },
            approval: {
                single: 'Single Approval',
                multi: 'Multi Approval'
            }
        };
        
        return labels[type]?.[subtype] || 'New Node';
    }
    
    getDefaultProperties(type, subtype) {
        const properties = {
            task: {
                assignee: '',
                form_key: '',
                due_date: ''
            },
            gateway: {
                condition: ''
            },
            event: {
                duration: ''
            },
            approval: {
                approvers: '',
                threshold: 1
            }
        };
        
        return properties[type] || {};
    }
    
    saveState() {
        const state = this.getProcessGraph();
        
        // Remove future states if we're not at the end
        this.history.splice(this.historyIndex + 1);
        
        this.history.push(JSON.parse(JSON.stringify(state)));
        this.historyIndex = this.history.length - 1;
        
        // Limit history size
        if (this.history.length > 50) {
            this.history.shift();
            this.historyIndex--;
        }
    }
    
    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.loadGraph(this.history[this.historyIndex]);
        }
    }
    
    redo() {
        if (this.historyIndex < this.history.length - 1) {
            this.historyIndex++;
            this.loadGraph(this.history[this.historyIndex]);
        }
    }
    
    getProcessGraph() {
        const nodes = Array.from(this.nodes.values());
        const edges = Array.from(this.edges.values());
        
        return {
            nodes: nodes,
            edges: edges
        };
    }
    
    loadGraph(graph) {
        // Clear existing
        this.clearCanvas();
        this.nodes.clear();
        this.edges.clear();
        
        // Load nodes
        if (graph.nodes) {
            graph.nodes.forEach(nodeData => {
                this.nodes.set(nodeData.id, nodeData);
                this.renderNode(nodeData);
                
                // Update next ID counter
                const idNum = parseInt(nodeData.id.split('_')[1]);
                if (idNum >= this.nextNodeId) {
                    this.nextNodeId = idNum + 1;
                }
            });
        }
        
        // Load edges
        if (graph.edges) {
            graph.edges.forEach(edgeData => {
                this.edges.set(edgeData.id, edgeData);
                this.renderEdge(edgeData);
                
                // Update next ID counter
                const idNum = parseInt(edgeData.id.split('_')[1]);
                if (idNum >= this.nextEdgeId) {
                    this.nextEdgeId = idNum + 1;
                }
            });
        }
    }
    
    clearCanvas() {
        // Remove all nodes
        const nodeElements = this.canvas.querySelectorAll('.canvas-node');
        nodeElements.forEach(element => element.remove());
        
        // Remove all edges
        const edgeElements = this.svg.querySelectorAll('path');
        edgeElements.forEach(element => element.remove());
        
        this.deselectNode();
    }
    
    validateProcess() {
        const graph = this.getProcessGraph();
        const errors = [];
        
        // Check for start node
        const startNodes = graph.nodes.filter(node => 
            node.type === 'event' && node.subtype === 'start'
        );
        
        if (startNodes.length === 0) {
            errors.push('Process must have a start event');
        } else if (startNodes.length > 1) {
            errors.push('Process can only have one start event');
        }
        
        // Check for end node
        const endNodes = graph.nodes.filter(node => 
            node.type === 'event' && node.subtype === 'end'
        );
        
        if (endNodes.length === 0) {
            errors.push('Process must have at least one end event');
        }
        
        // Check for disconnected nodes
        graph.nodes.forEach(node => {
            const hasIncoming = graph.edges.some(edge => edge.target === node.id);
            const hasOutgoing = graph.edges.some(edge => edge.source === node.id);
            
            if (!hasIncoming && node.type !== 'event') {
                errors.push(`Node "${node.label}" has no incoming connections`);
            }
            
            if (!hasOutgoing && node.subtype !== 'end') {
                errors.push(`Node "${node.label}" has no outgoing connections`);
            }
        });
        
        // Show validation results
        if (errors.length === 0) {
            this.showMessage('Process validation passed!', 'success');
        } else {
            this.showMessage(`Validation failed:\n${errors.join('\n')}`, 'error');
        }
        
        return errors.length === 0;
    }
    
    saveProcess() {
        if (!this.options.saveUrl) {
            this.showMessage('Save URL not configured', 'error');
            return;
        }
        
        const graph = this.getProcessGraph();
        
        fetch(this.options.saveUrl, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                process_graph: graph
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.result) {
                this.showMessage('Process saved successfully!', 'success');
            } else {
                this.showMessage('Failed to save process', 'error');
            }
        })
        .catch(error => {
            console.error('Save error:', error);
            this.showMessage('Error saving process', 'error');
        });
    }
    
    showMessage(message, type) {
        // Create and show toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} designer-toast`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            opacity: 0;
            transition: opacity 0.3s;
        `;
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.style.opacity = '1';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    getCSRFToken() {
        const tokenElement = document.querySelector('meta[name=csrf-token]');
        return tokenElement ? tokenElement.getAttribute('content') : '';
    }
    
    deleteSelectedNode() {
        if (this.selectedNode) {
            this.deleteNode(this.selectedNode);
        }
    }
    
    zoomToFit() {
        // Calculate bounds of all nodes
        const nodes = Array.from(this.nodes.values());
        if (nodes.length === 0) return;
        
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        
        nodes.forEach(node => {
            minX = Math.min(minX, node.x);
            minY = Math.min(minY, node.y);
            maxX = Math.max(maxX, node.x + node.width);
            maxY = Math.max(maxY, node.y + node.height);
        });
        
        // Add padding
        const padding = 50;
        minX -= padding;
        minY -= padding;
        maxX += padding;
        maxY += padding;
        
        // Calculate scale and offset
        const canvasRect = this.canvas.getBoundingClientRect();
        const contentWidth = maxX - minX;
        const contentHeight = maxY - minY;
        const scale = Math.min(
            canvasRect.width / contentWidth,
            canvasRect.height / contentHeight,
            1
        );
        
        // Apply transform (simplified version - real implementation would need proper pan/zoom)
        this.canvas.style.transform = `scale(${scale})`;
        this.canvas.style.transformOrigin = `${minX}px ${minY}px`;
    }
}

// Make ProcessDesigner globally available
window.ProcessDesigner = ProcessDesigner;