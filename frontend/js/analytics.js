/**
 * Analytics Dashboard client logic
 * =================================
 */

const API_BASE = "";

document.addEventListener("DOMContentLoaded", () => {
    loadAnalytics();
});

async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/analytics`);
        if (!response.ok) throw new Error("Failed to load analytics data.");

        const data = await response.json();

        // Update indicators
        document.getElementById("stat-total-queries").innerText = data.total_queries;
        document.getElementById("stat-retrieval-lat").innerText = `${data.avg_retrieval_time.toFixed(3)}s`;
        document.getElementById("stat-total-lat").innerText = `${data.avg_response_time.toFixed(3)}s`;
        document.getElementById("stat-success-rate").innerText = `${data.retrieval_success_rate}%`;

        // Update listings
        renderRefDocuments(data.most_referenced_documents);
        renderTopics(data.most_asked_topics);

        // Setup charts
        if (typeof Chart !== "undefined" && data.total_queries > 0) {
            setupLatencyChart(data.avg_retrieval_time, data.avg_response_time);
            setupStrategyChart(data.strategy_distribution);
        } else {
            console.log("[INFO] Chart.js was not loaded or query log is empty. Skipping chart rendering.");
        }

    } catch (err) {
        console.error("Analytics load error:", err);
    }
}

// Render referenced files table
function renderRefDocuments(docs) {
    const container = document.getElementById("ref-docs-list");
    if (!docs || docs.length === 0) {
        container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No reference history logged yet.</div>`;
        return;
    }

    container.innerHTML = `
        <table class="med-table" style="font-size: 0.9rem;">
            <thead>
                <tr>
                    <th>Document</th>
                    <th style="width: 80px; text-align: right;">Citations</th>
                </tr>
            </thead>
            <tbody>
                ${docs.map(doc => `
                    <tr>
                        <td style="font-weight: 500;">📄 ${escapeHtml(doc.filename)}</td>
                        <td style="text-align: right; font-weight: 600; color: var(--accent-blue);">${doc.count}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

// Render topics list
function renderTopics(topics) {
    const container = document.getElementById("topics-list");
    if (!topics || topics.length === 0) {
        container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 2rem;">No topic search history logged yet.</div>`;
        return;
    }

    container.innerHTML = topics.map((t, idx) => `
        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-light); border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;">
            <span style="font-weight: 600; text-transform: capitalize;">#${idx + 1} ${escapeHtml(t.topic)}</span>
            <span style="background: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.2); color: var(--accent-purple); font-size: 0.8rem; font-weight: 600; border-radius: 4px; padding: 0.2rem 0.5rem;">
                ${t.count} queries
            </span>
        </div>
    `).join("");
}

// Draw charts
let latencyChartInstance = null;
function setupLatencyChart(avgRetrieval, avgResponse) {
    const ctx = document.getElementById("latencyChart").getContext("2d");
    if (latencyChartInstance) latencyChartInstance.destroy();

    latencyChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Retrieval Latency", "Model Generation Latency"],
            datasets: [{
                label: "Latency (seconds)",
                data: [avgRetrieval, Math.max(avgResponse - avgRetrieval, 0.01)],
                backgroundColor: [
                    "rgba(59, 130, 246, 0.6)",   // blue
                    "rgba(139, 92, 246, 0.6)"    // purple
                ],
                borderColor: [
                    "rgba(59, 130, 246, 1)",
                    "rgba(139, 92, 246, 1)"
                ],
                borderWidth: 1.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#9CA3AF" }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: "#9CA3AF" }
                }
            }
        }
    });
}

let strategyChartInstance = null;
function setupStrategyChart(strategyDist) {
    const ctx = document.getElementById("strategyChart").getContext("2d");
    if (strategyChartInstance) strategyChartInstance.destroy();

    const labels = Object.keys(strategyDist);
    const data = Object.values(strategyDist);

    strategyChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels.map(l => l.toUpperCase()),
            datasets: [{
                data: data,
                backgroundColor: [
                    "rgba(59, 130, 246, 0.6)",   // blue
                    "rgba(16, 185, 129, 0.6)",   // green
                    "rgba(245, 158, 11, 0.6)"    // orange
                ],
                borderColor: [
                    "rgba(59, 130, 246, 1)",
                    "rgba(16, 185, 129, 1)",
                    "rgba(245, 158, 11, 1)"
                ],
                borderWidth: 1.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: "#9CA3AF", boxWidth: 15 }
                }
            }
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
