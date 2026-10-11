# Braintrust Multi-Turn Conversation Threads Guide

This guide explains how multi-turn conversation logs are instrumented, structured, and analyzed in **Braintrust**, leveraging the **Thread View**, **Topics (semantic clustering)**, and **Pattern discovery (Loop & BTQL)**.

---

## 1. How Braintrust Threads Work

In production AI customer support, single-turn evaluation often fails to capture realistic failure modes like context loss, circular loops, or safety drift under pressure. Braintrust supports multi-turn conversations natively through its **Thread View**.

### 1.1 The Thread Preprocessor
When you view a trace in the Braintrust Logs tab:
1. Selecting the **Trace** tab displays the raw span hierarchy.
2. Clicking the **Thread** icon (or choosing **Thread** from the preprocessor dropdown) activates Braintrust's built-in **Thread Preprocessor**.
3. The preprocessor walks the span tree, extracts messages from span `input` and `output` objects, deduplicates them across consecutive turns, and renders an interactive, chronological chat transcript with user bubbles, assistant reasoning, expandable tool executions, and scores.

---

## 2. Recommended Instrumentation Hierarchy

To ensure Braintrust automatically identifies and renders multi-turn sessions cleanly, wrap the entire conversation in a root conversation span, with child spans for each turn, LLM reasoning, and tool executions:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ROOT SPAN: meridian_support_thread (type: "task")                                     │
│ • name: "meridian_support_thread"                                                      │
│ • input: {"initial_ticket": "...", "account_id": "ACC-4081", "turn_count": 3}         │
│ • metadata: {"thread_id": "TH-...", "is_thread": true, "topic": "...", "pattern": ...}│
│ • scores: {"resolution_success": 1.0, "no_unauthorized_action": 1.0, ...}             │
│ • tags: ["thread", "multi-turn", "topic:fraud_dispute", "pattern:mandatory_escalation"]│
└────────────────────────────────────────────────────────────────────────────────────────┘
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               ▼                            ▼                            ▼
  ┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐
  │ TURN 1 SPAN (task)       │ │ TURN 2 SPAN (task)       │ │ TURN 3 SPAN (task)       │
  │ • name: "turn_1"         │ │ • name: "turn_2"         │ │ • name: "turn_3"         │
  │ • input: {"turn_index":1}│ │ • input: {"turn_index":2}│ │ • input: {"turn_index":3}│
  │                          │ │                          │ │                          │
  │ ├─ claude_reasoning(llm) │ │ ├─ claude_reasoning(llm) │ │ ├─ claude_reasoning(llm) │
  │ │  input.messages:       │ │ │  input.messages:       │ │ │  input.messages:       │
  │ │    [system, user1]     │ │ │    [..., asst1, user2] │ │ │    [..., asst2, user3] │
  │ │  output.choices:       │ │ │  output.choices:       │ │ │  output.choices:       │
  │ │    assistant reply 1   │ │ │    assistant reply 2   │ │ │    assistant reply 3   │
  │ └─ tool: get_account     │ │ └─ tool: replace_card    │ │ └─ tool: search_kb       │
  └──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘
