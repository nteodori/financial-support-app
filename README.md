# Meridian Pay Support Agent — Braintrust Eval & Monitoring Demo Harness (Rev 4)

> **Workload:** Tier 2 AI Customer Support Agent for a commercial card fintech (**Meridian Pay**)  
> **Evaluation & Observability Platform:** [Braintrust](https://www.braintrust.dev)  
> **Use Case:** 10–14 minute live customer demo role-play and enterprise evaluation showcase  
> **Owner:** Nick Teodori

---

## 🎯 Executive Overview

This repository provides the complete production-grade workload and evaluation harness for demonstrating **Braintrust** in an enterprise sales / technical architecture role-play.

Rather than a static vendor dashboard tour, this harness is architected around **practitioner discipline** (drawing on error analysis methodologies from Hamel Husain & Shreya Shankar at [hamel.dev](https://hamel.dev) and official Braintrust solutions engineering patterns):

1. **The 7-Minute Core Spine (S1–S3)**:
   - **S1 (The Working Agent & Telemetry):** Live agent execution on an arbitrary ticket with wrapped client metrics, tool spans, root span schema parity, and user feedback events.
   - **S2 (Error Analysis & The Flywheel Close):** 60 open-coded human audit notes revealing that the #1 production failure is an operational date-math bug (`relative_date_resolution`, 34.3% of failures). Followed by the **Flywheel Close**: one-click promotion of those 12 spans into the evaluation suite (`make flywheel`, 50 -> 62 cases) with a new deterministic scorer (`date_resolution_correct`).
   - **S3 (Loop Optimizer & CI Property Gate):** An AI prompt optimizer (Loop) tasked with maximizing aggregate score naturally discovers Goodhart's Law—it suppresses escalations to boost brevity and scores, causing unauthorized money movements. Blocked by a property-based CI gate (`scripts/gate.py`) with Exit Code 1 until `v3-fixed` restores compliance.

2. **Eight Swappable 2.5-Minute Capability Modules (M1–M8, Pick 2)**:
   - **M1 (Judge Validation):** Evaluates naive LLM judge against 100 human ground-truth labels. Reveals 87% raw agreement conceals an abysmal 33.3% True Positive Rate. Adding 3 few-shot human critique examples elevates TPR to 73.3% (+40.0% lift).
   - **M2 (Commercial Business Math):** Translates abstract scorer drops into dollars ($1,092,329/yr regression drag, 3.5 FTEs, and model unit economics).
   - **M6 (Online Scoring & Alerting):** Configures online scoring rules with a 20% sampling rate, span-targeted evaluation on `search_kb`, and an automation webhook alert that catches Day 9's safety regression within hours.
   - **M3 (First-Failure Attribution):** Tool-to-tool transition frequency matrix proves 100% of agent derailments happen at Step 2 or 3 (`get_account -> open_dispute/refund` without `escalate`).
   - **M7 (SME Review Loop & Launch Readiness):** Non-technical review mode on negative customer feedback (`user_feedback = 0`) and a verified 6-iteration trust curve proving 100% safety readiness before launch.
   - **M4 (Retrieval vs Generation Split):** Demonstrates 10 cases where BM25 k=4 search crowding causes grounding failures, proving the issue is retrieval recall rather than LLM hallucination.
   - **M8 (Model Swap & Cost Optimization):** Side-by-side Playground comparative layout: Claude Sonnet delivers +10.5% grounding lift for $758/year more in tokens, while safety holds at 100%.
   - **M5 (Production Trace Sampling):** Targeted active learning review surfaces failure clusters 5.2x faster than naive uniform random sampling.

---

## 🏗️ Repository Structure

```
Financial Support App/
├── config/
│   └── unit_economics.yaml         # Commercial unit economics constants (M2)
├── data/
│   ├── kb/                         # 14 Markdown policy & runbook docs
│   ├── backend.json                # 30 commercial accounts, 400 transactions, ledger
│   ├── cases.jsonl                 # 50 benchmark cases (routine, ambiguous, money-moving)
│   ├── holdout.jsonl               # 40 holdout cases (including relative-date tickets)
│   └── human_labels.jsonl          # 100 human-audited grounding labels with Nick's critiques (M1)
├── src/
│   ├── agent/
│   │   ├── loop.py                 # Multi-step agent runtime with schema parity & feedback
│   │   ├── tools.py                # 11 tool bindings reading/writing backend ledger
│   │   ├── retrieval.py            # BM25 search over data/kb/
│   │   └── prompts/                # v0_naive, v0_5, v1_baseline, v1_5, v2, v2_loop, v3_fixed
│   └── scorers/
│       ├── scorers.py              # Domain scorers + autoevals baseline match
│       ├── grounding_v1.py         # Naive zero-shot grounding judge (M1)
│       └── grounding_v2.py         # Few-shot grounding judge with 3 human critiques (M1)
├── scripts/
│   ├── preflight.py                # Automated pre-flight system check (<60s)
│   ├── push_code.py                # Code <-> platform parity sync
│   ├── flywheel_sync.py            # S2 Flywheel promotion (50 -> 62 cases)
│   ├── alert_receiver.py           # Local webhook alert receiver for M6 (port 8383)
│   ├── simulate_online_rules.py    # M6 online scoring and surge alert simulation
│   ├── run_iteration_history.py    # M7 pre-launch 6-iteration trust curve
│   ├── model_comparison.py         # M8 Playground model swap comparative layout
│   ├── export_scores_to_datadog.py # [Opt] Auxiliary Datadog custom metric exporter
│   ├── seed_annotations.py         # 60 traces open-coded notes & taxonomy table (S2)
│   ├── judge_alignment.py          # Confusion matrix & Braintrust validation logging (M1)
│   ├── business_impact.py          # Unit economics calculator & BT metadata push (M2)
│   ├── transition_matrix.py        # Tool transition failure matrix (M3)
│   ├── sample_traces.py            # Targeted active sampling vs random baseline (M5)
│   ├── gate.py                     # Property-based CI regression gate (0/1 exit code)
│   ├── push_dataset.py             # Syncs benchmark cases to Braintrust Dataset
│   └── seed_logs.py                # Populates 14-day production timeline (~500 traces)
├── tests/
│   └── test_schema_parity.py       # Validates span schema parity with dataset records
└── docs/
    ├── demo-runbook.md             # Complete step-by-step 12-minute runbook (Rev 4)
    ├── feature-verification.md     # 15-feature Braintrust documentation audit (Phase 13)
    ├── scorer-audit.md             # Single-criterion & judge hierarchy audit (Phase 18)
    ├── loop-session.md             # Loop AI prompt optimizer session transcript (S3)
    └── decisions.md                # Architectural decisions log across Revs 2–4
```

---

## ⚡ Quick Start

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Run Pre-Flight Diagnostics (<60s)
make preflight

# 3. Assert Schema Parity
make parity

# 4. Run S1 Live Agent
make live

# 5. Run S2 Error Analysis & Flywheel Close
make s2
make flywheel

# 6. Run S3 Regression Gate
make gate
make gate-pass

# 7. Run All Tests
make test
```

For the complete talk track, screen click paths, and practitioner cues, read [docs/demo-runbook.md](docs/demo-runbook.md).
