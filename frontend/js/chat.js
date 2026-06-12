/**
 * Chat Interface Client Logic
 * ============================
 */

const API_BASE = "";
let currentStrategy = "hybrid";
let lastQueryData = null; // store last answer for exporter

document.addEventListener("DOMContentLoaded", () => {
    setupStrategySelectors();
});

// Setup click handlers for retrieval strategy badges
function setupStrategySelectors() {
    const badges = document.querySelectorAll("#strategy-bar .strategy-badge");
    badges.forEach(badge => {
        badge.addEventListener("click", () => {
            badges.forEach(b => b.classList.remove("active"));
            badge.classList.add("active");
            currentStrategy = badge.getAttribute("data-strategy");
        });
    });
}

// Send user query to FastAPI
async function sendQuery() {
    const input = document.getElementById("query-input");
    const query = input.value.trim();
    if (!query) return;

    input.value = "";
    
    // Add user message to UI
    appendMessage(query, "user");

    const loading = document.getElementById("loading");
    loading.style.display = "flex";

    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: query,
                strategy: currentStrategy
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Query failed.");
        }

        const data = await response.json();
        lastQueryData = data; // cache for export

        // Add assistant message
        appendMessage(data.answer, "assistant", data.sources, data.is_fallback, data.latencies);

        // Display Citations Panel
        renderCitations(data.sources, data.confidence_score, data.is_fallback, data.retrieval_strategy);

    } catch (err) {
        appendMessage(`Error: ${err.message}`, "system");
    } finally {
        loading.style.display = "none";
    }
}

// Append message block to conversation view
function appendMessage(text, sender, sources = null, isFallback = false, latencies = null) {
    const chatBox = document.getElementById("chat-box");
    const msgDiv = document.createElement("div");
    
    msgDiv.classList.add("message");
    if (sender === "user") {
        msgDiv.classList.add("message-user");
        msgDiv.innerText = text;
    } else if (sender === "assistant") {
        msgDiv.classList.add("message-assistant");
        
        let htmlContent = `<div>${escapeHtml(text).replace(/\n/g, "<br/>")}</div>`;
        
        // Add sources footer in bubble
        if (sources && sources.length > 0 && !isFallback) {
            htmlContent += `
                <div class="message-sources">
                    <strong>References:</strong>
                    ${sources.map(s => `<span class="source-badge">${escapeHtml(s.filename)} (p. ${s.page_number})</span>`).join("")}
                </div>
            `;
        }

        // Add latency indicator
        if (latencies) {
            htmlContent += `
                <div style="font-size: 0.75rem; color: var(--text-muted); text-align: right; margin-top: 0.5rem;">
                    Retrieval: ${latencies.retrieval_time}s | Inference: ${latencies.inference_time}s
                </div>
            `;
        }
        
        msgDiv.innerHTML = htmlContent;
    } else {
        msgDiv.classList.add("message-system");
        msgDiv.innerText = text;
    }

    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Render source details in citations side-panel
function renderCitations(sources, confidence, isFallback, strategy) {
    const panel = document.getElementById("citations-panel");

    if (isFallback) {
        panel.innerHTML = `
            <div class="alert-warning" style="margin-bottom: 1rem;">
                ⚠️ <strong>Fallback Activated</strong><br/>
                FAISS retrieval fell below similarity threshold. Query was answered using general knowledge.
            </div>
            <div class="stat-box" style="margin-bottom: 1rem;">
                <div class="stat-val" style="color: var(--yellow-warning);">0.00</div>
                <div class="stat-label">Confidence Score</div>
            </div>
        `;
        return;
    }

    if (!sources || sources.length === 0) {
        panel.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding-top: 3rem;">
                No sources cited for this query.
            </div>
        `;
        return;
    }

    // Set status text for confidence
    const statusColor = confidence >= 0.60 ? "var(--green-success)" : "var(--yellow-warning)";

    let html = `
        <div class="stat-box" style="margin-bottom: 1rem;">
            <div class="stat-val" style="color: ${statusColor};">${confidence.toFixed(2)}</div>
            <div class="stat-label">Confidence Score (Strategy: ${strategy.toUpperCase()})</div>
        </div>
        <h3>Retrieved References:</h3>
        <div style="display: flex; flex-direction: column; gap: 0.75rem; max-height: 350px; overflow-y: auto;">
    `;

    sources.forEach((src, idx) => {
        html += `
            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-light); border-radius: 8px; padding: 0.75rem;">
                <div style="font-weight: 600; font-size: 0.9rem; color: var(--accent-blue); margin-bottom: 0.25rem;">
                    [${idx + 1}] ${escapeHtml(src.filename)}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary);">
                    <span>Page: <strong>${src.page_number}</strong></span>
                    <span>Similarity: <strong>${src.similarity_score.toFixed(3)}</strong></span>
                </div>
            </div>
        `;
    });

    html += `</div>`;
    panel.innerHTML = html;
}

// Clear conversation history on client and server
async function clearHistory() {
    if (!confirm("Clear current conversation history?")) return;
    
    try {
        await fetch(`${API_BASE}/query/clear_history`, { method: "POST" }).catch(() => {});
    } catch(e) {}

    document.getElementById("chat-box").innerHTML = `
        <div class="message message-assistant">
            Conversation cleared. Ask me a question to start.
        </div>
    `;
    document.getElementById("citations-panel").innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding-top: 3rem;">
            Ask a question to see retrieved references.
        </div>
    `;
    lastQueryData = null;
}

// Export last answer as PDF or TXT
async function exportConversation(format) {
    if (!lastQueryData) {
        alert("Please run a query first before exporting.");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/query/export`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: lastQueryData.answer ? lastQueryData.sources ? lastQueryData.answer.split("Question:").pop() : "" : "", // we can grab query from lastQueryData
                question: document.querySelectorAll(".message-user")[document.querySelectorAll(".message-user").length - 1].innerText,
                answer: lastQueryData.answer,
                sources: lastQueryData.sources || [],
                format: format
            })
        });

        if (!response.ok) throw new Error("Export failed.");
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `medical_report_${Date.now()}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

    } catch (err) {
        alert(`Export failed: ${err.message}`);
    }
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
