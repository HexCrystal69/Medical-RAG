/**
 * Interactive Knowledge Graph Simulator (HTML5 Canvas)
 * ====================================================
 */

const API_BASE = "";

// Node category styling mapping
const CATEGORY_STYLES = {
    "disease": { color: "#EF4444", label: "Disease", radius: 24 },
    "symptom": { color: "#F59E0B", label: "Symptom", radius: 18 },
    "treatment": { color: "#10B981", label: "Treatment", radius: 18 },
    "medication": { color: "#3B82F6", label: "Medication", radius: 18 },
    "risk_factor": { color: "#8B5CF6", label: "Risk Factor", radius: 18 }
};

// State Variables
let nodes = [];
let links = [];
let filteredNodes = [];
let filteredLinks = [];

let selectedNode = null;
let hoveredNode = null;
let draggedNode = null;

// Zoom and Pan
let transform = { x: 0, y: 0, k: 1 };
let isPanning = false;
let startPan = { x: 0, y: 0 };

const canvas = document.getElementById("graph-canvas");
const ctx = canvas.getContext("2d");

// Resize handler
function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = 580;
}

window.addEventListener("resize", () => {
    resizeCanvas();
    draw();
});

// Setup Mouse Events
function setupMouseEvents() {
    canvas.addEventListener("mousedown", (e) => {
        const mouse = getMousePos(e);
        const node = findNodeAt(mouse.x, mouse.y);
        
        if (node) {
            draggedNode = node;
            selectedNode = node;
            displayNodeDetails(node);
        } else {
            isPanning = true;
            startPan = { x: e.clientX - transform.x, y: e.clientY - transform.y };
        }
    });

    canvas.addEventListener("mousemove", (e) => {
        const mouse = getMousePos(e);
        
        if (draggedNode) {
            draggedNode.x = mouse.x;
            draggedNode.y = mouse.y;
            draggedNode.vx = 0;
            draggedNode.vy = 0;
        } else if (isPanning) {
            transform.x = e.clientX - startPan.x;
            transform.y = e.clientY - startPan.y;
        } else {
            hoveredNode = findNodeAt(mouse.x, mouse.y);
            canvas.style.cursor = hoveredNode ? "pointer" : isPanning ? "grabbing" : "grab";
        }
    });

    window.addEventListener("mouseup", () => {
        draggedNode = null;
        isPanning = false;
    });

    canvas.addEventListener("wheel", (e) => {
        e.preventDefault();
        const mouse = { x: e.offsetX, y: e.offsetY };
        const zoomIntensity = 0.1;
        
        const wheel = e.deltaY < 0 ? 1 : -1;
        const zoomFactor = Math.exp(wheel * zoomIntensity);
        
        const targetX = (mouse.x - transform.x) / transform.k;
        const targetY = (mouse.y - transform.y) / transform.k;
        
        transform.k = Math.min(Math.max(transform.k * zoomFactor, 0.2), 4);
        transform.x = mouse.x - targetX * transform.k;
        transform.y = mouse.y - targetY * transform.k;
    });
}

function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: (e.clientX - rect.left - transform.x) / transform.k,
        y: (e.clientY - rect.top - transform.y) / transform.k
    };
}

function findNodeAt(x, y) {
    for (let node of filteredNodes) {
        const dist = Math.hypot(node.x - x, node.y - y);
        if (dist <= node.radius) return node;
    }
    return null;
}

// Graph simulation loop (Physics Engine)
function updatePhysics() {
    const width = canvas.width;
    const height = canvas.height;

    // Apply forces
    const gravity = 0.05; // pull to center
    const repulsion = 1200; // repel nodes
    const attraction = 0.06; // pull along links

    // Repulsion force
    for (let i = 0; i < filteredNodes.length; i++) {
        const nodeA = filteredNodes[i];
        if (nodeA === draggedNode) continue;
        
        for (let j = i + 1; j < filteredNodes.length; j++) {
            const nodeB = filteredNodes[j];
            const dx = nodeB.x - nodeA.x;
            const dy = nodeB.y - nodeA.y;
            const dist = Math.hypot(dx, dy) || 1;
            
            // Push away
            const force = repulsion / (dist * dist);
            const forceX = (dx / dist) * force;
            const forceY = (dy / dist) * force;
            
            nodeA.vx -= forceX;
            nodeA.vy -= forceY;
            nodeB.vx += forceX;
            nodeB.vy += forceY;
        }
    }

    // Attraction force along links
    for (let link of filteredLinks) {
        const source = filteredNodes.find(n => n.id === link.source);
        const target = filteredNodes.find(n => n.id === link.target);
        
        if (!source || !target) continue;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.hypot(dx, dy) || 1;
        
        const force = attraction * (dist - 100); // 100 is target link length
        const forceX = (dx / dist) * force;
        const forceY = (dy / dist) * force;

        if (source !== draggedNode) {
            source.vx += forceX;
            source.vy += forceY;
        }
        if (target !== draggedNode) {
            target.vx -= forceX;
            target.vy -= forceY;
        }
    }

    // Apply velocity, friction and gravity (center gravity)
    const friction = 0.85;
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    for (let node of filteredNodes) {
        if (node === draggedNode) continue;

        // Gravity pull to center
        node.vx += (centerX - node.x) * gravity * 0.1;
        node.vy += (centerY - node.y) * gravity * 0.1;

        node.vx *= friction;
        node.vy *= friction;
        
        node.x += node.vx;
        node.y += node.vy;
    }
}

