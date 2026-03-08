/* ═══════════════════════════════════════════════════════════
   RIG-Builder — Frontend Logic
   ═══════════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────────
let currentBuild = null;
let selectedTier = "Mid-Range";
let currentUser = null;

// ═══════════════════════════════════════════════════════════
//   Authentication
// ═══════════════════════════════════════════════════════════

// Check session on page load
async function checkAuth() {
    try {
        const res = await fetch("/auth/me");
        const data = await res.json();
        if (data.authenticated) {
            currentUser = data.user;
            updateAuthUI(true);
        }
    } catch (e) { /* not logged in */ }
}

function updateAuthUI(loggedIn) {
    const btn = document.getElementById("auth-trigger");
    const text = document.getElementById("auth-trigger-text");

    if (loggedIn && currentUser) {
        text.textContent = currentUser.username;
        btn.classList.add("logged-in");
        btn.onclick = showUserMenu;
    } else {
        text.textContent = "Sign In";
        btn.classList.remove("logged-in");
        btn.onclick = showAuthModal;
    }
}

function showAuthModal() {
    document.getElementById("auth-modal").classList.remove("hidden");
    document.getElementById("login-error").classList.add("hidden");
    document.getElementById("register-error").classList.add("hidden");
}

function hideAuthModal() {
    document.getElementById("auth-modal").classList.add("hidden");
}

function switchAuthTab(tab) {
    document.getElementById("tab-login").classList.toggle("active", tab === "login");
    document.getElementById("tab-register").classList.toggle("active", tab === "register");
    document.getElementById("login-form").classList.toggle("hidden", tab !== "login");
    document.getElementById("register-form").classList.toggle("hidden", tab !== "register");
    document.getElementById("login-error").classList.add("hidden");
    document.getElementById("register-error").classList.add("hidden");
}

async function handleLogin(e) {
    e.preventDefault();
    const errEl = document.getElementById("login-error");
    errEl.classList.add("hidden");

    const username = document.getElementById("login-username").value.trim();
    const password = document.getElementById("login-password").value;

    try {
        const res = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
        const data = await res.json();

        if (res.ok) {
            currentUser = data.user;
            updateAuthUI(true);
            hideAuthModal();
            showToast(`Welcome back, ${data.user.username}! 👋`);
            loadHistory();
        } else {
            errEl.textContent = data.error || "Login failed";
            errEl.classList.remove("hidden");
        }
    } catch (err) {
        errEl.textContent = "Connection error";
        errEl.classList.remove("hidden");
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const errEl = document.getElementById("register-error");
    errEl.classList.add("hidden");

    const username = document.getElementById("register-username").value.trim();
    const email = document.getElementById("register-email").value.trim();
    const password = document.getElementById("register-password").value;

    try {
        const res = await fetch("/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password }),
        });
        const data = await res.json();

        if (res.ok) {
            currentUser = data.user;
            updateAuthUI(true);
            hideAuthModal();
            showToast(`Account created! Welcome, ${data.user.username}! 🎉`);
        } else {
            errEl.textContent = data.error || "Registration failed";
            errEl.classList.remove("hidden");
        }
    } catch (err) {
        errEl.textContent = "Connection error";
        errEl.classList.remove("hidden");
    }
}

function showUserMenu() {
    if (confirm(`Logged in as ${currentUser.username}\n\nDo you want to sign out?`)) {
        handleLogout();
    }
}

async function handleLogout() {
    try {
        await fetch("/auth/logout", { method: "POST" });
    } catch (e) { /* ignore */ }
    currentUser = null;
    updateAuthUI(false);
    showToast("Signed out 👋");
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
    if (e.target.id === "auth-modal") hideAuthModal();
});

// Init auth check
checkAuth();

// ── Category Icons ─────────────────────────────────────────
const CATEGORY_ICONS = {
    "CPU": "🔲",
    "GPU": "🎮",
    "Motherboard": "🔌",
    "RAM": "💾",
    "Storage": "💿",
    "PSU": "⚡",
    "Case": "🖥️",
    "Cooler": "❄️",
};

