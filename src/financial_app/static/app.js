/**
 * Meridian Pay Support Portal — Clean Financial Customer Interface
 * Autonomous commercial card concierge for transaction queries, card services, and account management.
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let currentAccountId = "ACC-0001";
  let accountsList = [];

  // DOM Elements - Navigation & Header
  const accountSelect = document.getElementById("account-select");
  const navCompanyName = document.getElementById("nav-company-name");
  const navTierBadge = document.getElementById("nav-tier-badge");
  const companyAvatar = document.getElementById("company-avatar");
  const promptSelect = document.getElementById("prompt-select") || { value: "v3" };
  const channelSelect = document.getElementById("channel-select") || { value: "web_chat" };

  // Banking Hub DOM
  const cardStatusBadge = document.getElementById("card-status-badge");
  const cardNumberDisplay = document.getElementById("card-number-display");
  const cardHolderName = document.getElementById("card-holder-name");
  const accountKycBadge = document.getElementById("account-kyc-badge");
  const currentBalanceDisplay = document.getElementById("current-balance-display");
  const creditLimitDisplay = document.getElementById("credit-limit-display");
  const creditUtilizationBar = document.getElementById("credit-utilization-bar");
  const utilizationPct = document.getElementById("utilization-pct");
  const availableCreditDisplay = document.getElementById("available-credit-display");
  const fraudScoreVal = document.getElementById("fraud-score-val");
  const riskFlagsDisplay = document.getElementById("risk-flags-display");
  const actionCountBadge = document.getElementById("action-count-badge");
  const actionLedgerList = document.getElementById("action-ledger-list");
  const transactionList = document.getElementById("transaction-list");
  const txnCountBadge = document.getElementById("txn-count-badge");

  // Chat DOM
  const chatMessagesContainer = document.getElementById("chat-messages-container");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const btnSendMessage = document.getElementById("btn-send-message");
  const agentTyping = document.getElementById("agent-typing");
  const btnClearChat = document.getElementById("btn-clear-chat");
  const btnResetData = document.getElementById("btn-reset-data");

  // Modals & Toast
  const kbModal = document.getElementById("kb-modal");
  const kbModalTitle = document.getElementById("kb-modal-title");
  const kbModalPath = document.getElementById("kb-modal-path");
  const kbModalContent = document.getElementById("kb-modal-content");
  const kbModalClose = document.getElementById("kb-modal-close");
  const kbModalOk = document.getElementById("kb-modal-ok");

  const appToast = document.getElementById("app-toast");
  const toastIcon = document.getElementById("toast-icon");
  const toastMessage = document.getElementById("toast-message");

  // Real Financial Inquiry Presets
  const SCENARIOS = {
    recent_txns: "What are my recent transactions on this account?",
    aws_spend: "Did our transaction to AWS EMEA go through, and what was the charge amount?",
    travel_spend: "What charges were made recently for travel, including Delta Air Lines and Uber?",
    card_replace: "My physical card was bent in my wallet and the chip fell out. We need a replacement card ASAP.",
    limit_check: "What is our current balance, credit limit, and available spend remaining?",
    fraud_dispute: "Customer says a $2,400 charge to 'GLOBAL VEND LTD' isn't theirs. How do I dispute this?"
  };

  // --------------------------------------------------------------------------
  // Initialization
  // --------------------------------------------------------------------------
  async function init() {
    setupEventListeners();
    await fetchAccounts();
    await loadAccountDetails(currentAccountId);
  }

  // --------------------------------------------------------------------------
  // Event Listeners
  // --------------------------------------------------------------------------
  function setupEventListeners() {
    accountSelect.addEventListener("change", (e) => {
      currentAccountId = e.target.value;
      loadAccountDetails(currentAccountId);
      showToast(`Switched active account to ${currentAccountId}`, "🏢");
    });

    // Preset chip clicks
    document.querySelectorAll(".preset-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const scenarioKey = chip.getAttribute("data-scenario");
        const promptText = SCENARIOS[scenarioKey];
        if (promptText) {
          chatInput.value = promptText;
          chatInput.focus();
          submitInquiry(promptText);
        }
      });
    });

    // Chat submit
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const message = chatInput.value.trim();
      if (!message) return;
      submitInquiry(message);
    });

    // Enter key handling (Shift+Enter for newline)
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event("submit"));
      }
    });

    // Clear Chat
    btnClearChat.addEventListener("click", () => {
      chatMessagesContainer.innerHTML = `
        <div class="message-row agent-row">
          <div class="msg-avatar agent-avatar">MP</div>
          <div class="msg-bubble agent-bubble">
            <div class="msg-sender">Meridian Pay Support Concierge</div>
            <div class="msg-text">
              Conversation reset. How can I assist you with your Meridian Pay commercial account or transactions?
            </div>
            <div class="msg-meta">
              <span class="msg-time">Just now</span>
            </div>
          </div>
        </div>
      `;
      showToast("Chat history cleared", "🧹");
    });

    // Reset Data
    btnResetData.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/app/reset", { method: "POST" });
        if (res.ok) {
          showToast("Account ledger reset to initial state", "🔄");
          actionLedgerList.innerHTML = `<div class="ledger-empty">No agent state actions executed yet in this session.</div>`;
          actionCountBadge.textContent = "0 Actions";
          await loadAccountDetails(currentAccountId);
        }
      } catch (err) {
        showToast("Failed to reset ledger data", "❌");
      }
    });

    // Policy Modal
    if (kbModalClose) kbModalClose.addEventListener("click", () => kbModal.close());
    if (kbModalOk) kbModalOk.addEventListener("click", () => kbModal.close());
  }

  // --------------------------------------------------------------------------
  // Data Fetching: Accounts & Financial Details
  // --------------------------------------------------------------------------
  async function fetchAccounts() {
    try {
      const res = await fetch("/api/app/accounts");
      const data = await res.json();
      accountsList = data.accounts || [];

      accountSelect.innerHTML = "";
      accountsList.forEach((acc) => {
        const opt = document.createElement("option");
        opt.value = acc.account_id;
        opt.textContent = `${acc.account_id} — ${acc.company_name} (${acc.tier.toUpperCase()})`;
        if (acc.account_id === currentAccountId) opt.selected = true;
        accountSelect.appendChild(opt);
      });
    } catch (err) {
      console.error("Error fetching accounts:", err);
      accountSelect.innerHTML = `<option value="ACC-0001">ACC-0001 — Acme Cloud Inc</option>`;
    }
  }

  async function loadAccountDetails(accountId) {
    try {
      const res = await fetch(`/api/app/accounts/${accountId}`);
      const acc = await res.json();
      renderAccountView(acc);
    } catch (err) {
      console.error("Error loading account details:", err);
    }
  }

  function renderAccountView(acc) {
    // Header & User badge
    navCompanyName.textContent = acc.company_name || "Acme Cloud Inc";
    const tier = (acc.tier || "growth").toUpperCase();
    navTierBadge.textContent = `${tier} TIER`;
    const initials = (acc.company_name || "AC").split(" ").map(w => w[0]).slice(0, 2).join("");
    companyAvatar.textContent = initials;

    // Card visual
    cardHolderName.textContent = (acc.company_name || "ACME CLOUD INC").toUpperCase();
    const cardId = acc.active_card_id || "CARD-0001";
    const cardSuffix = cardId.replace(/[^0-9]/g, "").slice(-4) || "1042";
    cardNumberDisplay.textContent = `•••• •••• •••• ${cardSuffix}`;

    // Card Status
    const isReplaced = cardId.includes("NEW");
    if (isReplaced) {
      cardStatusBadge.textContent = "REPLACED";
      cardStatusBadge.className = "card-type-chip";
      cardStatusBadge.style.background = "rgba(59, 130, 246, 0.25)";
      cardStatusBadge.style.color = "#93c5fd";
      cardStatusBadge.style.borderColor = "rgba(59, 130, 246, 0.5)";
    } else {
      cardStatusBadge.textContent = "ACTIVE";
      cardStatusBadge.className = "card-type-chip";
      cardStatusBadge.style = "";
    }

    // Balances & Limit
    const balance = acc.current_balance || 0;
    const limit = acc.credit_limit || 15000;
    const available = Math.max(0, limit - balance);
    const utilPct = Math.min(100, Math.round((balance / (limit || 1)) * 100));

    currentBalanceDisplay.textContent = formatUSD(balance);
    creditLimitDisplay.textContent = formatUSD(limit);
    availableCreditDisplay.textContent = `${formatUSD(available)} Available`;
    utilizationPct.textContent = `${utilPct}% Utilized`;
    creditUtilizationBar.style.width = `${utilPct}%`;

    // Badges & Risk
    accountKycBadge.textContent = `KYC ${capitalize(acc.kyc_status || "verified")}`;
    const fraudScore = acc.fraud_score !== undefined ? acc.fraud_score : 12;
    fraudScoreVal.textContent = `${fraudScore} / 100`;
    fraudScoreVal.className = `risk-score ${fraudScore > 50 ? 'high' : (fraudScore > 30 ? 'medium' : 'low')}`;

    const flags = acc.risk_flags || [];
    riskFlagsDisplay.textContent = flags.length > 0 ? flags.join(", ") : "None";

    // Transactions list
    renderTransactions(acc.transactions || []);
  }

  function renderTransactions(txns) {
    txnCountBadge.textContent = `${txns.length} recorded`;
    if (!txns.length) {
      transactionList.innerHTML = `<div class="txn-loading">No transactions found for this account.</div>`;
      return;
    }

    transactionList.innerHTML = "";
    txns.slice(0, 15).forEach((t) => {
      const row = document.createElement("div");
      row.className = "txn-row";

      const merchant = t.merchant_name || t.merchant || "Merchant Purchase";
      const amt = formatUSD(t.amount || 0);
      const date = t.date ? new Date(t.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "Recent";
      const status = (t.status || "settled").toLowerCase();
      const tid = t.id || t.transaction_id || "TXN";

      row.innerHTML = `
        <div class="txn-info-left">
          <span class="txn-merchant">${escapeHtml(merchant)}</span>
          <span class="txn-details-sub">
            <span>${date}</span>
            <span>•</span>
            <span class="txn-id-pill">${escapeHtml(tid)}</span>
          </span>
        </div>
        <div class="txn-info-right">
          <span class="txn-amount">${amt}</span>
          <span class="txn-status-badge ${status}">${status}</span>
        </div>
      `;
      transactionList.appendChild(row);
    });
  }

  // --------------------------------------------------------------------------
  // Chat & Live Agent Execution
  // --------------------------------------------------------------------------
  async function submitInquiry(ticketText) {
    chatInput.value = "";
    btnSendMessage.disabled = true;

    // Append User Message
    appendUserMessage(ticketText);
    scrollToBottom();

    // Show typing
    agentTyping.style.display = "flex";
    scrollToBottom();

    try {
      const payload = {
        ticket: ticketText,
        account_id: currentAccountId,
        channel: channelSelect.value || "web_chat",
        prompt_version: promptSelect.value || "v3"
      };

      const res = await fetch("/api/app/agent/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Agent run failed with status ${res.status}`);
      }

      const result = await res.json();

      // Hide typing
      agentTyping.style.display = "none";

      // Append Agent Message (clean, without developer Braintrust telemetry)
      appendAgentMessage(result);
      scrollToBottom();

      // If actions were executed, update Action Ledger and reload account data
      if (result.actions && result.actions.length > 0) {
        updateActionLedger(result.actions, result.action_ledger);
        await loadAccountDetails(currentAccountId);
        showToast(`Account updated: ${result.actions.join(", ")}`, "⚡");
      }

    } catch (err) {
      console.error("Error executing agent:", err);
      agentTyping.style.display = "none";
      appendErrorMessage("Sorry, an error occurred while checking your account records. Please try again.");
      scrollToBottom();
    } finally {
      btnSendMessage.disabled = false;
      chatInput.focus();
    }
  }

  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user-row";
    row.innerHTML = `
      <div class="msg-avatar user-avatar">${companyAvatar.textContent}</div>
      <div class="msg-bubble user-bubble">
        <div class="msg-sender">You (${navCompanyName.textContent})</div>
        <div class="msg-text">${escapeHtml(text)}</div>
        <div class="msg-meta">
          <span class="msg-time">Just now</span>
        </div>
      </div>
    `;
    chatMessagesContainer.appendChild(row);
  }

  function appendAgentMessage(result) {
    const row = document.createElement("div");
    row.className = "message-row agent-row";

    const isEscalated = result.escalated === true;
    const formattedContent = formatReplyText(result.reply);

    row.innerHTML = `
      <div class="msg-avatar agent-avatar">MP</div>
      <div class="msg-bubble agent-bubble">
        <div class="msg-sender">
          <span>Meridian Pay Support Concierge</span>
          ${isEscalated ? '<span class="badge-escalated">🚨 Escalated to Specialist</span>' : ''}
        </div>
        <div class="msg-text">${formattedContent}</div>
        <div class="msg-meta">
          <span class="msg-time">Just now</span>
        </div>
      </div>
    `;

    chatMessagesContainer.appendChild(row);
  }

  function appendErrorMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row agent-row";
    row.innerHTML = `
      <div class="msg-avatar agent-avatar" style="background: #f43f5e;">!</div>
      <div class="msg-bubble agent-bubble" style="border-color: rgba(244, 63, 94, 0.4);">
        <div class="msg-sender" style="color: #fda4af;">Support Notice</div>
        <div class="msg-text">${escapeHtml(text)}</div>
      </div>
    `;
    chatMessagesContainer.appendChild(row);
  }

  // --------------------------------------------------------------------------
  // Action Ledger Updates
  // --------------------------------------------------------------------------
  function updateActionLedger(actions, ledgerEntries) {
    if (!actions || !actions.length) return;

    if (actionLedgerList.querySelector(".ledger-empty")) {
      actionLedgerList.innerHTML = "";
    }

    const currentCount = actionLedgerList.querySelectorAll(".ledger-entry").length;
    actionCountBadge.textContent = `${currentCount + actions.length} Actions`;

    actions.forEach((action) => {
      const entry = document.createElement("div");
      entry.className = "ledger-entry";
      const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      entry.innerHTML = `
        <span class="ledger-entry-action">⚡ ${escapeHtml(action)}()</span>
        <span class="ledger-entry-time">${now}</span>
      `;
      actionLedgerList.prepend(entry);
    });
  }

  // --------------------------------------------------------------------------
  // Rich Markdown & Text Formatting
  // --------------------------------------------------------------------------
  function formatReplyText(text) {
    if (!text) return "";
    let html = escapeHtml(text);

    // Bold: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic: *text*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Inline code / IDs: `text`
    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

    // Currency highlighting: $X,XXX.XX
    html = html.replace(/(\$[\d,]+(?:\.\d{2})?)/g, '<span class="currency-highlight">$1</span>');

    // Parse lists and paragraphs
    const lines = html.split('\n');
    let inList = false;
    let formatted = [];

    for (let line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*')) {
        if (!inList) {
          formatted.push('<ul class="reply-list">');
          inList = true;
        }
        const item = trimmed.replace(/^[•\-\*]\s*/, '');
        formatted.push(`<li>${item}</li>`);
      } else {
        if (inList) {
          formatted.push('</ul>');
          inList = false;
        }
        if (trimmed === '') {
          formatted.push('<div class="reply-spacer"></div>');
        } else {
          formatted.push(`<p class="reply-para">${line}</p>`);
        }
      }
    }
    if (inList) {
      formatted.push('</ul>');
    }

    return formatted.join('');
  }

  // --------------------------------------------------------------------------
  // Toast Notifications
  // --------------------------------------------------------------------------
  let toastTimer = null;
  function showToast(message, icon = "ℹ️") {
    toastIcon.textContent = icon;
    toastMessage.textContent = message;

    try {
      appToast.showPopover();
    } catch (e) {
      appToast.style.display = "flex";
    }

    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      try {
        appToast.hidePopover();
      } catch (e) {
        appToast.style.display = "none";
      }
    }, 3200);
  }

  // --------------------------------------------------------------------------
  // Helpers
  // --------------------------------------------------------------------------
  function formatUSD(amount) {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
  }

  function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function scrollToBottom() {
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
  }

  // Start app
  init();
});
