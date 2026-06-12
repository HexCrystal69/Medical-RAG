/**
 * Evaluation Center Client Logic
 * ==============================
 */

const API_BASE = "";
let preparedQuestions = []; // stores generated questions
let activeRunId = null;

document.addEventListener("DOMContentLoaded", () => {
    loadHistory();
});

// Load runs log
async function loadHistory() {
    const listBody = document.getElementById("history-body");
    try {
        const response = await fetch(`${API_BASE}/evaluate/history`);
        if (!response.ok) throw new Error("Failed to fetch history.");

        const runs = await response.json();
        if (runs.length === 0) {
            listBody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                        No evaluation history available. Run checks above.
                    </td>
                </tr>
            `;
            return;
        }

        listBody.innerHTML = runs.map(run => `
            <tr style="cursor: pointer;" onclick="showRunDetails('${run.run_id}')">
                <td style="font-weight: 500;">⏱ ${run.timestamp}</td>
                <td style="font-weight: 700; color: var(--accent-blue);">${run.overall_score.toFixed(3)}</td>
                <td>${run.metrics.faithfulness.toFixed(3)}</td>
                <td>${run.metrics.answer_relevancy.toFixed(3)}</td>
                <td>${run.metrics.context_precision.toFixed(3)}</td>
                <td>${run.metrics.context_recall.toFixed(3)}</td>
                <td>
                    <button class="btn btn-secondary" onclick="event.stopPropagation(); downloadReport('${run.run_id}', 'txt')" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;">TXT</button>
                    <button class="btn btn-secondary" onclick="event.stopPropagation(); downloadReport('${run.run_id}', 'pdf')" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;">PDF</button>
                </td>
            </tr>
        `).reverse().join("");

    } catch (err) {
        listBody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; color: var(--red-danger); padding: 1.5rem;">
                    Error loading history: ${err.message}
                </td>
            </tr>
        `;
    }
}

// Step 1: Generate questions from database chunks
async function generateBenchmarkQuestions() {
    const sizeInput = document.getElementById("test-size-input");
    const count = parseInt(sizeInput.value) || 3;

    const btn = document.getElementById("gen-questions-btn");
    const runBtn = document.getElementById("run-eval-btn");
    const loading = document.getElementById("loading");
    const statusText = document.getElementById("loading-status-text");
    const casesCard = document.getElementById("test-cases-card");
    const casesBody = document.getElementById("test-cases-body");

    btn.disabled = true;
    runBtn.disabled = true;
    loading.style.display = "flex";
    statusText.innerText = `Scanning vector space and drafting ${count} clinical queries...`;
    casesCard.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/evaluate/generate-questions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ questions_count: count })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Test set generation failed.");
        }

        const data = await response.json();
        preparedQuestions = data.questions || [];

        if (preparedQuestions.length === 0) {
            alert("No questions were generated. Make sure you have uploaded and indexed PDFs.");
            return;
        }

        casesBody.innerHTML = preparedQuestions.map((q, idx) => `
            <tr>
                <td style="font-weight: 600;">${idx + 1}</td>
                <td style="font-style: italic;">"${escapeHtml(q.question)}"</td>
                <td style="color: var(--text-secondary); font-size: 0.95rem;">📄 ${escapeHtml(q.filename)} (page ${q.page_number})</td>
            </tr>
        `).join("");

        casesCard.style.display = "block";
        runBtn.disabled = false; // enable step 2

    } catch (err) {
        alert(`Error generating test cases: ${err.message}`);
    } finally {
        btn.disabled = false;
        loading.style.display = "none";
    }
}