// ── DOM Elements ───────────────────────────────────────────
const budgetSlider = document.getElementById("budget-slider");
const budgetValue = document.getElementById("budget-value");
const buildForm = document.getElementById("build-form");
const generateBtn = document.getElementById("generate-btn");
const tierGrid = document.getElementById("tier-grid");
const configCard = document.getElementById("config-card");
const loadingContainer = document.getElementById("loading-container");
const resultsContainer = document.getElementById("results-container");
const errorContainer = document.getElementById("error-container");
const componentsGrid = document.getElementById("components-grid");
const totalPrice = document.getElementById("total-price");
const aiSummary = document.getElementById("ai-summary");
const buildSpecsLabel = document.getElementById("build-specs-label");
const loadingStep = document.getElementById("loading-step");
const loadingBarFill = document.getElementById("loading-bar-fill");

// ── Budget Slider ──────────────────────────────────────────
budgetSlider.addEventListener("input", () => {
    const val = parseInt(budgetSlider.value);
    budgetValue.textContent = `₹${val.toLocaleString("en-IN")}`;
});

// ── Tier Selection ─────────────────────────────────────────
tierGrid.addEventListener("click", (e) => {
    const btn = e.target.closest(".tier-btn");
    if (!btn) return;

    tierGrid.querySelectorAll(".tier-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    selectedTier = btn.dataset.tier;
});

// ── Navigation ─────────────────────────────────────────────
document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        const section = btn.dataset.section;
        document.querySelectorAll(".section").forEach((s) => s.classList.remove("active"));
        document.getElementById(`section-${section}`).classList.add("active");

        if (section === "history") {
            loadHistory();
        }
    });
});

// ── Loading Animation ──────────────────────────────────────
const LOADING_STEPS = [
    "Consulting AI for optimal components...",
    "Analyzing compatibility and performance...",
    "Scraping real-time prices from retailers...",
    "Comparing prices across marketplaces...",
    "Finalizing your perfect build...",
];

function animateLoading() {
    let step = 0;
    loadingBarFill.style.width = "0%";

    const interval = setInterval(() => {
        if (step < LOADING_STEPS.length) {
            loadingStep.textContent = LOADING_STEPS[step];
            loadingBarFill.style.width = `${((step + 1) / LOADING_STEPS.length) * 90}%`;
            step++;
        }
    }, 2500);

    return interval;
}

// ── Generate Build ─────────────────────────────────────────
buildForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const budget = parseInt(budgetSlider.value);
    const useCase = document.getElementById("use-case").value;

    // Show loading
    configCard.classList.add("hidden");
    resultsContainer.classList.add("hidden");
    errorContainer.classList.add("hidden");
    loadingContainer.classList.remove("hidden");

    generateBtn.disabled = true;
    const loadingInterval = animateLoading();

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                budget: budget,
                use_case: useCase,
                performance_tier: selectedTier,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Failed to generate build");
        }

        currentBuild = data;
        displayResults(data);
    } catch (error) {
        showError(error.message);
    } finally {
        clearInterval(loadingInterval);
        loadingContainer.classList.add("hidden");
        generateBtn.disabled = false;
    }
});

// ── Display Results ────────────────────────────────────────
function displayResults(data) {
    // Summary
    totalPrice.textContent = `₹${data.total_price.toLocaleString("en-IN")}`;
    aiSummary.textContent = data.summary || "AI-optimized build for your requirements.";
    buildSpecsLabel.textContent = `${data.use_case} • ${data.performance_tier} • ₹${data.budget.toLocaleString("en-IN")} budget`;

    // Component cards
    componentsGrid.innerHTML = "";
    const components = data.components || [];

    components.forEach((comp, index) => {
        const card = createComponentCard(comp, index);
        componentsGrid.appendChild(card);
    });

    // Show results
    resultsContainer.classList.remove("hidden");
    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
}

