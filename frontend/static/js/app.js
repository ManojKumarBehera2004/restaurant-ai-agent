/**
 * Restaurant AI Agent Frontend Application Logic.
 */

const API_BASE = "";
let currentSessionId = "session_" + Math.random().toString(36).substring(2, 9);
let isOutageSimulated = false;

// DOM Elements
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initChat();
    initHealthAndOutage();
    loadOrders();
    loadTickets();
});

// ---------------------------------------------------------
// Navigation & Tab Management
// ---------------------------------------------------------
function initNavigation() {
    const tabs = document.querySelectorAll(".nav-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

            tab.classList.add("active");
            const targetId = tab.getAttribute("data-tab");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
            }

            // Auto-refresh view data on tab select
            if (targetId === "view-orders") loadOrders();
            if (targetId === "view-tickets") loadTickets();
            if (targetId === "view-logs") loadLogs();
        });
    });
}

// ---------------------------------------------------------
// Health & Outage Simulation Toggle
// ---------------------------------------------------------
async function initHealthAndOutage() {
    const outageBtn = document.getElementById("outageToggleBtn");
    
    async function checkHealth() {
        try {
            const res = await fetch(`${API_BASE}/api/health`);
            const data = await res.json();
            document.getElementById("llmProviderBadge").textContent = `LLM: ${data.llm_provider.toUpperCase()} (${data.llm_model})`;
            document.getElementById("ragStatusBadge").textContent = `RAG: ${data.vector_store_status}`;
            
            isOutageSimulated = data.order_outage_simulation_active;
            updateOutageButtonState();
        } catch (e) {
            console.error("Health check error:", e);
        }
    }

    function updateOutageButtonState() {
        if (isOutageSimulated) {
            outageBtn.classList.add("active");
            outageBtn.textContent = "⚠️ Order API Outage: ACTIVE (Click to Restore)";
        } else {
            outageBtn.classList.remove("active");
            outageBtn.textContent = "⚡ Simulate Order API Outage";
        }
    }

    outageBtn.addEventListener("click", async () => {
        isOutageSimulated = !isOutageSimulated;
        try {
            await fetch(`${API_BASE}/api/debug/simulate-outage`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ simulate_order_service_outage: isOutageSimulated })
            });
            updateOutageButtonState();
            appendSystemMessage(isOutageSimulated ? 
                "⚠️ Diagnostic Mode: Simulated Order API Outage is now ENABLED. Order queries will experience mock 503 failures." :
                "✅ Diagnostic Mode: Simulated Order API Outage is now RESTORED to normal healthy state."
            );
        } catch (e) {
            console.error("Failed to toggle outage:", e);
        }
    });

    checkHealth();
}

// ---------------------------------------------------------
// Chat Interaction
// ---------------------------------------------------------
function initChat() {
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const clearBtn = document.getElementById("clearChatBtn");

    // Quick scenario buttons
    document.querySelectorAll(".scenario-card").forEach(card => {
        card.addEventListener("click", () => {
            const prompt = card.getAttribute("data-prompt");
            if (prompt) {
                chatInput.value = prompt;
                sendMessage(prompt);
            }
        });
    });

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (text) {
            sendMessage(text);
            chatInput.value = "";
        }
    });

    if (clearBtn) {
        clearBtn.addEventListener("click", async () => {
            await fetch(`${API_BASE}/api/agent/reset/${currentSessionId}`, { method: "POST" });
            const messagesContainer = document.getElementById("chatMessages");
            messagesContainer.innerHTML = "";
            appendSystemMessage("Conversation session reset. Memory cleared.");
        });
    }
}

