// InfraGuard Application Controller

// Global App State
const state = {
    analyses: [],
    selectedAnalysisId: null,
    activeAnalysisData: null,
    cmdbFilePath: null,
    actualFilePath: null,
};

// DOM Elements
const elements = {
    auditForm: document.getElementById("audit-ingestion-form"),
    runNameInput: document.getElementById("audit-name-input"),
    cmdbInput: document.getElementById("cmdb-file-input"),
    actualInput: document.getElementById("actual-file-input"),
    cmdbDisplay: document.getElementById("cmdb-filename-display"),
    actualDisplay: document.getElementById("actual-filename-display"),
    startBtn: document.getElementById("start-reconciliation-btn"),
    spinner: document.getElementById("reconcile-spinner"),
    uploadStatus: document.getElementById("upload-status-message"),
    historyList: document.getElementById("analyses-history-list"),
    emptyState: document.getElementById("empty-state-view"),
    resultsView: document.getElementById("dashboard-results-view"),
    activeTitle: document.getElementById("active-audit-title"),
    activeMeta: document.getElementById("active-audit-meta"),
    downloadPdfBtn: document.getElementById("download-pdf-btn"),
    
    // Stats elements
    statsElems: {
        total: document.getElementById("stat-total-val"),
        high: document.getElementById("stat-high-val"),
        medium: document.getElementById("stat-medium-val"),
        low: document.getElementById("stat-low-val"),
    },
    
    // Patterns container
    patternsWarningBox: document.getElementById("patterns-warning-box"),
    patternsList: document.getElementById("patterns-list-container"),
    
    // Filters
    sevFilter: document.getElementById("severity-filter"),
    typeFilter: document.getElementById("type-filter"),
    
    // Table
    tableBody: document.getElementById("discrepancy-log-tbody"),
};

// Color mappings for visual charts
const COLORS = {
    High: "#ef4444",
    Medium: "#f59e0b",
    Low: "#10b981",
    missing: "#ec4899",
    untracked: "#3b82f6",
    naming_mismatch: "#a855f7",
    attribute_mismatch: "#06b6d4",
    duplicate: "#64748b",
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    setupEventListeners();
    fetchAuditHistory();
});

// Setup DOM Event Listeners
function setupEventListeners() {
    // File inputs name change display
    elements.cmdbInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        elements.cmdbDisplay.textContent = file ? file.name : "No file selected";
    });

    elements.actualInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        elements.actualDisplay.textContent = file ? file.name : "No file selected";
    });

    // Form submit
    elements.auditForm.addEventListener("submit", handleAuditSubmit);

    // Filters update
    elements.sevFilter.addEventListener("change", renderDiscrepanciesTable);
    elements.typeFilter.addEventListener("change", renderDiscrepanciesTable);

    // PDF download trigger
    elements.downloadPdfBtn.addEventListener("click", handleDownloadPdf);

    // Setup Chatbot
    setupChatbot();
}

// Fetch reconciliation runs list
async function fetchAuditHistory() {
    try {
        const res = await fetch("/api/analyses");
        if (!res.ok) throw new Error("Failed to fetch history.");
        state.analyses = await res.json();
        renderHistoryList();
    } catch (err) {
        console.error(err);
        elements.historyList.innerHTML = `<li class="loading-placeholder color-high">Error loading history: ${err.message}</li>`;
    }
}

// Render history sidebar list
function renderHistoryList() {
    if (state.analyses.length === 0) {
        elements.historyList.innerHTML = '<li class="loading-placeholder">No audit runs recorded.</li>';
        return;
    }

    elements.historyList.innerHTML = "";
    state.analyses.forEach((analysis) => {
        const li = document.createElement("li");
        li.dataset.id = analysis.id;
        if (state.selectedAnalysisId === analysis.id) {
            li.classList.add("active");
        }

        const dateStr = new Date(analysis.created_at).toLocaleString();
        const stats = analysis.summary_stats || {};
        
        li.innerHTML = `
            <div class="history-item-header">
                <span class="history-item-name">${escapeHtml(analysis.name)}</span>
                <span class="history-item-meta">${analysis.status}</span>
            </div>
            <div class="history-item-header" style="margin-top: 4px;">
                <span class="history-item-meta">${dateStr}</span>
                <span class="history-item-stats">
                    <span class="color-high">H:${stats.high_severity || 0}</span>
                    <span class="color-medium">M:${stats.medium_severity || 0}</span>
                    <span class="color-low">L:${stats.low_severity || 0}</span>
                </span>
            </div>
        `;

        li.addEventListener("click", () => selectAnalysis(analysis.id));
        elements.historyList.appendChild(li);
    });
}