function createComponentCard(comp, index) {
    const card = document.createElement("div");
    card.className = "component-card glass-card";
    card.style.animationDelay = `${index * 0.08}s`;
    card.style.animation = `slideUp 0.5s ease-out ${index * 0.08}s both`;

    const icon = CATEGORY_ICONS[comp.category] || "🔧";
    const prices = comp.prices || [];
    const estimatedPrice = comp.estimated_price || 0;

    // Find best price
    let bestPrice = estimatedPrice;
    if (prices.length > 0) {
        bestPrice = Math.min(...prices.map((p) => p.price));
    }

    // Price comparison HTML
    let priceHTML = "";
    if (prices.length > 0) {
        const sortedPrices = [...prices].sort((a, b) => a.price - b.price);
        priceHTML = `<div class="price-comparison">`;
        sortedPrices.forEach((p, i) => {
            const isBest = i === 0;
            priceHTML += `
                <div class="price-row ${isBest ? "best" : ""}">
                    <span class="retailer-name">
                        <span class="retailer-badge"></span>
                        ${p.retailer}
                    </span>
                    <span class="retailer-price">₹${p.price.toLocaleString("en-IN")}</span>
                    ${p.url ? `<a href="${p.url}" target="_blank" rel="noopener" class="retailer-link">View →</a>` : ""}
                </div>`;
        });
        priceHTML += `</div>`;
    } else {
        priceHTML = `
            <div class="price-comparison">
                <div class="price-row">
                    <span class="retailer-name">
                        <span class="retailer-badge"></span>
                        Estimated
                    </span>
                    <span class="retailer-price">₹${estimatedPrice.toLocaleString("en-IN")}</span>
                </div>
                <p class="no-prices">Live prices unavailable — showing AI estimate</p>
            </div>`;
    }

    card.innerHTML = `
        <div class="component-header">
            <span class="component-category">
                <span class="cat-icon">${icon}</span>
                ${comp.category}
            </span>
            <span class="component-price-tag">₹${bestPrice.toLocaleString("en-IN")}</span>
        </div>
        <div class="component-name">${comp.name}</div>
        <div class="component-brand">${comp.brand || ""}</div>
        ${priceHTML}
        ${comp.rationale ? `
        <div class="component-rationale">
            <div class="rationale-label">Why this part?</div>
            ${comp.rationale}
        </div>` : ""}
    `;

    return card;
}

// ── Save Build ─────────────────────────────────────────────
async function saveBuild() {
    if (!currentBuild) return;
    if (!currentUser) {
        showToast("Please sign in to save builds 🔒");
        showAuthModal();
        return;
    }

    try {
        const response = await fetch("/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(currentBuild),
        });

        const data = await response.json();

        if (response.ok) {
            showToast("Build saved successfully! ✅");
            currentBuild.id = data.id;
        } else {
            showToast("Failed to save build ❌");
        }
    } catch (error) {
        showToast("Error saving build ❌");
    }
}

// ── Export PDF ──────────────────────────────────────────────
async function exportPDF() {
    if (!currentBuild) return;

    try {
        if (currentBuild.id) {
            // Saved build — use GET route
            window.open(`/export?id=${currentBuild.id}`, "_blank");
        } else {
            // Unsaved build — POST the data
            const response = await fetch("/export-current", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(currentBuild),
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "RIG_Build.pdf";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showToast("PDF exported! 📄");
            } else {
                showToast("Failed to export PDF ❌");
            }
        }
    } catch (error) {
        showToast("Error exporting PDF ❌");
    }
}