async function sendMessage(text) {
    const messagesContainer = document.getElementById("chatMessages");
    
    // Append User Message
    appendMessage("user", text);

    // Show typing placeholder
    const typingId = "typing-" + Date.now();
    const typingDiv = document.createElement("div");
    typingDiv.className = "message assistant";
    typingDiv.id = typingId;
    typingDiv.innerHTML = `
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
            <div class="msg-bubble">Thinking and reasoning over tools & policies...</div>
        </div>
    `;
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await fetch(`${API_BASE}/api/agent/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                session_id: currentSessionId,
                customer_id: "CUST-001"
            })
        });

        const data = await response.json();
        
        // Remove typing indicator
        const el = document.getElementById(typingId);
        if (el) el.remove();

        // Append Assistant Response
        appendAssistantResponse(data);
    } catch (err) {
        const el = document.getElementById(typingId);
        if (el) el.remove();
        appendMessage("assistant", `An error occurred while communicating with the agent: ${err.message}`);
    }
}

function appendMessage(role, text) {
    const messagesContainer = document.getElementById("chatMessages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;
    const avatar = role === "user" ? "👤" : "🤖";
    
    msgDiv.innerHTML = `
        <div class="msg-avatar">${avatar}</div>
        <div class="msg-body">
            <div class="msg-bubble">${formatMarkdown(text)}</div>
            <div class="msg-meta">${new Date().toLocaleTimeString()}</div>
        </div>
    `;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendAssistantResponse(data) {
    const messagesContainer = document.getElementById("chatMessages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message assistant`;

    let toolBadgesHtml = "";
    if (data.tool_calls && data.tool_calls.length > 0) {
        data.tool_calls.forEach(t => {
            const statusIcon = t.success ? "✅" : "⚠️";
            toolBadgesHtml += `
                <div class="tool-call-banner">
                    <span>${statusIcon} <strong>Tool:</strong> <code>${t.tool_name}</code> (${JSON.stringify(t.arguments)})</span>
                    <span>${t.execution_time_ms}ms</span>
                </div>
            `;
        });
    }

    let ragBadgesHtml = "";
    if (data.rag_sources && data.rag_sources.length > 0) {
        ragBadgesHtml += `
            <div class="rag-sources-banner">
                <strong>📚 Retrieved Policy Sources:</strong>
                <ul style="margin-left: 16px; margin-top: 4px;">
                    ${data.rag_sources.map(s => `<li>${s.title} (Relevance: ${(s.similarity_score * 100).toFixed(1)}%)</li>`).join("")}
                </ul>
            </div>
        `;
    }

    let ticketHtml = "";
    if (data.created_ticket) {
        const t = data.created_ticket;
        ticketHtml += `
            <div class="ticket-created-card">
                <div style="font-weight: 700; color: #fbbf24; margin-bottom: 4px;">🎫 Support Ticket Created: ${t.id}</div>
                <div><strong>Category:</strong> ${t.category} | <strong>Priority:</strong> ${t.priority} | <strong>Status:</strong> ${t.status}</div>
                <div><strong>Summary:</strong> ${t.issue_summary}</div>
            </div>
        `;
    }

    const securityIndicator = data.security_flag ? `<span style="color: #f87171; font-weight: bold;">[🛡️ Security Guardrail Active]</span> ` : "";

    msgDiv.innerHTML = `
        <div class="msg-avatar">🤖</div>
        <div class="msg-body">
            <div class="msg-bubble">
                ${securityIndicator}
                ${formatMarkdown(data.reply)}
                ${toolBadgesHtml}
                ${ragBadgesHtml}
                ${ticketHtml}
            </div>
            <div class="msg-meta">
                <span>⏱️ ${data.execution_time_ms}ms</span>
                <span>🎯 Intent: ${data.intent || 'GENERAL'}</span>
                <span>🔤 ~${data.token_usage_estimate} tokens</span>
            </div>
        </div>
    `;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function appendSystemMessage(text) {
    const messagesContainer = document.getElementById("chatMessages");
    const div = document.createElement("div");
    div.style.cssText = "text-align: center; font-size: 12px; color: var(--text-muted); margin: 8px 0;";
    div.innerHTML = `<em>${text}</em>`;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ---------------------------------------------------------
// Data Fetchers for Explorer Views
// ---------------------------------------------------------
async function loadOrders() {
    const tableBody = document.getElementById("ordersTableBody");
    if (!tableBody) return;
    tableBody.innerHTML = "<tr><td colspan='7'>Loading operational orders...</td></tr>";

    try {
        const res = await fetch(`${API_BASE}/api/orders`);
        const orders = await res.json();
        
        tableBody.innerHTML = orders.map(o => `
            <tr>
                <td><strong>${o.id}</strong></td>
                <td>${o.customer_name}</td>
                <td><span class="badge ${getStatusBadgeClass(o.status)}">${o.status}</span></td>
                <td>${o.items.map(i => `${i.quantity}x ${i.name}`).join(", ")}</td>
                <td>$${o.total.toFixed(2)}</td>
                <td>${o.delivery_partner || 'N/A'}</td>
                <td>${o.can_cancel ? '✅ Yes' : '❌ No'}</td>
            </tr>
        `).join("");
    } catch (e) {
        tableBody.innerHTML = `<tr><td colspan='7' style='color: #f87171;'>Failed to load orders: ${e.message}</td></tr>`;
    }
}

async function loadTickets() {
    const tableBody = document.getElementById("ticketsTableBody");
    if (!tableBody) return;
    tableBody.innerHTML = "<tr><td colspan='7'>Loading support tickets...</td></tr>";

    try {
        const res = await fetch(`${API_BASE}/api/support/tickets`);
        const tickets = await res.json();

        if (tickets.length === 0) {
            tableBody.innerHTML = "<tr><td colspan='7'>No support tickets found.</td></tr>";
            return;
        }

        tableBody.innerHTML = tickets.map(t => `
            <tr>
                <td><strong>${t.id}</strong></td>
                <td><span class="badge badge-yellow">${t.category}</span></td>
                <td><span class="badge ${getPriorityBadgeClass(t.priority)}">${t.priority}</span></td>
                <td>${t.sentiment}</td>
                <td>${t.issue_summary}</td>
                <td>${t.order_id || 'None'}</td>
                <td><span class="badge badge-blue">${t.status}</span></td>
            </tr>
        `).join("");
    } catch (e) {
        tableBody.innerHTML = `<tr><td colspan='7' style='color: #f87171;'>Failed to load tickets: ${e.message}</td></tr>`;
    }
}

async function loadLogs() {
    const container = document.getElementById("logsContainer");
    if (!container) return;
    container.innerHTML = "Loading observability traces...";

    try {
        const res = await fetch(`${API_BASE}/api/observability/logs?limit=40`);
        const data = await res.json();
        
        container.innerHTML = data.recent_in_memory_traces.slice().reverse().map(l => `
            <div class="log-entry" style="margin-bottom: 8px;">
                <span style="color: #94a3b8;">[${l.timestamp}]</span>
                <strong style="color: ${l.level === 'ERROR' ? '#f87171' : '#38bdf8'};">[${l.level}]</strong>
                ${l.message}
                ${l.details ? `<pre style="color: #a7f3d0; margin-top: 4px; font-size: 11px;">${JSON.stringify(l.details, null, 2)}</pre>` : ''}
            </div>
        `).join("");
    } catch (e) {
        container.innerHTML = `<div style='color: #f87171;'>Failed to load logs: ${e.message}</div>`;
    }
}

// ---------------------------------------------------------
// Utilities
// ---------------------------------------------------------
function getStatusBadgeClass(status) {
    switch (status) {
        case "DELIVERED": return "badge-green";
        case "OUT_FOR_DELIVERY": return "badge-blue";
        case "PREPARING": return "badge-yellow";
        case "RECEIVED": return "badge-gray";
        case "CANCELLED": return "badge-gray";
        case "FAILED": return "badge-red";
        default: return "badge-gray";
    }
}

function getPriorityBadgeClass(priority) {
    switch (priority) {
        case "Critical": return "badge-red";
        case "High": return "badge-red";
        case "Medium": return "badge-yellow";
        case "Low": return "badge-green";
        default: return "badge-gray";
    }
}

function formatMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}
