/**
 * Braintrust Trace Review Studio Client Application
 * Provides real-time filtering, multi-turn inspection, LLM reasoning display,
 * system evaluations scorecard, and commentary syncing back to Braintrust.
 */

// Application State
const state = {
  currentUser: null,
  assigneeFilter: 'me', // 'me' | 'unassigned' | 'all'
  statusFilter: 'all',  // 'all' | 'failed' | 'pending_review' | 'reviewed'
  searchQuery: '',
  traces: [],
  selectedTraceId: null,
  selectedTraceDetail: null,
  activeVerdict: 'pass',
  criteriaScores: {
    human_policy_compliance: 1.0,
    human_date_accuracy: 1.0,
    human_contradiction_free: 1.0,
    human_escalation_appropriate: 1.0,
    human_citation_quality: 1.0,
    human_tone_and_conciseness: 1.0,
    human_tool_execution: 1.0,
  },
  stats: {},
};

// DOM Element References
const elements = {
  projectNameDisplay: document.getElementById('project-name-display'),
  userNameDisplay: document.getElementById('user-name-display'),
  userAvatar: document.getElementById('user-avatar'),
  statAssignedCount: document.getElementById('stat-assigned-count'),
  statUnassignedCount: document.getElementById('stat-unassigned-count'),
  statFailingCount: document.getElementById('stat-failing-count'),
  statNeedsReviewCount: document.getElementById('stat-needs-review-count'),
  traceSearch: document.getElementById('trace-search'),
  traceList: document.getElementById('trace-list'),
  btnRefreshAll: document.getElementById('btn-refresh-all'),
  inspectorEmptyState: document.getElementById('inspector-empty-state'),
  inspectorContent: document.getElementById('inspector-content'),
  traceDetailTitle: document.getElementById('trace-detail-title'),
  traceDetailId: document.getElementById('trace-detail-id'),
  traceDetailAccount: document.getElementById('trace-detail-account'),
  traceDetailTier: document.getElementById('trace-detail-tier'),
  traceDetailTime: document.getElementById('trace-detail-time'),
  traceDetailTags: document.getElementById('trace-detail-tags'),
  btnAssignMe: document.getElementById('btn-assign-me'),
  btnOpenBraintrust: document.getElementById('btn-open-braintrust'),
  evalDiagnosticBanner: document.getElementById('eval-diagnostic-banner'),
  evalCardsGrid: document.getElementById('eval-cards-grid'),
  turnsTimeline: document.getElementById('turns-timeline'),
  selectFailureCategory: document.getElementById('select-failure-category'),
  reviewCommentInput: document.getElementById('review-comment-input'),
  btnSubmitReview: document.getElementById('btn-submit-review'),
  criteriaSummaryBadge: document.getElementById('criteria-summary-badge'),
  criteriaGroupContainer: document.getElementById('criteria-group-container'),
  reviewSidebarContent: document.getElementById('review-sidebar-content'),
  reviewSidebarEmpty: document.getElementById('review-sidebar-empty'),
  toastContainer: document.getElementById('toast-container'),
  filterTabs: document.querySelectorAll('.filter-tab'),
  chipFilters: document.querySelectorAll('.chip-filter'),
  verdictButtons: document.querySelectorAll('.btn-verdict'),
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await loadCurrentUser();
  await loadTraces();
});