// Canvas Drawing logic
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.translate(transform.x, transform.y);
    ctx.scale(transform.k, transform.k);

    // Draw links
    ctx.lineWidth = 1.5;
    for (let link of filteredLinks) {
        const source = filteredNodes.find(n => n.id === link.source);
        const target = filteredNodes.find(n => n.id === link.target);
        
        if (!source || !target) continue;

        // Draw line
        ctx.strokeStyle = "rgba(255,255,255,0.08)";
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();

        // Draw link label
        ctx.fillStyle = "rgba(255,255,255,0.3)";
        ctx.font = "10px Inter";
        ctx.fillText(link.label, (source.x + target.x) / 2, (source.y + target.y) / 2);
    }

    // Draw nodes
    for (let node of filteredNodes) {
        const style = CATEGORY_STYLES[node.category] || { color: "#FFF", radius: 15 };
        
        // Glow effect
        ctx.shadowColor = style.color;
        ctx.shadowBlur = (hoveredNode === node || selectedNode === node) ? 15 : 0;

        ctx.fillStyle = style.color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fill();

        // Stroke
        ctx.shadowBlur = 0; // reset shadow
        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label inside or below node
        ctx.fillStyle = "#FFF";
        ctx.font = "bold 12px Inter";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        
        // Handle long node labels
        let text = node.label;
        if (text.length > 8) {
            text = text.substring(0, 7) + "..";
        }
        ctx.fillText(text, node.x, node.y);

        // Hover tooltip/label below node
        if (hoveredNode === node || selectedNode === node) {
            ctx.font = "bold 10px Inter";
            ctx.fillStyle = "rgba(0,0,0,0.8)";
            ctx.fillRect(node.x - 50, node.y + node.radius + 5, 100, 16);
            ctx.fillStyle = "#FFF";
            ctx.fillText(node.label, node.x, node.y + node.radius + 13);
        }
    }

    ctx.restore();
}

function animate() {
    updatePhysics();
    draw();
    requestAnimationFrame(animate);
}