// Handle single analysis click selection
async function selectAnalysis(id) {
    state.selectedAnalysisId = id;
    
    // Update active highlight classes in sidebar
    Array.from(elements.historyList.children).forEach((li) => {
        if (li.dataset.id === id) {
            li.classList.add("active");
        } else {
            li.classList.remove("active");
        }
    });

    try {
        const res = await fetch(`/api/analyses/${id}`);
        if (!res.ok) throw new Error("Failed to load audit run details.");
        
        const data = await res.json();
        state.activeAnalysisData = data;
        
        renderDashboardResults(data);
    } catch (err) {
        alert("Error loading reconciliation details: " + err.message);
    }
}

// Main Results Dashboard Render
function renderDashboardResults(data) {
    // Toggle displays
    elements.emptyState.classList.add("hidden");
    elements.resultsView.classList.remove("hidden");

    // Title and Meta
    elements.activeTitle.textContent = data.name;
    const dateStr = new Date(data.created_at).toLocaleString();
    elements.activeMeta.textContent = `Executed: ${dateStr} | CMDB Source: ${data.cmdb_file.split(/[\\/]/).pop()} | Actual Source: ${data.actual_file.split(/[\\/]/).pop()}`;

    // Update Stats counters
    const stats = data.summary_stats || {};
    elements.statsElems.total.textContent = stats.total_discrepancies || 0;
    elements.statsElems.high.textContent = stats.high_severity || 0;
    elements.statsElems.medium.textContent = stats.medium_severity || 0;
    elements.statsElems.low.textContent = stats.low_severity || 0;

    // Draw canvas charts
    renderCharts(stats);

    // Systematic Patterns Warnings
    const findings = stats.findings || [];
    if (findings.length === 0) {
        elements.patternsWarningBox.classList.add("hidden");
    } else {
        elements.patternsWarningBox.classList.remove("hidden");
        elements.patternsList.innerHTML = "";
        findings.forEach((find) => {
            const div = document.createElement("div");
            const sevLower = find.severity.toLowerCase();
            div.className = `pattern-item severity-${sevLower}`;
            div.innerHTML = `
                <div class="pattern-title-row">
                    <span class="pattern-title">${escapeHtml(find.title)}</span>
                    <span class="pattern-severity-badge ${sevLower}">${find.severity}</span>
                </div>
                <p class="pattern-desc">${escapeHtml(find.description)}</p>
            `;
            elements.patternsList.appendChild(div);
        });
    }

    // Render Discrepancies Table (resets filter selectors first)
    elements.sevFilter.value = "all";
    elements.typeFilter.value = "all";
    renderDiscrepanciesTable();
    
    // Fetch AI Executive Summary
    fetchAISummary(data.id);
}

// Discrepancy Table render with active filters
function renderDiscrepanciesTable() {
    if (!state.activeAnalysisData) return;

    const items = state.activeAnalysisData.discrepancies || [];
    const sevVal = elements.sevFilter.value;
    const typeVal = elements.typeFilter.value;

    elements.tableBody.innerHTML = "";

    const filtered = items.filter((item) => {
        const sevMatch = sevVal === "all" || item.severity === sevVal;
        const typeMatch = typeVal === "all" || item.type === typeVal;
        return sevMatch && typeMatch;
    });

    if (filtered.length === 0) {
        elements.tableBody.innerHTML = `
            <tr>
                <td colspan="4" class="loading-placeholder">No discrepancies matched current filter settings.</td>
            </tr>
        `;
        return;
    }

    filtered.forEach((item) => {
        const tr = document.createElement("tr");

        // Format ID column text
        const ids = [];
        if (item.external_id) ids.push(`<div><label>ID:</label>${escapeHtml(item.external_id)}</div>`);
        const host = item.hostname_actual || item.hostname_cmdb;
        if (host) ids.push(`<div><label>Host:</label>${escapeHtml(host)}</div>`);
        const ip = item.ip_actual || item.ip_cmdb;
        if (ip) ids.push(`<div><label>IP:</label>${escapeHtml(ip)}</div>`);
        const idHtml = ids.join("") || "N/A";

        // Badges
        const typeLabel = item.type.replace("_", " ");
        const sevLower = item.severity.toLowerCase();

        tr.innerHTML = `
            <td><span class="badge-type">${escapeHtml(typeLabel)}</span></td>
            <td><span class="badge-severity ${sevLower}">${item.severity}</span></td>
            <td><div class="asset-identifiers">${idHtml}</div></td>
            <td>
                <div class="observation-remediation">
                    <div class="obs-text">${escapeHtml(item.description)}</div>
                    <div class="rem-text"><b>Remediation Action:</b> ${escapeHtml(item.remediation)}</div>
                </div>
            </td>
        `;
        elements.tableBody.appendChild(tr);
    });
}

