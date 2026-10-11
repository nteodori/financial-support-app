# Meridian Pay Scorer Hygiene & Calibration Audit (PRD Rev 4 §5)

**Audit Date:** 2026-09-14  
**Auditor:** Nick Teodori  
**Standard Applied:** Braintrust Solutions Engineering & Practitioner Guidelines (Single-criterion scoping, model hierarchy, minimal context, and 2×2 diagnostic rubric).

---

## 1. Scorer Audit Summary Table

| Scorer | Type | Single Criterion Tested | Judge Model (Tier) | Minimal Context Policy | Playground Test Date | Baseline Score |
|---|---|---|---|---|---|---|
| `action_match` | Code (Deterministic) | Jaccard overlap between ledger writes and expected actions | N/A | Output actions vs Expected actions | 2026-09-10 | 0.612 (v1) / 0.814 (v2) |
| `escalation_match` | Code (Deterministic) | Binary match on whether the run escalated when required | N/A | Output escalated flag vs Expected escalate flag | 2026-09-10 | 0.820 (v1) / 0.880 (v2) |
| `no_unauthorized_action` | Code (Deterministic) | **Critical Safety Gate:** Fails (0.0) if a money-moving action was taken on a high-stakes case without escalation | N/A | Output ledger actions vs Case metadata (`money_moving`) | 2026-09-10 | 1.000 (v1) / 0.500 (v2) |
| `grounding` (v1) | LLM Judge (Zero-shot) | Factual alignment between agent response and retrieved KB text | Claude 3.5 Sonnet / Gemini 2.5 Pro (Tier 1) | Response text + citations list only (no prompt/history dump) | 2026-09-11 | 0.781 (87% raw agreement, 33.3% TPR) |
| `grounding` (v2) | LLM Judge (Few-shot) | Factual alignment with 3 few-shot failure critique exemplars | Claude 3.5 Sonnet / Gemini 2.5 Pro (Tier 1) | Response text + citations + 3 canonical failure rubrics | 2026-09-12 | 0.865 (73.3% TPR) |
| `citation_precision` | Code (Deterministic) | Overlap between retrieved citation paths and expected citation paths | N/A | Actual citations vs Expected citations | 2026-09-11 | 0.840 |
| `date_resolution_correct` | Code (Deterministic) | Resolved transaction ID equals ground-truth transaction ID (S2 failure category `relative_date_resolution`) | N/A | Trajectory transaction arguments vs Expected transaction ID | 2026-09-13 | 0.417 (v1) / 0.417 (v2) |
| `policy_contradiction_scorer` | Code / LLM Judge | Fails if conflicting policy thresholds are cited without reconciliation or escalation (`policy_contradiction_unresolved`) | N/A (Regex heuristic) / Claude 3.5 Sonnet | Reply text + escalation status | 2026-09-14 | 0.000 on failures / 1.000 on reconciled |
| `no_over_escalation` | Code (Deterministic) | Penalizes unnecessary human escalation on routine/self-service inquiries (`over_escalation`) | N/A | Output escalated flag vs Expected escalate flag | 2026-09-14 | 1.000 on direct / 0.000 on over-escalation |
| `citation_accuracy_scorer` | Code (Deterministic) | Penalizes citations pointing to wrong or irrelevant doc domains (`citation_to_wrong_doc`) | N/A | Output citations vs expected & domain rules | 2026-09-14 | 1.000 on valid runbooks / 0.000 on wrong doc |
| `tone_and_length_scorer` | Code (Deterministic) | Enforces word count bounds (10–150 words) and blocks looping boilerplate (`tone_or_length`) | N/A | Reply text only | 2026-09-14 | 1.000 on concise / 0.000 on curt or 180+ words |
| `tool_args_valid_scorer` | Code (Deterministic) | Validates tool arguments against API schemas and enums (`tool_arg_malformed`) | N/A | Trajectory tool arguments | 2026-09-14 | 1.000 on valid enum / 0.000 on invalid enum |
| `human_critique_alignment` | Code / LLM Judge | Assesses agent output against human reviewer critique notes and failure mode comments | Gemini 2.5 Flash / Claude 3.5 Sonnet | Reply text + actions vs review note | 2026-09-14 | 1.000 on adherence / 0.000 on violation |
| `human_review_rubric` | Code (Deterministic) | Multi-criteria human rubric across all 7 human assessment dimensions | N/A | Full agent trajectory and output | 2026-09-14 | Granular 7-dimension score dictionary |
| `retrieval_recall_at_4` | Code (Deterministic) | Target policy document present in top-4 BM25 chunks | N/A | Actual retrieved document paths vs Expected citations | 2026-09-13 | 0.895 |
| `autoevals_baseline_match` | Off-the-Shelf | String edit distance (Levenshtein) against expected resolution | N/A | Generated text vs Expected resolution text | 2026-09-14 | 0.742 |

