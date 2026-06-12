/**
 * Literature Search Client Logic
 * ==============================
 */

const API_BASE = "";

async function executeSearch() {
    const queryInput = document.getElementById("search-input");
    const query = queryInput.value.trim();
    if (!query) return;

    const strategy = document.getElementById("strategy-select").value;
    const threshold = parseFloat(document.getElementById("threshold-input").value);
    const limit = parseInt(document.getElementById("limit-input").value);

    const btn = document.getElementById("search-btn");
    const loading = document.getElementById("loading");
    const resultsCard = document.getElementById("search-results-card");
    const container = document.getElementById("passages-container");
    const countSpan = document.getElementById("results-count");

    btn.disabled = true;
    loading.style.display = "flex";
    resultsCard.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query: query,
                strategy: strategy,
                threshold: threshold,
                limit: limit
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Search failed.");
        }

        const data = await response.json();
        const results = data.results || [];
        
        countSpan.innerText = `Found ${results.length} match(es) (Mode: ${data.retrieval_strategy.toUpperCase()})`;

        if (results.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No passages found meeting similarity threshold. Try reducing the threshold or keyword requirements.
                </div>
            `;
        } else {
            container.innerHTML = results.map((res, idx) => `
                <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-light); border-radius: 12px; padding: 1.5rem; position: relative;">
                    <!-- Top metadata -->
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-light); padding-bottom: 0.5rem; margin-bottom: 1rem;">
                        <span style="font-weight: 600; color: var(--accent-blue);">📄 ${escapeHtml(res.filename)} (Page ${res.page_number})</span>
                        <span style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); color: var(--green-success); font-size: 0.8rem; font-weight: 600; border-radius: 4px; padding: 0.2rem 0.5rem;">
                            Score: ${res.similarity_score.toFixed(4)}
                        </span>
                    </div>
                    
                    <!-- Content -->
                    <p style="font-size: 0.95rem; line-height: 1.6; color: var(--text-secondary); margin-bottom: 0.75rem; white-space: pre-wrap;">
                        ${escapeHtml(res.passage)}
                    </p>
                    
                    <!-- Bottom tags -->
                    <div style="display: flex; gap: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
                        <span>Category: <strong style="text-transform: uppercase;">${escapeHtml(res.disease_category)}</strong></span>
                    </div>
                </div>
            `).join("");
        }

        resultsCard.style.display = "block";

    } catch (err) {
        alert(`Error executing search: ${err.message}`);
    } finally {
        btn.disabled = false;
        loading.style.display = "none";
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