// Setup UI Event Listeners
function setupEventListeners() {
  // Assignee Tabs
  elements.filterTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      elements.filterTabs.forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      state.assigneeFilter = tab.dataset.assignee;
      loadTraces();
    });
  });

  // Quick Status Filter Chips
  elements.chipFilters.forEach((chip) => {
    chip.addEventListener('click', () => {
      elements.chipFilters.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      state.statusFilter = chip.dataset.status;
      loadTraces();
    });
  });

  // Header Stat Pills clicking activates filter
  document.getElementById('stat-assigned-btn')?.addEventListener('click', () => {
    document.getElementById('tab-assignee-me')?.click();
  });
  document.getElementById('stat-unassigned-btn')?.addEventListener('click', () => {
    document.getElementById('tab-assignee-unassigned')?.click();
  });
  document.getElementById('stat-failing-btn')?.addEventListener('click', () => {
    document.getElementById('chip-status-failed')?.click();
  });
  document.getElementById('stat-needs-review-btn')?.addEventListener('click', () => {
    document.getElementById('chip-status-pending')?.click();
  });

  // Search input debounced
  let searchTimeout;
  elements.traceSearch.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.searchQuery = e.target.value.trim();
      loadTraces();
    }, 250);
  });

  // Refresh Button
  elements.btnRefreshAll.addEventListener('click', () => {
    loadTraces();
    if (state.selectedTraceId) {
      loadTraceDetail(state.selectedTraceId);
    }
  });

  // Assign to Me Button
  elements.btnAssignMe.addEventListener('click', async () => {
    if (!state.selectedTraceId || !state.currentUser) return;
    try {
      elements.btnAssignMe.disabled = true;
      elements.btnAssignMe.textContent = 'Assigning...';
      const res = await fetch(`/api/traces/${state.selectedTraceId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          assignee: state.currentUser.name,
          email: state.currentUser.email,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast('Trace successfully assigned to you in Braintrust!', 'success');
        await loadTraceDetail(state.selectedTraceId);
        await loadTraces(false);
      } else {
        showToast(data.detail || 'Failed to assign trace', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      elements.btnAssignMe.disabled = false;
      elements.btnAssignMe.innerHTML = '<span>👤</span> Assigned to Me';
    }
  });

  // Verdict Selection
  elements.verdictButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      state.activeVerdict = btn.dataset.verdict;
      updateVerdictUI();

      if (state.activeVerdict === 'pass') {
        Object.keys(state.criteriaScores).forEach((k) => {
          state.criteriaScores[k] = 1.0;
        });
        if (elements.selectFailureCategory) {
          elements.selectFailureCategory.value = 'none';
        }
        updateCriteriaUI();
      } else if (state.activeVerdict === 'fail') {
        // If all currently pass, suggest defect on policy or selected category
        const anyFailing = Object.values(state.criteriaScores).some((v) => v < 0.9);
        if (!anyFailing) {
          syncCategoryWithCriteria(elements.selectFailureCategory?.value || 'none');
        }
      }
    });
  });

  // Criteria Item Toggle Buttons
  if (elements.criteriaGroupContainer) {
    elements.criteriaGroupContainer.addEventListener('click', (e) => {
      const toggleBtn = e.target.closest('.btn-criteria-toggle');
      if (!toggleBtn) return;

      const item = toggleBtn.closest('.criteria-item');
      if (!item) return;

      const criterionKey = item.dataset.criteria;
      const val = parseFloat(toggleBtn.dataset.value);

      state.criteriaScores[criterionKey] = val;
      updateCriteriaUI();

      // If a failure is selected and overall verdict is currently pass, switch verdict to fail
      if (val < 0.9 && state.activeVerdict === 'pass') {
        state.activeVerdict = 'fail';
        updateVerdictUI();
      }

      // If all are pass and overall verdict was fail, restore pass
      const allPass = Object.values(state.criteriaScores).every((v) => v >= 0.9);
      if (allPass && state.activeVerdict === 'fail') {
        state.activeVerdict = 'pass';
        updateVerdictUI();
        if (elements.selectFailureCategory) {
          elements.selectFailureCategory.value = 'none';
        }
      }
    });
  }

  // Category Change -> sync with criteria
  if (elements.selectFailureCategory) {
    elements.selectFailureCategory.addEventListener('change', (e) => {
      syncCategoryWithCriteria(e.target.value);
    });
  }

  // Submit Review Feedback to Braintrust
  elements.btnSubmitReview.addEventListener('click', async () => {
    const comment = elements.reviewCommentInput.value.trim();
    if (!comment) {
      showToast('Please enter review commentary before submitting', 'error');
      elements.reviewCommentInput.focus();
      return;
    }

    if (!state.selectedTraceId) return;

    try {
      elements.btnSubmitReview.disabled = true;
      elements.btnSubmitReview.innerHTML = '<span>⏳</span> Syncing to Braintrust...';

      let humanReviewScore = 1.0;
      if (state.activeVerdict === 'fail') humanReviewScore = 0.0;
      else if (state.activeVerdict === 'escalate') humanReviewScore = 0.5;

      const category = elements.selectFailureCategory.value;

      const payload = {
        comment,
        scores: {
          human_review: humanReviewScore,
          ...state.criteriaScores,
        },
        tags: [
          state.activeVerdict === 'pass' ? 'pass' : (state.activeVerdict === 'escalate' ? 'escalate' : 'fail'),
          category !== 'none' ? category : 'passed_audit',
        ],
        reviewer: state.currentUser ? state.currentUser.name : 'Nick Teodori',
        category: category,
      };

      const res = await fetch(`/api/traces/${state.selectedTraceId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (res.ok) {
        showToast('Commentary and review criteria scores recorded in Braintrust!', 'success');
        elements.reviewCommentInput.value = '';
        await loadTraceDetail(state.selectedTraceId);
        await loadTraces(false);
      } else {
        showToast(data.detail || 'Failed to sync feedback to Braintrust', 'error');
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      elements.btnSubmitReview.disabled = false;
      elements.btnSubmitReview.innerHTML = '<span>🚀</span> Submit Review to Braintrust';
    }
  });
}

// Load Authenticated User Info
async function loadCurrentUser() {
  try {
    const res = await fetch('/api/me');
    if (res.ok) {
      const user = await res.json();
      state.currentUser = user;
      elements.userNameDisplay.textContent = user.name || 'Nick Teodori';
      elements.projectNameDisplay.textContent = user.project || 'meridian-pay-support';
      if (user.name) {
        const initials = user.name
          .split(' ')
          .map((n) => n[0])
          .join('')
          .toUpperCase()
          .slice(0, 2);
        elements.userAvatar.textContent = initials;
      }
    }
  } catch (err) {
    console.error('Error fetching user info:', err);
  }
}

// Load Traces List
async function loadTraces(autoSelectFirst = true) {
  try {
    elements.traceList.innerHTML = `
      <div class="inspector-empty" style="padding: 24px 12px;">
        <span>Loading traces from Braintrust...</span>
      </div>
    `;

    const params = new URLSearchParams({
      assignee: state.assigneeFilter,
      status: state.statusFilter,
      limit: 60,
    });

    if (state.searchQuery) {
      params.append('search', state.searchQuery);
    }

    const res = await fetch(`/api/traces?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load traces');

    const data = await res.json();
    state.traces = data.traces || [];
    state.stats = data.stats || {};

    updateHeaderStats(data.stats);
    renderTraceList();

    if (autoSelectFirst && state.traces.length > 0) {
      if (!state.selectedTraceId || !state.traces.some((t) => t.id === state.selectedTraceId)) {
        loadTraceDetail(state.traces[0].id);
      }
    } else if (state.traces.length === 0) {
      showEmptyInspector();
    }
  } catch (err) {
    console.error('Error loading traces:', err);
    elements.traceList.innerHTML = `
      <div class="inspector-empty" style="padding: 24px 12px; color: var(--color-danger);">
        <span>Error loading traces from Braintrust.</span>
      </div>
    `;
  }
}

// Update Top Bar Stats
function updateHeaderStats(stats = {}) {
  elements.statAssignedCount.textContent = stats.assigned_to_me ?? 0;
  elements.statUnassignedCount.textContent = stats.unassigned ?? 0;
  elements.statFailingCount.textContent = stats.failing_evals ?? 0;
  elements.statNeedsReviewCount.textContent = stats.needs_review ?? 0;
}

// Render Trace Cards in Left Pane
function renderTraceList() {
  if (state.traces.length === 0) {
    elements.traceList.innerHTML = `
      <div class="inspector-empty" style="padding: 40px 16px;">
        <span>No traces match current filters.</span>
      </div>
    `;
    return;
  }

  elements.traceList.innerHTML = '';
  state.traces.forEach((trace) => {
    const isSelected = trace.id === state.selectedTraceId;
    const card = document.createElement('div');
    card.className = `trace-card ${isSelected ? 'selected' : ''}`;
    card.dataset.traceId = trace.id;

    const timeAgo = formatTimeAgo(trace.created);
    const multiTurnText = trace.turn_count > 1 ? `💬 ${trace.turn_count} turns` : `⚡ 1 turn`;
    const isThread = trace.is_thread || trace.turn_count > 1;

    let assigneeBadge = '';
    if (trace.reviewer) {
      assigneeBadge = `<span class="badge badge-assigned" title="Assigned to ${escapeHtml(trace.reviewer)}">👤 ${escapeHtml(trace.reviewer)}</span>`;
    } else {
      assigneeBadge = `<span class="badge badge-unassigned">⭕ Unassigned</span>`;
    }

    let statusBadge = '';
    if (trace.is_failing) {
      statusBadge = `<span class="badge badge-fail">🚨 Policy Fail</span>`;
    } else {
      statusBadge = `<span class="badge badge-pass">✅ Passed</span>`;
    }

    const companyDisplay = trace.company_name || 'Commercial Support';
    const accountDisplay = trace.account_id ? `<span class="account-tag">${escapeHtml(trace.account_id)}</span>` : '';

    card.innerHTML = `
      <div class="trace-card-header">
        <div class="trace-company">${escapeHtml(companyDisplay)} ${accountDisplay}</div>
        <span class="trace-time">${timeAgo}</span>
      </div>
      <div class="trace-ticket">${escapeHtml(trace.ticket || 'Support inquiry')}</div>
      <div class="trace-meta-row">
        <span class="badge ${isThread ? 'badge-thread' : 'badge-single'}">${multiTurnText}</span>
        ${statusBadge}
        ${assigneeBadge}
      </div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.trace-card').forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
      loadTraceDetail(trace.id);
    });

    elements.traceList.appendChild(card);
  });
}

