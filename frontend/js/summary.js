/**
 * Medical Research Summarizer Logic
 * =================================
 */

const API_BASE = "";
let lastSummaryData = null; // store last summary for exporter

async function generateSummary() {
    const input = document.getElementById("topic-input");
    const topic = input.value.trim();
    if (!topic) return;

    const btn = document.getElementById("generate-btn");
    const loading = document.getElementById("loading");
    const outputDiv = document.getElementById("summary-result");
    const exportControls = document.getElementById("export-controls");

    btn.disabled = true;
    loading.style.display = "flex";
    outputDiv.style.display = "none";
    exportControls.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/summary`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: topic })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Summary generation failed.");
        }

        const data = await response.json();
        lastSummaryData = data; // store for download

        // Populate elements
        document.getElementById("summary-title").innerText = `Research Summary: ${escapeHtml(data.topic)}`;
        document.getElementById("sum-overview").innerHTML = formatBody(data.overview);
        document.getElementById("sum-findings").innerHTML = formatBody(data.key_findings);
        document.getElementById("sum-risks").innerHTML = formatBody(data.risk_factors);
        document.getElementById("sum-treatments").innerHTML = formatBody(data.treatments);
        document.getElementById("sum-gaps").innerHTML = formatBody(data.research_gaps);
        document.getElementById("sum-directions").innerHTML = formatBody(data.future_directions);

        // Display results
        outputDiv.style.display = "block";
        exportControls.style.display = "flex";

    } catch (err) {
        alert(`Error: ${err.message}`);
    } finally {
        btn.disabled = false;
        loading.style.display = "none";
    }
}

// Convert plain markdown lists or newlines to styled HTML
function formatBody(text) {
    if (!text) return "Information unavailable.";
    
    // Check if it is list-like
    const lines = text.split("\n").map(l => l.trim()).filter(l => l.length > 0);
    const listItems = lines.filter(l => l.startsWith("*") || l.startsWith("-") || /^\d+\./.test(l));

    if (listItems.length > 1) {
        return `<ul>${lines.map(line => {
            const clean = line.replace(/^[\*\-\d\.]+\s*/, "");
            return `<li>${escapeHtml(clean)}</li>`;
        }).join("")}</ul>`;
    }

    return escapeHtml(text).replace(/\n/g, "<br/>");
}

// Export summary endpoint
async function exportSummary(format) {
    if (!lastSummaryData) return;

    try {
        const response = await fetch(`${API_BASE}/summary/export`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topic: lastSummaryData.topic,
                overview: lastSummaryData.overview,
                key_findings: lastSummaryData.key_findings,
                risk_factors: lastSummaryData.risk_factors,
                treatments: lastSummaryData.treatments,
                research_gaps: lastSummaryData.research_gaps,
                future_directions: lastSummaryData.future_directions,
                format: format
            })
        });

        if (!response.ok) throw new Error("Export failed.");
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `summary_${lastSummaryData.topic.replace(/\s+/g, "_")}.${format}`;
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
