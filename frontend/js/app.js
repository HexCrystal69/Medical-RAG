/**
 * Dashboard & Document Catalog Logic
 * ===================================
 */

document.addEventListener("DOMContentLoaded", () => {
    loadDocuments();
});

const API_BASE = "";

// Load documents from backend
async function loadDocuments() {
    const listBody = document.getElementById("doc-list-body");
    const docCountVal = document.getElementById("total-docs-count");
    const pageCountVal = document.getElementById("total-pages-count");

    try {
        const response = await fetch(`${API_BASE}/documents`);
        if (!response.ok) throw new Error("Failed to fetch documents.");
        
        const docs = await response.json();
        
        // Update Stats
        docCountVal.innerText = docs.length;
        let totalPages = docs.reduce((sum, d) => sum + (d.page_count || 0), 0);
        pageCountVal.innerText = totalPages;

        if (docs.length === 0) {
            listBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                        No indexed documents found. Upload a PDF to get started!
                    </td>
                </tr>
            `;
            return;
        }

        listBody.innerHTML = docs.map(doc => `
            <tr>
                <td style="font-weight: 500;">📄 ${escapeHtml(doc.filename)}</td>
                <td>${doc.page_count} page(s)</td>
                <td style="color: var(--text-secondary); font-size: 0.9rem;">${doc.timestamp}</td>
                <td>
                    <button class="btn btn-danger" onclick="deleteDocument('${doc.id}')" style="padding: 0.4rem 0.8rem; font-size: 0.8rem;">
                        Delete
                    </button>
                </td>
            </tr>
        `).join("");

    } catch (err) {
        listBody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--red-danger); padding: 2rem;">
                    Error loading catalog: ${err.message}
                </td>
            </tr>
        `;
    }
}

// Upload file select handler
async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    await uploadFile(file);
}

// Upload file action
async function uploadFile(file) {
    const statusDiv = document.getElementById("upload-status");
    statusDiv.innerHTML = `
        <div class="loading-indicator">
            <div class="spinner"></div>
            <span>Uploading and parsing ${escapeHtml(file.name)} (running incremental indexing) ...</span>
        </div>
    `;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE}/documents/upload`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Upload failed.");
        }

        const result = await response.json();
        statusDiv.innerHTML = `
            <div style="color: var(--green-success); font-weight: 500; font-size: 0.95rem; margin-top: 0.5rem;">
                ✓ ${escapeHtml(result.message)}
            </div>
        `;
        // Reload list
        await loadDocuments();

    } catch (err) {
        statusDiv.innerHTML = `
            <div style="color: var(--red-danger); font-weight: 500; font-size: 0.95rem; margin-top: 0.5rem;">
                ❌ Error: ${err.message}
            </div>
        `;
    }
}

// Delete document action
async function deleteDocument(docId) {
    if (!confirm("Are you sure you want to delete this document? Its chunks will be purged from the index.")) return;

    try {
        const response = await fetch(`${API_BASE}/documents/${docId}`, {
            method: "DELETE"
        });

        if (!response.ok) throw new Error("Deletion failed.");
        
        await loadDocuments();
    } catch (err) {
        alert(`Error deleting document: ${err.message}`);
    }
}

// Rebuild index action
async function rebuildIndex() {
    const btn = document.getElementById("rebuild-btn");
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `🔄 Rebuilding...`;

    try {
        const response = await fetch(`${API_BASE}/documents/rebuild-index`, {
            method: "POST"
        });

        if (!response.ok) throw new Error("Rebuild failed.");
        
        const res = await response.json();
        alert(res.message);
        await loadDocuments();
    } catch (err) {
        alert(`Error rebuilding index: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Drag & drop dropzone events
const dropzone = document.getElementById("dropzone");
if (dropzone) {
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "var(--accent-blue)";
            dropzone.style.background = "rgba(59, 130, 246, 0.05)";
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "rgba(255, 255, 255, 0.15)";
            dropzone.style.background = "rgba(255, 255, 255, 0.01)";
        }, false);
    });

    dropzone.addEventListener("drop", async (e) => {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        if (file && file.name.lower().endsWith(".pdf")) {
            await uploadFile(file);
        } else {
            alert("Only PDF files are supported.");
        }
    });
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