// Load Single Trace Details
async function loadTraceDetail(traceId) {
  state.selectedTraceId = traceId;
  try {
    elements.inspectorEmptyState.style.display = 'none';
    elements.inspectorContent.style.display = 'flex';
    elements.inspectorContent.style.opacity = '0.5';
    if (elements.reviewSidebarContent) elements.reviewSidebarContent.style.display = 'flex';
    if (elements.reviewSidebarEmpty) elements.reviewSidebarEmpty.style.display = 'none';

    const res = await fetch(`/api/traces/${traceId}`);
    if (!res.ok) throw new Error('Failed to load trace detail');

    const detail = await res.json();
    state.selectedTraceDetail = detail;
    renderTraceDetail(detail);
  } catch (err) {
    console.error('Error fetching trace detail:', err);
    showToast('Failed to load trace details', 'error');
  } finally {
    elements.inspectorContent.style.opacity = '1';
  }
}

// Render Trace Details in Right Pane
function renderTraceDetail(detail) {
  const meta = detail.metadata || {};
  const scores = detail.scores || {};

  // Header
  const title = meta.company_name ? `${meta.company_name} Support Thread` : (detail.summary.initial_ticket || 'Inquiry Review');
  elements.traceDetailTitle.textContent = title;
  elements.traceDetailId.textContent = `ID: ${detail.id.slice(0, 12)}...`;
  elements.traceDetailAccount.textContent = meta.account_id ? `Account: ${meta.account_id}` : 'Account: N/A';
  elements.traceDetailTier.textContent = `Tier: ${meta.customer_tier || 'Core'}`;
  elements.traceDetailTime.textContent = new Date(detail.created).toLocaleString();

  // Braintrust Link
  elements.btnOpenBraintrust.href = detail.braintrust_url || '#';

  // Assignee Button Status
  if (detail.is_assigned_to_me) {
    elements.btnAssignMe.innerHTML = '<span>✅</span> Assigned to You';
    elements.btnAssignMe.classList.add('assigned-active');
  } else {
    elements.btnAssignMe.innerHTML = '<span>👤</span> Assign to Me';
    elements.btnAssignMe.classList.remove('assigned-active');
  }

  // Tags Bar
  elements.traceDetailTags.innerHTML = '';
  if (meta.topic_name || meta.topic) {
    elements.traceDetailTags.innerHTML += `<span class="badge badge-thread">📂 Topic: ${escapeHtml(meta.topic_name || meta.topic)}</span>`;
  }
  if (meta.pattern_name || meta.pattern) {
    elements.traceDetailTags.innerHTML += `<span class="badge badge-single">🔄 Pattern: ${escapeHtml(meta.pattern_name || meta.pattern)}</span>`;
  }
  if (detail.reviewer) {
    elements.traceDetailTags.innerHTML += `<span class="badge badge-assigned">👤 Reviewer: ${escapeHtml(detail.reviewer)}</span>`;
  }
  (detail.tags || []).forEach((t) => {
    if (!t.startsWith('topic:') && !t.startsWith('pattern:') && !t.startsWith('assigned:')) {
      elements.traceDetailTags.innerHTML += `<span class="badge badge-single">#${escapeHtml(t)}</span>`;
    }
  });

  // SECTION 1: System Evaluations
  renderSystemEvaluations(detail.system_evaluations);

  // SECTION 2: Multi-Turn Conversation & LLM Decisions Timeline
  renderTurnsTimeline(detail.turns);

  // Pre-fill existing human review scores if recorded on trace
  const criteriaKeys = [
    'human_policy_compliance',
    'human_date_accuracy',
    'human_contradiction_free',
    'human_escalation_appropriate',
    'human_citation_quality',
    'human_tone_and_conciseness',
    'human_tool_execution',
  ];

  let hasCustomScores = false;
  criteriaKeys.forEach((k) => {
    if (scores[k] !== undefined) {
      state.criteriaScores[k] = Number(scores[k]);
      hasCustomScores = true;
    } else {
      state.criteriaScores[k] = detail.is_failing ? 0.0 : 1.0;
    }
  });

  // Overall verdict
  if (scores.human_review !== undefined) {
    const hr = Number(scores.human_review);
    if (hr >= 0.9) state.activeVerdict = 'pass';
    else if (hr >= 0.4) state.activeVerdict = 'escalate';
    else state.activeVerdict = 'fail';
  } else if (detail.is_failing) {
    state.activeVerdict = 'fail';
  } else {
    state.activeVerdict = 'pass';
  }

  // Pre-fill failure category if recorded or pattern detected
  const initialCategory =
    meta.failure_category ||
    (meta.pattern && ['circular_friction', 'policy_drift_under_pressure', 'context_loss'].includes(meta.pattern)
      ? meta.pattern
      : 'none');
  if (elements.selectFailureCategory) {
    elements.selectFailureCategory.value = initialCategory;
  }

  if (!hasCustomScores && initialCategory !== 'none') {
    syncCategoryWithCriteria(initialCategory, false);
  }

  // Pre-fill review notes if recorded
  if (meta.review_notes) {
    elements.reviewCommentInput.value = meta.review_notes;
  } else if (detail.comments && detail.comments.length > 0) {
    const lastComment = detail.comments[detail.comments.length - 1];
    elements.reviewCommentInput.value = lastComment.text || '';
  } else {
    elements.reviewCommentInput.value = '';
  }

  updateVerdictUI();
  updateCriteriaUI();
}