// ── Load History ───────────────────────────────────────────
async function loadHistory() {
    const grid = document.getElementById("history-grid");

    try {
        const response = await fetch("/history");
        const builds = await response.json();

        if (builds.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    <h3>No Saved Builds</h3>
                    <p>Generate and save a build to see it here.</p>
                </div>`;
            return;
        }

        grid.innerHTML = builds
            .map((build) => {
                const components = build.components || [];
                const chips = components
                    .slice(0, 4)
                    .map((c) => `<span class="history-chip">${c.category}: ${c.name ? c.name.substring(0, 25) : "N/A"}</span>`)
                    .join("");

                const date = new Date(build.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                });

                return `
                <div class="history-card glass-card">
                    <div class="history-card-header">
                        <span class="history-card-title">${build.name}</span>
                        <span class="history-card-price">₹${(build.total_price || 0).toLocaleString("en-IN")}</span>
                    </div>
                    <div class="history-card-meta">
                        <span>🎯 ${build.use_case || "N/A"}</span>
                        <span>⚡ ${build.performance_tier || "N/A"}</span>
                        <span>📅 ${date}</span>
                    </div>
                    <div class="history-card-components">${chips}</div>
                    <div class="history-card-actions">
                        <button class="history-action-btn" onclick="exportHistoryPDF(${build.id})">📄 PDF</button>
                        <button class="history-action-btn" onclick="openPCPartPicker(${build.id})">🔗 PCPartPicker</button>
                        <button class="history-action-btn delete" onclick="deleteBuild(${build.id})">🗑️ Delete</button>
                    </div>
                </div>`;
            })
            .join("");
    } catch (error) {
        grid.innerHTML = `<div class="empty-state"><h3>Error loading history</h3><p>${error.message}</p></div>`;
    }
}

// ── History Actions ────────────────────────────────────────
function exportHistoryPDF(id) {
    window.open(`/export?id=${id}`, "_blank");
}

function openPCPartPicker(id) {
    window.open(`/pcpartpicker/${id}`, "_blank");
}

async function deleteBuild(id) {
    if (!confirm("Delete this build?")) return;

    try {
        const response = await fetch(`/delete/${id}`, { method: "DELETE" });
        if (response.ok) {
            showToast("Build deleted 🗑️");
            loadHistory();
        } else {
            showToast("Failed to delete build ❌");
        }
    } catch (error) {
        showToast("Error deleting build ❌");
    }
}

// ── Reset Builder ──────────────────────────────────────────
function resetBuilder() {
    currentBuild = null;
    resultsContainer.classList.add("hidden");
    errorContainer.classList.add("hidden");
    loadingContainer.classList.add("hidden");
    configCard.classList.remove("hidden");
    configCard.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Error Display ──────────────────────────────────────────
function showError(message) {
    document.getElementById("error-message").textContent = message;
    errorContainer.classList.remove("hidden");
    errorContainer.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Toast Notification ─────────────────────────────────────
function showToast(message) {
    const toast = document.getElementById("toast");
    document.getElementById("toast-message").textContent = message;
    toast.classList.remove("hidden");
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.classList.add("hidden"), 400);
    }, 3000);
}

// ═══════════════════════════════════════════════════════════
//   Chatbot Logic
// ═══════════════════════════════════════════════════════════

const chatInput = document.getElementById("chat-input");
const chatSendBtn = document.getElementById("chat-send-btn");
const chatMessages = document.getElementById("chat-messages");
const chatSuggestions = document.getElementById("chat-suggestions");
const chatClearBtn = document.getElementById("chat-clear-btn");

let chatHistory = [];
let chatBuildData = null; // Last build generated via chat

// ── Send Chat Message ──────────────────────────────────────
async function sendChatMessage(message) {
    if (!message.trim()) return;

    // Hide suggestions after first message
    chatSuggestions.style.display = "none";

    // Add user message
    appendChatMsg("user", message);
    chatHistory.push({ role: "user", content: message });

    // Disable input
    chatInput.value = "";
    chatInput.disabled = true;
    chatSendBtn.disabled = true;

    // Show typing indicator
    const typingEl = appendTypingIndicator();

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: message,
                history: chatHistory,
            }),
        });

        const data = await response.json();

        // Remove typing indicator
        typingEl.remove();

        if (data.type === "build") {
            // Bot message + build result
            appendChatMsg("bot", data.message, data);
            chatHistory.push({ role: "assistant", content: data.message });
            chatBuildData = data;
        } else {
            // Question / follow-up
            appendChatMsg("bot", data.message);
            chatHistory.push({ role: "assistant", content: data.message });
        }
    } catch (error) {
        typingEl.remove();
        appendChatMsg("bot", "Sorry, something went wrong. Please try again!");
    } finally {
        chatInput.disabled = false;
        chatSendBtn.disabled = false;
        chatInput.focus();
    }
}

// ── Append Chat Message ────────────────────────────────────
function appendChatMsg(role, text, buildData = null) {
    const msg = document.createElement("div");
    msg.className = `chat-msg ${role}`;

    const avatar = role === "user" ? "👤" : "🤖";

    let contentHTML = `<p>${text}</p>`;

    // If there's build data, render the build result
    if (buildData && buildData.components) {
        const components = buildData.components || [];
        const total = buildData.total_price || 0;

        let rows = components.map((c) => {
            const price = c.estimated_price || 0;
            return `
                <div class="chat-build-row">
                    <div class="chat-build-row-name">
                        <span class="chat-build-row-cat">${c.category}</span>
                        ${c.name}
                    </div>
                    <span class="chat-build-row-price">₹${price.toLocaleString("en-IN")}</span>
                </div>`;
        }).join("");

        contentHTML += `
            <div class="chat-build-result">
                <div class="chat-build-header">
                    <h4>🖥️ Your Build</h4>
                    <span class="chat-build-total">₹${total.toLocaleString("en-IN")}</span>
                </div>
                <div class="chat-build-components">${rows}</div>
                <div class="chat-build-actions">
                    <button class="primary" onclick="saveChatBuild()">💾 Save Build</button>
                    <button onclick="exportChatPDF()">📄 Export PDF</button>
                    <button onclick="viewChatBuildFull()">🔍 Full View</button>
                </div>
            </div>`;
    }

    msg.innerHTML = `
        <div class="chat-msg-avatar">${avatar}</div>
        <div class="chat-msg-content">${contentHTML}</div>
    `;

    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── Typing Indicator ───────────────────────────────────────
function appendTypingIndicator() {
    const msg = document.createElement("div");
    msg.className = "chat-msg bot";
    msg.innerHTML = `
        <div class="chat-msg-avatar">🤖</div>
        <div class="chat-msg-content">
            <div class="chat-typing">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msg;
}

// ── Chat Build Actions ─────────────────────────────────────
async function saveChatBuild() {
    if (!chatBuildData) return;
    if (!currentUser) {
        showToast("Please sign in to save builds 🔒");
        showAuthModal();
        return;
    }

    const saveData = {
        name: `Chat Build — ${chatBuildData.use_case || "Custom"}`,
        budget: chatBuildData.budget || 0,
        use_case: chatBuildData.use_case || "Custom",
        performance_tier: chatBuildData.performance_tier || "Mid-Range",
        summary: chatBuildData.summary || chatBuildData.message || "",
        components: chatBuildData.components || [],
        total_price: chatBuildData.total_price || 0,
    };

    try {
        const response = await fetch("/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(saveData),
        });
        const data = await response.json();
        if (response.ok) {
            chatBuildData.id = data.id;
            showToast("Build saved! ✅");
        } else {
            showToast("Failed to save build ❌");
        }
    } catch (e) {
        showToast("Error saving build ❌");
    }
}

async function exportChatPDF() {
    if (!chatBuildData) return;

    const exportData = {
        name: `Chat Build — ${chatBuildData.use_case || "Custom"}`,
        budget: chatBuildData.budget || 0,
        use_case: chatBuildData.use_case || "Custom",
        performance_tier: chatBuildData.performance_tier || "Mid-Range",
        ai_summary: chatBuildData.summary || chatBuildData.message || "",
        components: chatBuildData.components || [],
        total_price: chatBuildData.total_price || 0,
    };

    try {
        const response = await fetch("/export-current", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(exportData),
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "RIG_Chat_Build.pdf";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            showToast("PDF exported! 📄");
        }
    } catch (e) {
        showToast("Error exporting PDF ❌");
    }
}

function viewChatBuildFull() {
    if (!chatBuildData) return;
    // Switch to builder tab and display the build
    currentBuild = {
        ...chatBuildData,
        budget: chatBuildData.budget || 0,
        use_case: chatBuildData.use_case || "Chat Build",
        performance_tier: chatBuildData.performance_tier || "Mid-Range",
    };

    // Switch to builder section
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    document.getElementById("nav-builder").classList.add("active");
    document.querySelectorAll(".section").forEach((s) => s.classList.remove("active"));
    document.getElementById("section-builder").classList.add("active");

    configCard.classList.add("hidden");
    displayResults(currentBuild);
}

// ── Clear Chat ─────────────────────────────────────────────
chatClearBtn.addEventListener("click", () => {
    chatHistory = [];
    chatBuildData = null;
    chatMessages.innerHTML = `
        <div class="chat-msg bot">
            <div class="chat-msg-avatar">🤖</div>
            <div class="chat-msg-content">
                <p>Hey! I'm your <strong>RIG Assistant</strong>. Tell me what you need your PC for, and I'll build the perfect rig for you.</p>
                <p class="chat-msg-hint">Try something like: <em>"I want to play Valorant at 144+ fps on a 1440p monitor"</em></p>
            </div>
        </div>
    `;
    chatSuggestions.style.display = "flex";
});

// ── Event Listeners ────────────────────────────────────────
chatSendBtn.addEventListener("click", () => {
    sendChatMessage(chatInput.value);
});

chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage(chatInput.value);
    }
});

// Suggestion chips
chatSuggestions.addEventListener("click", (e) => {
    const chip = e.target.closest(".chat-chip");
    if (!chip) return;
    sendChatMessage(chip.dataset.msg);
});