// Step 2: Run benchmark checks
async function runBenchmark() {
    if (preparedQuestions.length === 0) return;

    const runBtn = document.getElementById("run-eval-btn");
    const loading = document.getElementById("loading");
    const statusText = document.getElementById("loading-status-text");
    const summaryCard = document.getElementById("eval-summary-card");

    runBtn.disabled = true;
    loading.style.display = "flex";
    statusText.innerText = "Executing RAG pipeline and scoring outputs on local Qwen3 model (takes approx 15-30s per case)...";
    summaryCard.style.display = "none";

    try {
        const response = await fetch(`${API_BASE}/evaluate/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(preparedQuestions)
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Quality evaluation failed.");
        }

        const run = await response.json();
        activeRunId = run.run_id;

        // Render summary indicators
        document.getElementById("eval-overall").innerText = run.overall_score.toFixed(3);
        document.getElementById("eval-faithfulness").innerText = run.metrics.faithfulness.toFixed(3);
        document.getElementById("eval-relevancy").innerText = run.metrics.answer_relevancy.toFixed(3);
        document.getElementById("eval-precision").innerText = run.metrics.context_precision.toFixed(3);
        document.getElementById("eval-recall").innerText = run.metrics.context_recall.toFixed(3);

        // Bind export actions
        document.getElementById("export-txt-btn").onclick = () => downloadReport(run.run_id, "txt");
        document.getElementById("export-pdf-btn").onclick = () => downloadReport(run.run_id, "pdf");

        // Render detailed test case boxes
        renderRunDetails(run.queries);

        summaryCard.style.display = "block";
        await loadHistory(); // refresh list

    } catch (err) {
        alert(`Error executing RAGAS checks: ${err.message}`);
    } finally {
        loading.style.display = "none";
    }
}

// Display queries details on run click
async function showRunDetails(runId) {
    try {
        const response = await fetch(`${API_BASE}/evaluate/history`);
        const history = await response.json();
        const run = history.find(r => r.run_id === runId);
        if (!run) return;

        activeRunId = run.run_id;

        // Update stats
        document.getElementById("eval-overall").innerText = run.overall_score.toFixed(3);
        document.getElementById("eval-faithfulness").innerText = run.metrics.faithfulness.toFixed(3);
        document.getElementById("eval-relevancy").innerText = run.metrics.answer_relevancy.toFixed(3);
        document.getElementById("eval-precision").innerText = run.metrics.context_precision.toFixed(3);
        document.getElementById("eval-recall").innerText = run.metrics.context_recall.toFixed(3);

        // Bind export actions
        document.getElementById("export-txt-btn").onclick = () => downloadReport(run.run_id, "txt");
        document.getElementById("export-pdf-btn").onclick = () => downloadReport(run.run_id, "pdf");

        renderRunDetails(run.queries);
        
        const card = document.getElementById("eval-summary-card");
        card.style.display = "block";
        card.scrollIntoView({ behavior: "smooth" });

    } catch(err) {
        alert(`Error showing run details: ${err.message}`);
    }
}

// Render query boxes in UI
function renderRunDetails(queries) {
    const container = document.getElementById("eval-details-container");
    container.innerHTML = "<h3>Detailed Test Cases Scores:</h3>";

    queries.forEach((q, idx) => {
        container.innerHTML += `
            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-light); border-radius: 12px; padding: 1.5rem;">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.5rem; color: var(--accent-blue);">
                    Test Case ${idx + 1}: ${escapeHtml(q.question)}
                </div>
                
                <div style="margin-bottom: 1rem; font-size: 0.95rem; line-height: 1.5;">
                    <strong>Pipeline Answer:</strong><br/>
                    <span style="color: var(--text-secondary);">${escapeHtml(q.answer).replace(/\n/g, "<br/>")}</span>
                </div>
                
                <div style="margin-bottom: 1.25rem; font-size: 0.95rem; line-height: 1.5; padding-left: 0.75rem; border-left: 2px solid var(--text-muted);">
                    <strong>Ground Truth Chunk:</strong><br/>
                    <span style="color: var(--text-muted);">${escapeHtml(q.ground_truth)}</span>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 0.75rem;">
                    <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; text-align: center; border-radius: 6px; border: 1px solid rgba(59, 130, 246, 0.15);">
                        <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-blue);">${q.metrics.faithfulness.toFixed(2)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Faithfulness</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; text-align: center; border-radius: 6px; border: 1px solid rgba(139, 92, 246, 0.15);">
                        <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-purple);">${q.metrics.answer_relevancy.toFixed(2)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Relevancy</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; text-align: center; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.15);">
                        <div style="font-size: 1.1rem; font-weight: 700; color: var(--green-success);">${q.metrics.context_precision.toFixed(2)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Precision</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); padding: 0.5rem; text-align: center; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.15);">
                        <div style="font-size: 1.1rem; font-weight: 700; color: var(--yellow-warning);">${q.metrics.context_recall.toFixed(2)}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Recall</div>
                    </div>
                </div>
            </div>
        `;
    });
}

// Download report
async function downloadReport(runId, format) {
    try {
        const response = await fetch(`${API_BASE}/evaluate/export`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ run_id: runId, format: format })
        });

        if (!response.ok) throw new Error("Report export failed.");

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `eval_report_${runId}.${format}`;
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