// Render System Evaluations Scorecard
function renderSystemEvaluations(systemEvals) {
  const banner = elements.evalDiagnosticBanner;
  if (systemEvals.diagnostic_alert) {
    banner.style.display = 'flex';
    banner.className = `eval-alert-banner ${systemEvals.diagnostic_alert.type}`;
    banner.innerHTML = `
      <div style="font-size: 1.25rem;">⚠️</div>
      <div>
        <div class="eval-alert-title">${escapeHtml(systemEvals.diagnostic_alert.title)}</div>
        <div>${escapeHtml(systemEvals.diagnostic_alert.description)}</div>
      </div>
    `;
  } else {
    banner.style.display = 'none';
  }

  elements.evalCardsGrid.innerHTML = '';
  (systemEvals.eval_cards || []).forEach((card) => {
    const isPass = card.status === 'pass';
    const percent = Math.round(card.score * 100);

    const cardEl = document.createElement('div');
    cardEl.className = `eval-metric-card status-${card.status}`;
    cardEl.innerHTML = `
      <div class="metric-header">
        <span class="metric-name">${escapeHtml(card.label)}</span>
        <span class="metric-score-value ${isPass ? 'pass' : 'fail'}">${card.score.toFixed(2)}</span>
      </div>
      <div class="metric-progress-bar">
        <div class="metric-progress-fill ${isPass ? 'pass' : 'fail'}" style="width: ${percent}%"></div>
      </div>
      <div class="metric-explanation">${escapeHtml(card.explanation)}</div>
    `;
    elements.evalCardsGrid.appendChild(cardEl);
  });
}