// API upload and analyze execution handler
async function handleAuditSubmit(e) {
    e.preventDefault();

    const name = elements.runNameInput.value.trim ? elements.runNameInput.value.trim() : elements.runNameInput.value;
    const cmdbFile = elements.cmdbInput.files[0];
    const actualFile = elements.actualInput.files[0];

    if (!name || !cmdbFile || !actualFile) {
        showStatus("Please specify run name and select both audit files.", "error");
        return;
    }

    // Toggle loading states
    elements.startBtn.disabled = true;
    elements.spinner.classList.remove("hidden");
    showStatus("Uploading CMDB Inventory file (Stage 1/3)...", "success");

    try {
        // Step 1: Upload CMDB
        const cmdbPath = await uploadFileApi(cmdbFile, "cmdb");
        
        showStatus("Uploading Actual discovery report (Stage 2/3)...", "success");
        // Step 2: Upload Actual
        const actualPath = await uploadFileApi(actualFile, "actual");

        showStatus("Analyzing and reconciling datasets (Stage 3/3)...", "success");
        // Step 3: Trigger Analyze API
        const analyzeRes = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                cmdb_file_path: cmdbPath,
                actual_file_path: actualPath,
            }),
        });

        if (!analyzeRes.ok) {
            const errBody = await analyzeRes.json();
            throw new Error(errBody.detail || "Analysis request failed.");
        }

        const auditResponse = await analyzeRes.json();
        
        // Reset form
        elements.auditForm.reset();
        elements.cmdbDisplay.textContent = "No file selected";
        elements.actualDisplay.textContent = "No file selected";
        
        showStatus("Reconciliation audit complete!", "success");
        setTimeout(() => elements.uploadStatus.classList.add("hidden"), 3000);

        // Fetch history and auto-select new item
        await fetchAuditHistory();
        if (auditResponse.analysis_id) {
            selectAnalysis(auditResponse.analysis_id);
        }

    } catch (err) {
        showStatus("Error running audit: " + err.message, "error");
    } finally {
        elements.startBtn.disabled = false;
        elements.spinner.classList.add("hidden");
    }
}

// Upload file helper calling multipart endpoint
async function uploadFileApi(file, fileType) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType);

    const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const errBody = await res.json();
        throw new Error(errBody.detail || `Upload failed for ${file.name}`);
    }

    const data = await res.json();
    return data.saved_filepath;
}