```

### 2.1 Schema Requirements for Thread View
- **Span Type:** Child LLM spans must have `type="llm"` or `span_attributes={"type": "llm", "model": ...}`.
- **Message Accumulation:** The LLM span's `input` must contain a `"messages"` list:
  ```json
  {
    "messages": [
      {"role": "system", "content": "You are the Meridian Pay support assistant..."},
      {"role": "user", "content": "We noticed an unrecognized charge..."},
      {"role": "assistant", "content": "Because this exceeds our $1,000 threshold..."}
    ]
  }
  ```
- **Assistant Response:** The LLM span's `output` should follow standard provider or OpenAI format:
  ```json
  {
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "...",
          "tool_calls": [{"name": "replace_card", "args": {...}}]
        },
        "finish_reason": "stop"
      }
    ]
  }
  ```

---

## 3. Discoverability by Topics (Semantic Clustering)

Braintrust's **Topics** feature automatically clusters high volumes of traces into themes using an LLM facet-extraction and clustering pipeline (UMAP + HDBSCAN).

### 3.1 Taxonomy of Topics
Our multi-turn thread generator structures logs into 6 core commercial fintech topics:

| Topic ID | Topic Name | Description | Key Policy / Docs |
|---|---|---|---|
| `fraud_dispute` | Unrecognized Charge / Fraud | High-stakes disputes, card freezes, fraud investigation routing | `policy/fraud-thresholds.md` |
| `duplicate_charge` | Duplicate Billing Dispute | Identical ledger debits on same merchant/day | `policy/dispute-handling.md` |
| `credit_limit_bump` | Credit Limit Increase | Emergency ad spend/payroll limit bumps, financial statement reviews | `policy/limit-increase-policy.md` |
| `card_management` | Card Replacement & Provisioning | Damaged chip, expedited courier dispatch, instant virtual cards | `cards/replacement.md` |
| `wire_transfer_ops` | Wire Transfer & Settlement Ops | SWIFT MT103 receipts, IMAD tracking, delayed intermediary clears | `policy/wire-settlement.md` |
| `developer_api_webhook` | Developer API & Webhooks | 401 Bearer tokens, HMAC-SHA256 signature verification | `policy/api-troubleshooting.md` |

### 3.2 Metadata for Topic Facets
Every root thread span includes explicit metadata:
```python
metadata = {
    "thread_id": "TH-ACC-1101-264ccb78",
    "is_thread": True,
    "topic": "fraud_dispute",
    "topic_name": "Unrecognized Charge / Fraud",
    "customer_tier": "Scale",
    "is_money_moving": True,
}
```

---

## 4. Discoverability by Patterns (Loop, Saved Views & BTQL)

While Topics organizes logs into domain themes, **Patterns** surface recurring behavioral dynamics and failure modes across multi-turn interactions.

### 4.1 Taxonomy of Interaction Patterns

| Pattern ID | Pattern Name | Conversational Dynamic | Target Scores |
|---|---|---|---|
| `multi_turn_resolution` | Clean Multi-Turn Clarification | Incomplete query ➜ Agent asks targeted clarification ➜ User answers ➜ Tool executed ➜ Resolved. | `resolution_success: 1.0`<br>`no_unauth: 1.0` |
| `mandatory_escalation` | High-Stakes Escalation Flow | Out-of-policy financial request (> $1,000) ➜ Agent cites policy ➜ Obtains consent ➜ Escalate to Tier-3 queue. | `resolution_success: 1.0`<br>`no_unauth: 1.0` |
| `circular_friction` | Repetitive Circular Friction | User requests exception ➜ Agent repeats identical canned refusal ➜ Customer frustration escalates. | `resolution_success: 0.0`<br>`efficiency: 0.25` |
| `policy_drift_under_pressure` | Compliance Drift Under Pressure | Turn 1: Agent refuses ➜ Turn 2: User threatens churn ➜ Turn 3: Agent executes unauthorized money override. | `resolution_success: 0.5`<br>`no_unauth: 0.0` |
| `context_loss` | Multi-Turn Memory / Context Loss | User provides ID in Turn 1 ➜ Agent in Turn 2 forgets ID and re-asks ➜ Customer frustration. | `resolution_success: 0.7`<br>`efficiency: 0.40` |

---

## 5. Discovering and Querying Threads

### 5.1 Querying with BTQL in Braintrust

You can run BTQL queries in the Braintrust UI or via the `/btql` API:

#### Find All Multi-Turn Threads
```sql
SELECT
  id,
  metadata.thread_id,
  metadata.topic,
  metadata.pattern,
  metadata.turn_count,
  scores.resolution_success,
  scores.no_unauthorized_action
FROM project_logs("meridian-pay-support")
WHERE metadata.is_thread = true
ORDER BY created DESC
LIMIT 50
```

#### Find Circular Friction Threads
```sql
SELECT
  id,
  metadata.thread_id,
  metadata.company_name,
  metrics.total_turns,
  scores.conversational_efficiency
FROM project_logs("meridian-pay-support")
WHERE metadata.pattern = "circular_friction"
ORDER BY scores.conversational_efficiency ASC
```

#### Find Compliance Drifts Under Pressure (Unauthorized Overrides)
```sql
SELECT
  id,
  metadata.thread_id,
  metadata.company_name,
  metadata.topic,
  scores.no_unauthorized_action
FROM project_logs("meridian-pay-support")
WHERE metadata.pattern = "policy_drift_under_pressure"
  AND scores.no_unauthorized_action = 0.0
```

### 5.2 Discovering with Braintrust Loop

In the Braintrust **Loop** automation panel, you can use these prompts to discover patterns across your multi-turn logs:

- *"Find conversation threads where the customer had to repeat their account or transaction ID because the agent lost context."*
- *"Identify multi-turn sessions where customer sentiment turned negative after the agent refused a request without offering human escalation."*
- *"Cluster conversation threads by customer tier (Scale vs Growth vs Core) and compare average turn counts to resolution."*

---

## 6. How to Seed Threads

Run the multi-turn thread generator:

```bash
# Seed 30 realistic threads across all topics and patterns
python3 scripts/seed_threads.py --count 30

# Filter specifically to Fraud Disputes
python3 scripts/seed_threads.py --count 10 --topic fraud_dispute

# Filter specifically to Circular Friction patterns
python3 scripts/seed_threads.py --count 10 --pattern circular_friction

# Run dry-run test without writing to Braintrust
python3 scripts/seed_threads.py --dry-run --count 10
```

Or using Makefile:
```bash
make threads
```

View the seeded threads directly in your Braintrust project:
```
https://www.braintrust.dev/app/NTeodori/p/meridian-pay-support/logs
```
In any row, open the **Trace** viewer and toggle the **Thread** icon to inspect the conversation.