// Render Multi-Turn Timeline with Explicit LLM Decisions & Tools
function renderTurnsTimeline(turns = []) {
  elements.turnsTimeline.innerHTML = '';

  if (!turns || turns.length === 0) {
    elements.turnsTimeline.innerHTML = `
      <div class="inspector-empty" style="padding: 24px;">
        <span>No conversation turns captured for this trace.</span>
      </div>
    `;
    return;
  }

  turns.forEach((turn, idx) => {
    const turnBlock = document.createElement('div');
    turnBlock.className = 'turn-block';

    const totalTurns = turns.length;
    const turnMetricsText = turn.metrics && turn.metrics.duration ? `${(turn.metrics.duration * 1000).toFixed(0)} ms` : '';

    // Customer Input Box
    const userBoxHtml = turn.user_message
      ? `
        <div class="user-input-box">
          <div class="user-box-label">
            <span>👤</span> Customer Input (Turn ${turn.turn_index})
          </div>
          <div class="user-box-content">${escapeHtml(turn.user_message)}</div>
        </div>
      `
      : '';

    // LLM Reasoning Box ("Why it made them")
    let reasoningBoxHtml = '';
    if (turn.reasoning) {
      reasoningBoxHtml = `
        <div class="llm-reasoning-box">
          <div class="reasoning-header">
            <span class="reasoning-label">
              <span>🧠</span> LLM Decision & Reasoning
            </span>
            <span class="model-pill">${escapeHtml(turn.model || 'LLM Model')}</span>
          </div>
          <div class="reasoning-content">“${escapeHtml(turn.reasoning)}”</div>
        </div>
      `;
    }

    // Tool Invocations
    let toolsHtml = '';
    if (turn.tools && turn.tools.length > 0) {
      toolsHtml = `
        <div class="tool-calls-container">
          ${turn.tools
            .map(
              (tool) => `
            <div class="tool-card">
              <div class="tool-header">
                <span class="tool-name-badge">
                  <span>⚙️</span> Tool Execution: <strong>${escapeHtml(tool.name)}</strong>
                </span>
              </div>
              <div class="tool-payload-view">
                <div class="payload-column">
                  <div class="payload-label">Input Arguments</div>
                  <pre>${escapeHtml(JSON.stringify(tool.input, null, 2))}</pre>
                </div>
                <div class="payload-column">
                  <div class="payload-label">Return Value</div>
                  <pre>${escapeHtml(JSON.stringify(tool.output, null, 2))}</pre>
                </div>
              </div>
            </div>
          `
            )
            .join('')}
        </div>
      `;
    }

    // Assistant Reply Box
    const assistantBoxHtml = turn.assistant_reply
      ? `
        <div class="assistant-reply-box">
          <div class="assistant-box-label">
            <span>💬</span> Assistant Response
          </div>
          <div class="assistant-box-content">${escapeHtml(turn.assistant_reply)}</div>
        </div>
      `
      : '';

    turnBlock.innerHTML = `
      <div class="turn-header">
        <div class="turn-badge">
          <div class="turn-number-circle">${turn.turn_index}</div>
          <span>Turn ${turn.turn_index} of ${totalTurns}</span>
        </div>
        <div class="turn-metrics">${escapeHtml(turnMetricsText)}</div>
      </div>
      ${userBoxHtml}
      ${reasoningBoxHtml}
      ${toolsHtml}
      ${assistantBoxHtml}
    `;

    elements.turnsTimeline.appendChild(turnBlock);
  });
}