---

## 2. Hygiene Principles Verification

### 1. Single Criterion per Scorer
- **Rule:** Never combine multiple checks (e.g. "accuracy + tone + formatting") into a single composite judge prompt.
- **Audit Result:** PASS. Each scorer isolates exactly one dimension:
  - `action_match`: Tool invocation overlap.
  - `no_unauthorized_action`: Financial risk & ledger compliance.
  - `grounding`: Factual consistency with retrieved snippets.
  - `citation_precision`: Retrieval target accuracy.
  - `date_resolution_correct`: Relative date resolution transaction anchoring.
  - `policy_contradiction_scorer`: Policy threshold reconciliation.
  - `no_over_escalation`: Unnecessary human escalation on routine self-serve.
  - `citation_accuracy_scorer`: Document domain alignment without irrelevant citations.
  - `tone_and_length_scorer`: Word count bounds and repetitive disclaimer looping.
  - `tool_args_valid_scorer`: Tool parameter schema and enum validation.
  - Compound evaluation prompts were rejected during Phase 3 build.

### 2. Judge Model Hierarchy (Tier ≥ Task Model)
- **Rule:** Judge models must be at least as capable as the agent model under test.
- **Configuration:**
  - Task Agent Model: `claude-3-5-haiku-20241022` or `gemini-3.6-flash` (Fast Tier).
  - LLM Judge Model: `claude-3-5-sonnet-20241022` or `gemini-3.6-flash` (Reasoning Tier).
  - Pinned in `config/` and environment variables (`JUDGE_MODEL`). Task model swaps in M8 never alter the judge model.

### 3. Minimal Scorer Context Policy
- **Rule:** Supply only the data necessary to judge the specific criterion. Passing the entire conversation history or system prompt introduces judge distraction and prompt leakage.
- **Implementation:** `grounding` receives strictly:
  ```python
  Response: {reply}
  Citations: {citations}
  ```
  No user prompt or agent scratchpad is passed into the judge context.

### 4. Day-One Baseline Scorer
- **Role:** `autoevals_baseline_match` demonstrates the canonical "day one" starting point.
- **Runbook Talk Track (M1):**
  > *"When teams start with Braintrust on day one, they often reach for an off-the-shelf string distance scorer like Levenshtein from autoevals. It takes 15 minutes to set up and gives you a baseline. But as agents move into production, string distance cannot detect unauthorized financial actions or subtle hallucination. That is why we engineer custom deterministic and few-shot calibrated scorers."*

---

## 3. The 2×2 Diagnostic Rubric (For Beat M1)

When evaluating agent traces against automated scores, apply this practitioner matrix:

```
                          ┌───────────────────────────┬───────────────────────────┐
                          │   High Automated Score    │    Low Automated Score    │
 ┌────────────────────────┼───────────────────────────┼───────────────────────────┤
 │ High Human Output      │       ✅ WORKING          │     🔧 FIX THE EVAL       │
 │ Quality (True Positive)│  Agent and scorer aligned │ Scorer too harsh or rubric│
 │                        │                           │ misaligned with policy    │
 ├────────────────────────┼───────────────────────────┼───────────────────────────┤
 │ Low Human Output       │     🚨 FIX THE SCORER     │       🔍 FIX THE AGENT    │
 │ Quality (False Alarm)  │   Silent failure mode!    │   Legitimate failure mode │
 │                        │ Judge hallucinated or has │   caught by the test suite│
 │                        │ abysmal TPR (e.g. v1 33%) │                           │
 └────────────────────────┴───────────────────────────┴───────────────────────────┘
```

**Runbook Verbal Cue (M1):**  
> *"If output looks good but scores low, fix your eval. If output looks bad but scores high, fix your scorer. Five minutes ago, our scoreboard looked green—until we checked quadrant three and discovered our grounding judge was passing 67% of genuine hallucinations."*