// PDF download handler
function handleDownloadPdf() {
    if (!state.selectedAnalysisId) return;
    const url = `/api/reports/${state.selectedAnalysisId}/download.pdf`;
    const a = document.createElement("a");
    a.href = url;
    a.download = `InfraGuard_Report_${state.selectedAnalysisId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Status banners display controller
function showStatus(msg, type) {
    elements.uploadStatus.textContent = msg;
    elements.uploadStatus.className = `status-msg ${type}`;
    elements.uploadStatus.classList.remove("hidden");
}

// Canvas Pie Chart rendering
function renderCharts(stats) {
    // 1. Draw Type Chart
    const typeSegments = [
        { label: "Missing", value: stats.missing || 0, color: COLORS.missing },
        { label: "Untracked", value: stats.untracked || 0, color: COLORS.untracked },
        { label: "Naming", value: stats.naming_mismatch || 0, color: COLORS.naming_mismatch },
        { label: "Attribute", value: stats.attribute_mismatch || 0, color: COLORS.attribute_mismatch },
        { label: "Duplicate", value: stats.duplicate || 0, color: COLORS.duplicate },
    ];
    drawDoughnutChart("type-chart-canvas", typeSegments);
    populateLegend("chart-legend-container", typeSegments);

    // 2. Draw Severity Chart
    const sevSegments = [
        { label: "High", value: stats.high_severity || 0, color: COLORS.High },
        { label: "Medium", value: stats.medium_severity || 0, color: COLORS.Medium },
        { label: "Low", value: stats.low_severity || 0, color: COLORS.Low },
    ];
    drawDoughnutChart("severity-chart-canvas", sevSegments);
    populateLegend("sev-legend-container", sevSegments);
}

// Canvas Drawing Utility
function drawDoughnutChart(canvasId, segments) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    // Support retina displays/scaling
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(cx, cy) - 10;

    const total = segments.reduce((sum, s) => sum + s.value, 0);

    if (total === 0) {
        // Draw empty indicator state
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
        ctx.fillStyle = "#334155";
        ctx.fill();
        ctx.closePath();
        
        ctx.beginPath();
        ctx.arc(cx, cy, radius * 0.6, 0, 2 * Math.PI);
        ctx.fillStyle = "#1e293b"; // inner circle
        ctx.fill();
        ctx.closePath();
        return;
    }

    let startAngle = -Math.PI / 2; // start at 12 o'clock
    segments.forEach((slice) => {
        if (slice.value === 0) return;
        const sliceAngle = (slice.value / total) * 2 * Math.PI;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
        ctx.fillStyle = slice.color;
        ctx.fill();
        ctx.closePath();

        startAngle += sliceAngle;
    });

    // Draw inner cutout circle to create Doughnut effect
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.65, 0, 2 * Math.PI);
    ctx.fillStyle = "#1e293b";
    ctx.fill();
    ctx.closePath();
}

// Render dynamic legends in HTML
function populateLegend(containerId, segments) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    
    segments.forEach((s) => {
        const item = document.createElement("div");
        item.className = "legend-item";
        item.innerHTML = `
            <span class="legend-color" style="background-color: ${s.color}"></span>
            <span>${s.label} (${s.value})</span>
        `;
        container.appendChild(item);
    });
}

// XSS Sanitizer Helper
function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Fetch AI Executive Summary
async function fetchAISummary(analysisId) {
    const summaryContent = document.getElementById("ai-summary-content");
    // Show shimmer
    summaryContent.innerHTML = `
        <div class="shimmer-placeholder"></div>
        <div class="shimmer-placeholder w-80"></div>
        <div class="shimmer-placeholder w-90"></div>
    `;

    try {
        const res = await fetch(`/api/agent/summary/${analysisId}`);
        if (!res.ok) throw new Error("Failed to load AI summary");
        const data = await res.json();
        
        // Render markdown-like summary
        if (typeof marked !== 'undefined') {
            summaryContent.innerHTML = marked.parse(data.summary);
        } else {
            summaryContent.innerHTML = data.summary.replace(/\n/g, '<br/>');
        }
    } catch (err) {
        summaryContent.innerHTML = `<span class="color-high" style="color: #ef4444;">AI Summary unavailable: ${err.message}</span>`;
    }
}

// Chatbot Logic
function setupChatbot() {
    const toggleBtn = document.getElementById("chatbot-toggle-btn");
    const closeBtn = document.getElementById("chatbot-close-btn");
    const panel = document.getElementById("chatbot-panel");
    const sendBtn = document.getElementById("chatbot-send-btn");
    const input = document.getElementById("chatbot-input");
    const messagesContainer = document.getElementById("chatbot-messages");

    let chatHistory = [];

    toggleBtn.addEventListener("click", () => {
        panel.classList.remove("hidden");
        input.focus();
    });

    closeBtn.addEventListener("click", () => {
        panel.classList.add("hidden");
    });

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Add user message
        addMessage(text, "user");
        chatHistory.push({ role: "user", content: text });
        input.value = "";

        // Show typing indicator
        const typingId = showTypingIndicator();

        try {
            let messagesToSend = [];
            
            const summaryElement = document.getElementById('ai-summary-content');
            const sysInstruction = "CRITICAL INSTRUCTION: You MUST ONLY respond with a valid JSON object. Do not output conversational text outside the JSON. Format exactly like this: { \"answer\": \"Your detailed markdown-formatted response to the user.\", \"options\": [\"Follow up option 1\", \"Follow up option 2\"] }";

            if (summaryElement && summaryElement.innerText && !summaryElement.innerText.includes('AI Summary unavailable') && summaryElement.innerText.trim() !== '') {
                messagesToSend.push({
                    role: "system",
                    content: "You are the InfraGuard Security Assistant. The user just ran an infrastructure audit. Here is the executive summary of the audit: " + summaryElement.innerText + "\n\n" + sysInstruction
                });
            } else {
                messagesToSend.push({
                    role: "system",
                    content: "You are the InfraGuard Security Assistant. Help the user manage their infrastructure. " + sysInstruction
                });
            }
            
            messagesToSend = messagesToSend.concat(chatHistory);

            const payload = {
                messages: messagesToSend,
                model: "gemini-flash-lite-latest"
            };

            const res = await fetch('/api/chat/', { 
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            removeTypingIndicator(typingId);
            
            let replyText;
            if (!res.ok) {
                if (data.detail && data.detail.includes("429")) {
                    replyText = "Oops, I'm currently rate-limited by the Gemini free tier. Please wait about 1 minute and try again!";
                } else {
                    replyText = data.detail || "Sorry, I encountered an error on the server.";
                }
            } else {
                replyText = data.output || "Sorry, I didn't get that.";
            }
            
            addMessage(replyText, "system");
            chatHistory.push({ role: "assistant", content: replyText });
        } catch (err) {
            removeTypingIndicator(typingId);
            addMessage("Connection error to AI.", "system");
        }
    }

    function addMessage(text, sender) {
        const div = document.createElement("div");
        div.className = `message ${sender}`;

        if (sender === "system") {
            try {
                let cleanedText = text.trim();
                // Strip markdown json formatting if Gemini includes it
                if (cleanedText.startsWith("```json")) {
                    cleanedText = cleanedText.replace(/```json/g, "").replace(/```/g, "").trim();
                } else if (cleanedText.startsWith("```")) {
                    cleanedText = cleanedText.replace(/```/g, "").trim();
                }

                if (cleanedText.startsWith("{") && cleanedText.endsWith("}")) {
                    const parsed = JSON.parse(cleanedText);
                    if (parsed.answer || parsed.options) {
                        if (parsed.answer) {
                            div.innerHTML = typeof marked !== 'undefined' ? marked.parse(parsed.answer) : escapeHtml(parsed.answer).replace(/\n/g, "<br>");
                        } else {
                            div.innerHTML = "";
                        }
                        
                        if (Array.isArray(parsed.options) && parsed.options.length > 0) {
                            const optsDiv = document.createElement("div");
                            optsDiv.className = "options-container";
                            optsDiv.style.marginTop = "10px";
                            parsed.options.forEach(opt => {
                                const btn = document.createElement("button");
                                btn.className = "chatbot-option-chip";
                                btn.innerText = opt;
                                btn.onclick = () => {
                                    document.getElementById("chatbot-input").value = opt;
                                    sendMessage();
                                };
                                optsDiv.appendChild(btn);
                            });
                            div.appendChild(optsDiv);
                        }
                        messagesContainer.appendChild(div);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        return;
                    }
                }

                if (cleanedText.startsWith("[") && cleanedText.endsWith("]")) {
                    const options = JSON.parse(cleanedText);
                    if (Array.isArray(options) && options.length > 0) {
                        div.className = "options-container";
                        options.forEach(opt => {
                            const btn = document.createElement("button");
                            btn.className = "chatbot-option-chip";
                            btn.innerText = opt;
                            btn.onclick = () => {
                                document.getElementById("chatbot-input").value = opt;
                                sendMessage();
                            };
                            div.appendChild(btn);
                        });
                        messagesContainer.appendChild(div);
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        return;
                    }
                }
            } catch (e) {
                console.error("Failed to parse AI response as options:", e);
                // Fallback to normal text
            }
        }

        div.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
        messagesContainer.appendChild(div);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function showTypingIndicator() {
        const id = "typing-" + Date.now();
        const div = document.createElement("div");
        div.className = "typing-indicator";
        div.id = id;
        div.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;
        messagesContainer.appendChild(div);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return id;
    }

    function removeTypingIndicator(id) {
        const div = document.getElementById(id);
        if (div) div.remove();
    }
}