// Empty State View
function showEmptyInspector() {
  elements.inspectorEmptyState.style.display = 'flex';
  elements.inspectorContent.style.display = 'none';
  if (elements.reviewSidebarContent) elements.reviewSidebarContent.style.display = 'none';
  if (elements.reviewSidebarEmpty) elements.reviewSidebarEmpty.style.display = 'flex';
}

// Toast Notifications
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : '❌'}</span>
    <span>${escapeHtml(message)}</span>
  `;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// Criteria & Verdict Synchronization Helpers
function syncCategoryWithCriteria(category, updateVerdict = true) {
  // Reset all criteria to 1.0 first
  Object.keys(state.criteriaScores).forEach((k) => {
    state.criteriaScores[k] = 1.0;
  });

  if (category === 'relative_date_resolution') {
    state.criteriaScores.human_date_accuracy = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (
    category === 'policy_drift_under_pressure' ||
    category === 'missing_escalation_money_moving' ||
    category === 'unauthorized_refund'
  ) {
    state.criteriaScores.human_policy_compliance = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (category === 'circular_friction' || category === 'tone_or_length') {
    state.criteriaScores.human_tone_and_conciseness = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (category === 'citation_to_wrong_doc') {
    state.criteriaScores.human_citation_quality = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (category === 'tool_arg_malformed') {
    state.criteriaScores.human_tool_execution = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (category === 'hallucinated_policy') {
    state.criteriaScores.human_contradiction_free = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (category === 'context_loss') {
    state.criteriaScores.human_tone_and_conciseness = 0.0;
    if (updateVerdict) state.activeVerdict = 'fail';
  } else if (category === 'none') {
    if (updateVerdict) state.activeVerdict = 'pass';
  }

  if (updateVerdict) updateVerdictUI();
  updateCriteriaUI();
}

function updateVerdictUI() {
  elements.verdictButtons.forEach((b) => {
    b.classList.remove('selected-pass', 'selected-escalate', 'selected-fail');
    if (b.dataset.verdict === state.activeVerdict) {
      if (state.activeVerdict === 'pass') b.classList.add('selected-pass');
      else if (state.activeVerdict === 'escalate') b.classList.add('selected-escalate');
      else if (state.activeVerdict === 'fail') b.classList.add('selected-fail');
    }
  });
}

function updateCriteriaUI() {
  let passCount = 0;
  const totalCount = 7;

  document.querySelectorAll('.criteria-item').forEach((item) => {
    const key = item.dataset.criteria;
    const val = state.criteriaScores[key] ?? 1.0;
    const isPass = val >= 0.9;
    if (isPass) passCount++;

    item.classList.toggle('is-compliant', isPass);
    item.classList.toggle('has-failure', !isPass);

    const passBtn = item.querySelector('.btn-criteria-toggle[data-value="1.0"]');
    const failBtn = item.querySelector('.btn-criteria-toggle[data-value="0.0"]');

    if (passBtn && failBtn) {
      passBtn.classList.toggle('active-pass', isPass);
      failBtn.classList.toggle('active-fail', !isPass);
    }
  });

  if (elements.criteriaSummaryBadge) {
    if (passCount === totalCount) {
      elements.criteriaSummaryBadge.textContent = `${totalCount} / ${totalCount} Passing`;
      elements.criteriaSummaryBadge.classList.remove('has-defects');
    } else {
      const fails = totalCount - passCount;
      elements.criteriaSummaryBadge.textContent = `${passCount} / ${totalCount} Passing (${fails} Defect${fails > 1 ? 's' : ''})`;
      elements.criteriaSummaryBadge.classList.add('has-defects');
    }
  }
}

// Helpers
function escapeHtml(str) {
  if (typeof str !== 'string') return String(str || '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatTimeAgo(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec < 60) return 'Just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