// Build nodes dynamically from extracted medical entities
async function extractToGraph() {
    const input = document.getElementById("graph-topic-input");
    const query = input.value.trim();
    if (!query) return;

    const btn = document.getElementById("graph-gen-btn");
    const loading = document.getElementById("loading");

    btn.disabled = true;
    loading.style.display = "flex";

    try {
        // Step A: Search database for top 3 matching passages
        const searchResp = await fetch(`${API_BASE}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: query,
                limit: 3,
                threshold: 0.50
            })
        });

        if (!searchResp.ok) throw new Error("Vector search failed.");
        const searchData = await searchResp.json();

        // Concatenate passages
        const passages = (searchData.results || []).map(r => r.passage).join("\n\n");
        const scanText = passages || query; // fallback to user text directly if DB is empty

        // Step B: Send to entity extractor
        const entityResp = await fetch(`${API_BASE}/entities`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: scanText })
        });

        if (!entityResp.ok) throw new Error("Entity extraction failed.");
        const entities = await entityResp.json();

        // Step C: Incorporate into graph nodes
        addEntitiesToGraph(query, entities);

    } catch (err) {
        alert(`Failed to extract entities: ${err.message}`);
    } finally {
        btn.disabled = false;
        loading.style.display = "none";
        input.value = "";
    }
}

function addEntitiesToGraph(mainTopic, data) {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    // Create root disease node
    const rootId = mainTopic.toLowerCase().replace(/\s+/g, "_");
    let rootNode = nodes.find(n => n.id === rootId);
    if (!rootNode) {
        rootNode = {
            id: rootId,
            label: mainTopic,
            category: "disease",
            x: centerX + (Math.random() - 0.5) * 50,
            y: centerY + (Math.random() - 0.5) * 50,
            vx: 0, vy: 0,
            radius: CATEGORY_STYLES["disease"].radius
        };
        nodes.push(rootNode);
    }

    const mapping = [
        { key: "diseases", category: "disease", label: "related" },
        { key: "symptoms", category: "symptom", label: "symptom" },
        { key: "treatments", category: "treatment", label: "treatment" },
        { key: "medications", category: "medication", label: "treatment" },
        { key: "risk_factors", category: "risk_factor", label: "risk" }
    ];

    mapping.forEach(map => {
        const items = data[map.key] || [];
        items.forEach(item => {
            const itemId = item.toLowerCase().replace(/\s+/g, "_");
            if (itemId === rootId) return;

            let node = nodes.find(n => n.id === itemId);
            if (!node) {
                node = {
                    id: itemId,
                    label: item,
                    category: map.category,
                    x: centerX + (Math.random() - 0.5) * 200,
                    y: centerY + (Math.random() - 0.5) * 200,
                    vx: 0, vy: 0,
                    radius: CATEGORY_STYLES[map.category].radius
                };
                nodes.push(node);
            }

            // Create Link
            const linkId = `${rootId}-${itemId}`;
            let link = links.find(l => l.id === linkId);
            if (!link) {
                links.push({
                    id: linkId,
                    source: rootId,
                    target: itemId,
                    label: map.label
                });
            }
        });
    });

    toggleFilter(); // Apply filters & draw updated nodes
}

// Apply checked filter toggles
function toggleFilter() {
    const filters = {
        "disease": document.getElementById("chk-diseases").checked,
        "symptom": document.getElementById("chk-symptoms").checked,
        "treatment": document.getElementById("chk-treatments").checked,
        "medication": document.getElementById("chk-medications").checked,
        "risk_factor": document.getElementById("chk-risks").checked
    };

    filteredNodes = nodes.filter(n => filters[n.category]);
    
    // Links must connect nodes that both pass filters
    filteredLinks = links.filter(l => {
        const s = nodes.find(n => n.id === l.source);
        const t = nodes.find(n => n.id === l.target);
        return s && t && filters[s.category] && filters[t.category];
    });
}

// Render selected node info in side-panel
function displayNodeDetails(node) {
    const detailsDiv = document.getElementById("node-details");
    const style = CATEGORY_STYLES[node.category];

    // Find links
    const relatedLinks = links.filter(l => l.source === node.id || l.target === node.id);
    const connections = relatedLinks.map(l => {
        const otherId = l.source === node.id ? l.target : l.source;
        const otherNode = nodes.find(n => n.id === otherId);
        return {
            label: otherNode ? otherNode.label : "Unknown",
            category: otherNode ? otherNode.category : "general",
            rel: l.label
        };
    });

    detailsDiv.innerHTML = `
        <div style="border-left: 4px solid ${style.color}; padding-left: 0.75rem; margin-bottom: 1rem;">
            <h3 style="margin-bottom: 0.25rem;">${escapeHtml(node.label)}</h3>
            <span style="font-size: 0.8rem; font-weight: 600; color: ${style.color}; text-transform: uppercase;">
                ${style.label}
            </span>
        </div>
        
        <h4>Connected Relationships:</h4>
        <div style="max-height: 200px; overflow-y: auto; margin-top: 0.5rem; display: flex; flex-direction: column; gap: 0.5rem;">
            ${connections.length === 0 ? '<div style="color: var(--text-muted);">No active connections.</div>' : 
                connections.map(c => `
                    <div style="background: rgba(255,255,255,0.02); padding: 0.5rem; border-radius: 6px; font-size: 0.85rem; display: flex; justify-content: space-between;">
                        <span>${escapeHtml(c.label)}</span>
                        <span style="color: var(--text-muted); font-style: italic;">(${c.rel})</span>
                    </div>
                `).join("")
            }
        </div>
    `;
}

function resetGraphView() {
    transform = { x: 0, y: 0, k: 1 };
}

// Initializing
document.addEventListener("DOMContentLoaded", () => {
    resizeCanvas();
    setupMouseEvents();
    
    // Seed sample graph data
    const sampleEntities = {
        diseases: ["Type 2 Diabetes", "Hypertension"],
        symptoms: ["Polyuria", "Headache"],
        treatments: ["Diet Control", "Exercise"],
        medications: ["Metformin", "Lisinopril"],
        risk_factors: ["Obesity", "Family History"]
    };
    addEntitiesToGraph("Cardiovascular Risk Factors", sampleEntities);

    animate();
});
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
