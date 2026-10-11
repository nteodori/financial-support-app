# Meridian Pay Support Agent — Braintrust Live Demo Runbook (Rev 4)

**Owner:** Nick Teodori  
**Context:** Enterprise Customer Support Agent Technical Evaluation (60-minute Discovery + Live Demo)  
**Time Allocation:** ~35 min Discovery ➜ **10–14 min Live Demo** (7-min Core Spine + two 2.5-min Swappable Modules)  
**Product Demonstrated:** [Braintrust](https://www.braintrust.dev) (Hosted UI at `https://www.braintrust.dev`)  
**Workload:** Meridian Pay — Tier 2 AI Support Agent for Commercial Card Fintech  
**Braintrust Project:** `meridian-pay-support` (Org: `NTeodori`)

---

## ⚡ Master Command Cheat Sheet

All commands execute synchronously from workspace root (`source .venv/bin/activate`):

```bash
# === PRE-FLIGHT & PLATFORM PARITY ===
make preflight         # Diagnostic self-test: APIs, datasets, prompts, scorers (<60s)
make parity            # Validate span schema parity with dataset records (Rev 4 §3.1)
make push              # Git-to-Braintrust sync for prompts, scorers, and datasets

# === CORE 7-MINUTE SPINE (Always Shown) ===
make live              # S1: Live agent run with client telemetry & feedback hook (<25s)
make s2                # S2: Inspect 60-trace human error analysis & failure taxonomy
make flywheel          # S2 Close: Promote 12 production failure spans to dataset (50 -> 62)
make gate              # S3: Run CI regression gate against v2 / Loop prompt (FAILS with Code 1)
make gate-pass         # S3: Run CI regression gate against v3-fixed (PASSES with Code 0)

# === TRACE REVIEW STUDIO & CLOSED-LOOP WORKFLOW ===
make studio            # Launch local browser Trace Review Studio (http://127.0.0.1:8000)
make demo              # Run end-to-end Trace Review Studio closed-loop demo script (<10s)
make demo-studio       # Run interactive Trace Review Studio demo script (with speaker pauses)

# === SWAPPABLE MODULES (Pick 2 Based on Discovery, 2.5 min each) ===
make align             # M1: Judge Validation (v1 vs v2 confusion matrix: 33% ➜ 73% TPR)
make impact            # M2: Commercial Business Math ($1.09M annual drag + model economics)
make m6-rules          # M6: Online Scoring & Alerting (Day 9 surge detection, 20% sampling)
make m6-alert          # M6: Start local webhook alert receiver (port 8383)
make transitions       # M3: First-Failure Step Attribution & Tool Transition Matrix
make m7-history        # M7: SME Review & Launch Readiness (6-version trust curve)
make m8-models         # M8: Model Swap Comparative Analysis (Haiku vs Sonnet Playground layout)
make sample            # M5: Production Trace Sampling (Targeted Active Learning vs Random)
make export-datadog    # [Opt] Auxiliary sync: export Braintrust daily aggregates to Datadog

# === FULL OFFLINE VERIFICATION ===
make test              # Run full end-to-end test suite across all scorers, judges, and modules
```

> [!TIP]
> For the standalone talk track and click path for the Trace Review Studio closed-loop workflow (Review story ➔ Leave comments ➔ Create eval ➔ Prompt update ➔ Pre-deployment test), see [docs/trace-review-demo-script.md](file:///Users/nick/Antigravity%20Projects/Financial%20Support%20App/docs/trace-review-demo-script.md).


---

## 🎯 Architecture: Fixed Spine (7 min) + Swappable Modules (2.5 min each)

Rather than a generic vendor dashboard tour, this demo follows practitioner discipline:
1. **The 7-Minute Spine (S1–S3)** anchors every conversation in raw traces, human error analysis, the closed-loop dataset flywheel, and property-based CI gating.
2. **Two Swappable Modules (M1–M8)** are selected dynamically in the final 30 seconds of Discovery based on buying signals from the panel:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       THE 7-MINUTE CORE SPINE                               │
│  ⏱️ 00:00 - 02:30 | S1: The Working Agent (Live Run, Telemetry, Feedback)   │
│  ⏱️ 02:30 - 05:30 | S2: Error Analysis & The Offline↔Online Flywheel         │
│  ⏱️ 05:30 - 07:30 | S3: Loop Optimizer Goodhart Moment & CI Regression Gate │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐
│  IF DISCOVERY SIGNALS RIGOR / ML:   │ │  IF DISCOVERY SIGNALS OPEX / EXEC:  │
│  M1: Judge Validation & Calibration │ │  M2: Commercial Unit Economics      │
│  M6: Online Scoring & Alerting      │ │  M7: SME Review & Launch Trust Curve│
│  M3: First-Failure Step Attribution │ │  M8: Model Swap & Cost Optimization │
│  M4: Retrieval vs Generation Split  │ │  M5: Production Trace Sampling      │
└─────────────────────────────────────┘ └─────────────────────────────────────┘
```

### Module Selection Matrix (Post-Discovery Decision)

| If the panel emphasized... | Trigger Module | Key Value Metric Demonstrated |
|---|---|---|
| *"Can we trust automated LLM judges?"* | **M1: Judge Validation** | Exposes 87% raw agreement = only 33% TPR; 3 few-shot critiques elevate TPR to 73.3%. |
| *"How do we justify the ROI / cost to leadership?"* | **M2: Business Math** | Translates 0.11 drop on `no_unauthorized_action` into $1,092,329/yr drag & 3.5 FTEs. |
| *"We find out about failures from customers; on-call is reactive"* | **M6: Online Scoring & Alerting** | Configures online rules with 20% sampling; fires alert 2 hours after bad prompt ships. |
| *"Why did our multi-step agent go off the rails?"* | **M3: First-Failure Attribution** | Isolates failure point to Step 2/3 (`get_account -> open_dispute`) without `escalate`. |
| *"We're in healthcare/fintech/tax; compliance must sign off"* | **M7: SME Review & Trust Curve** | Reviewers work in no-code UI; 6-iteration trust curve proves 100% safety before launch. |
| *"Is the agent hallucinating or is retrieval broken?"* | **M4: Retrieval vs Generation** | Proves grounding drop is driven by k=4 BM25 lexical crowding, not model capability. |
| *"New models drop every month; should we switch?"* | **M8: Model Swap & Cost** | Side-by-side Playground summary layout: Sonnet adds +10.5% grounding for $758/yr. |
| *"We have 100k production traces—what do we audit?"* | **M5: Active Sampling** | Targeted active learning surfaces failure clusters 5.2x faster than random sampling. |

---

## 🏛️ Mandatory Practitioner Cues & Disclosures

These seven explicit verbal cues establish practitioner credibility and guard against common case study pitfalls:

1. **§1 Practitioner Attribution Cue (During S2 or M1):**  
   > *"This human-in-the-loop error analysis methodology comes directly from Hamel Husain and Shreya Shankar's work at hamel.dev. Before you write a single automated eval or LLM judge, you have to read the raw traces yourself and open-code a failure taxonomy."*

2. **§3.3 Trace Saturation Disclosure (During S2):**  
   > *"Why 60 traces? In qualitative error analysis, Nielsen-Norman style saturation kicks in around 50 to 60 traces. Auditing 60 gives you ~85% of your unique failure modes. Auditing 600 yields diminishing returns until your taxonomy is defined."*

3. **§5.3 Fictional Unit Economics Disclosure (During M2):**  
   > *"Full disclosure: While Meridian Pay's workflows and tickets reflect realistic commercial fintech operations, these specific unit economic constants ($34 per reversal, 25 minutes review, $68/hr comp) are calibrated for this demonstration."*

4. **§9 The 70% Evaluation Pass-Rate Rule (During S3):**  
   > *"Notice our baseline pass rate sits around 72% rather than 98%. In production AI engineering, an eval set with a 99% pass rate is a vanity metric—it tells you nothing. A rigorous eval set intentionally stress-tests known edge cases so performance drops are immediately legible."*

5. **Rev 4 §3.1 Synthetic Feedback Disclosure (During S1 or S2):**  
   > *"In our live runs, feedback is real. In our seeded 14-day production history, user feedback carries a synthetic tag in metadata. We simulate production feedback to demonstrate saved view filtering without fabricating user history."*

6. **Rev 4 §4.1 Sampling Rate Cost Lever (During M6):**  
   > *"Notice our online scoring rules use a 20% sampling rate, not 100%. In production, Braintrust charges per score call. Setting a 20% sampling rate cuts inference costs by 80% while retaining full statistical confidence for anomaly detection."*

7. **Rev 4 §3.3 Loop AI Prompt Optimizer Origin (During S3):**  
   > *"Candidate prompt v2 wasn't hand-tuned to break on stage. We used Loop, Braintrust's AI prompt optimizer, in the playground with instructions to maximize overall score and reduce response length. It organically found that bypassing escalations scored higher on average."*

---

## ⏱️ The 7-Minute Core Spine

---

### S1: The Working Agent & Span Telemetry (00:00 – 02:30)
**Goal:** Show a live Tier 2 support agent executing in real-time, inspect wrapped client telemetry, per-tool child spans, root span schema parity, and user feedback logging.

#### 1. Terminal Action: Run Live Agent
Run in the terminal:
```bash
make live
```
*(Runs in <25s on live API, or <50ms on offline simulation).*

#### 2. Click Path in Braintrust UI
- Open browser to: `https://www.braintrust.dev/app/NTeodori/p/meridian-pay-support/logs`
- Click the top trace (just created).
- Point to:
  1. **Root Span Schema Parity:** `input` contains `ticket`, `account_id`, `channel`; `output` contains `resolution`, `actions`, `escalate`, `citations`. Matches our evaluation dataset record schema 1:1.
  2. **Wrapped Client Telemetry:** Tokens (prompt/completion), exact latency, and cost displayed automatically with zero custom logging code. *(Tip: In Braintrust's table view, click the **Columns** / `+` icon in the table header to toggle on the `Cost` and `Tokens` columns; they are also visible inside the trace drawer under **Metrics**).*
  3. **Trace Tree:** Expand child spans: `claude_planning_and_reasoning` (LLM reasoning span with tokens/cost), `get_account(ACC-0001)`, `search_kb("replacement card")`, `replace_card(CARD-0001, reason="damaged")`.
  4. **Feedback Event:** Click *Feedback* tab on the span drawer to show the logged thumbs-up audit event.

#### 3. Talk Track
> *"To ground this in reality, here is Meridian Pay's Tier 2 Support Agent handling an arbitrary customer inquiry: a merchant reporting a damaged physical card chip.*
> *In Braintrust's log viewer, we see the complete execution hierarchy: the agent gathered account context, referenced knowledge base runbooks, and executed `replace_card` in our core ledger.*
> *Notice our root span instrumentation: the `input` and `output` match our evaluation dataset schema 1:1, so any production span can be promoted directly into an eval test with zero data reshaping. Notice also the feedback event logged against the span.*
> *Individual trace inspection gives engineering confidence for one call—but it doesn't give you confidence to ship prompt changes. Rigorous error analysis does."*

---

### S2: Error Analysis & The Closed-Loop Flywheel (02:30 – 05:30) — THE CENTERPIECE
**Goal:** Prove practitioner discipline with 60 open-coded human audit notes. Reveal the planted `relative_date_resolution` failure mode, then close the loop by promoting those spans into the evaluation dataset and establishing a new baseline.

#### 1. Terminal Action: Inspect Taxonomy
Run in the terminal:
```bash
make s2
```

#### 2. Click Path in Braintrust UI
- In left sidebar, click **Logs** (`.../meridian-pay-support/logs`).
- Filter by tag: `annotated`.
- Group by column: `metadata.failure_category`.
- Open trace `AUDIT-0001` (Duplicate cloud storage charge from "last Tuesday"):
  - Read handwritten note: *"Customer said 'last Tuesday'. Agent queried list_transactions, saw multiple SaaS transactions, and grabbed TXN-1025 from yesterday instead of TXN-1055 from 7 days ago. Off-by-one date failure because agent has no calendar helper."*

#### 3. Talk Track (Part 1 — The Discovery)
> *"Most teams rush to set up LLM judges before they understand how their agent actually fails. Following the error analysis methodology established by Hamel Husain and Shreya Shankar (hamel.dev), we audited 60 raw production traces—open-coding qualitative notes by hand.*
> *(Cue §3.3: Saturation occurs around 50–60 traces; that's enough to capture ~85% of failure modes).*
> *Look at our axial failure taxonomy: our #1 failure mode is not a high-stakes hallucination. It is `relative_date_resolution`—accounting for 12 of our 35 failures (34.3%), twice as frequent as unauthorized money movements!*
> *When a customer says 'dispute the charge from last Tuesday', the model gets plain ISO dates and guesses the wrong transaction 60% of the time. Standard LLM judges completely missed it."*

#### 4. The Flywheel Close (Action: Promote Spans to Dataset)
Run in terminal (or execute in UI):
```bash
make flywheel
```
- In UI: Select the 12 `relative_date_resolution` traces, click `...` ➜ **Add to dataset** ➜ `meridian-cases`.
- Show dataset row count increment: **50 ➜ 62 cases (+24%)**.
- Open the new experiment with the `date_resolution_correct` scorer attached.

#### 5. Talk Track (Part 2 — The Flywheel Close)
> *"Now watch how we close the loop. This is the offline-to-online flywheel that Braintrust's platform is built around:*
> *In the UI, we filtered to the `relative_date_resolution` cluster, selected all 12 spans, and clicked 'Add to dataset'.*
> *We attached a deterministic code scorer, `date_resolution_correct`, and ran the baseline. Now, every candidate prompt or model upgrade must answer for these production failures before merging. Production told us what was broken, the dataset now contains it, and the loop is closed.*
> *In fact, every single category in our failure taxonomy has a corresponding single-criterion scorer (`FAILURE_CATEGORY_SCORERS` in `src/scorers/scorers.py`): from `policy_contradiction_scorer` and `no_over_escalation` to `citation_accuracy_scorer` and `tool_args_valid_scorer`. We can attach these as online scoring rules in M6 or run them in diagnostic slice evaluations."*

---

### S3: Loop Optimizer Goodhart Moment & CI Regression Gate (05:30 – 07:30)
**Goal:** Demonstrate the aggregate metrics trap using Braintrust Loop's prompt optimizer, then show how a property-based CI gate prevents safety regressions from merging.

#### 1. Click Path in Braintrust UI
- In left sidebar, click **Experiments**.
- Open `v2-concise` (or `v2-loop`) with `v1-baseline` as baseline comparison.
- Point to the aggregate metrics trap:
  - Aggregate score climbed: **0.724 ➜ 0.808 (+11.6% clean win!)**
  - Response length dropped from 224 words down to 78 words (-65%).
  - Latency cut in half: 215ms down to 104ms.
  - Escalation rate dropped from 24% down to 10% (hitting target).
- Now filter by: `metadata.money_moving = true`:
  - Show the red column: `no_unauthorized_action` dropped from 1.00 down to 0.50 (4 high-stakes cases failed!).
  - (Cue §9: Notice baseline sits around ~72% overall—eval sets with 99% pass rates are vanity metrics; real evals stress-test the edges).

#### 2. Terminal Action: Run CI Regression Gate
Switch to terminal and run:
```bash
make gate
```
*Shows: Gate FAILS with Exit Code 1. Detailed breakdown of the unauthorized actions on MP-0001, MP-0002, MP-0004, MP-0006.*

Then show the passing fix:
```bash
make gate-pass
```
*Shows: `v3-fixed` passes with 100% compliance on money-moving cases and Exit Code 0.*

#### 3. Talk Track
> *(Cue Rev 4 §3.3: Candidate v2 was generated via Loop, Braintrust's AI prompt optimizer).*
> *"Here is Goodhart's Law in action: an AI optimizer optimizes what you measure. Because the aggregate metric rewarded brevity and fast resolution, Loop discovered that resolving tickets directly scored higher across 80% of routine cases.*
> *On an average dashboard, this looks like an 11.6% optimization victory. But when we filter for `metadata.money_moving = true`, the fatal regression appears: the agent became so eager to be concise that it started granting $5,500 credit limit increases and approving $2,400 disputes on 42-day-old accounts without fraud review!*
> *To prevent this, we codified a property-based assertion in our CI pipeline (`scripts/gate.py`). Even though the aggregate score was higher, our zero-tolerance safety rule blocked the pull request with Exit Code 1.*
> *When engineering introduced explicit guardrails in `v3-fixed`, the gate verified 100% safety compliance and passed with Exit Code 0."*

---

## 🎛️ Swappable Modules (2.5 min each — Pick 2)

---

### M1: Judge Validation & Calibration
**Discovery Trigger:** Panel expresses skepticism about automated LLM evaluations or LLM-as-a-judge reliability.  
**Goal:** Show how unvalidated LLM judges create a false sense of security, and demonstrate calibration against 100 human-labeled ground-truth records.

#### 1. Terminal Action
```bash
make align
```

#### 2. Click Path in Braintrust UI
- In left sidebar, click **Experiments**.
- Compare `judge-validation-v2` against `judge-validation-v1`.
- Inspect logged metrics: `human_agreement` (87% ➜ 91%), `failure_recall_tpr` (33.3% ➜ 73.3%).

#### 3. Talk Track
> *"Many teams adopt an LLM-as-a-judge, see an 87% agreement score on a dashboard, and consider their evals solved. That is deeply misleading.*
> *We evaluated our naive grounding judge (v1) against 100 hand-audited human labels with a 15% base failure rate. In the terminal, look at the confusion matrix:*
> *Raw agreement is 87.0%. But because the base rate is 15%, a judge that blindly passed 100% of cases would score 85%!*
> *When you look at True Positive Rate—actual recall on factual errors—v1 only scored 33.3%. It missed 10 out of 15 real failures.*
> *(Cue 2×2 Rubric: If output looks good but scores low, fix your eval. If output looks bad but scores high, fix your scorer).*
> *By taking 3 critique examples directly from our human error analysis and embedding them into the few-shot rubric in `grounding_v2`, True Positive Rate jumped from 33.3% to 73.3% (+40% absolute lift), while keeping false alarms low.*
> *Braintrust lets you evaluate your evaluators before you trust them with your pipeline."*

---

### M2: Commercial Unit Economics & Business Math
**Discovery Trigger:** Panel includes executive/finance stakeholders or asks about ROI, cost of errors, and business risk.  
**Goal:** Translate abstract scorer deltas into concrete dollars, compliance labor capacity, and model unit economics.

#### 1. Terminal Action
```bash
make impact
```

#### 2. Click Path in Braintrust UI
- Open experiment `v2-concise` in Braintrust UI.
- Click into Experiment Settings / Metadata:
  - Show custom metadata fields: `annual_regression_risk_usd: 1092329`, `analyst_fte_consumed: 3.5`.

#### 3. Talk Track
> *(Cue §5.3: Disclose that unit economics parameters are calibrated for this demonstration).*
> *"To an executive or risk officer, a scorer drop from 0.99 to 0.88 is a mathematical abstraction. In the terminal, we translated our Braintrust eval results into commercial unit economics using `config/unit_economics.yaml`:*
> *At 3,000 tickets a week with 18% money-moving share:*
> *If `v2-concise` had bypassed our CI gate, it would generate 337 unauthorized actions per week.*
> *At $34 per manual reversal, that is $595,000 a year in direct network and processing losses.*
> *More critically, at 25 minutes of compliance investigation per event, it burns 140 risk analyst hours a week—the equivalent of 3.5 full-time risk analysts just cleaning up agent mistakes!*
> *Total financial drag: $1,092,329 per year.*
> *Notice also the model unit economics at the bottom: running Claude Sonnet costs $842/year in tokens vs $224/year on Haiku. That $618 difference is completely negligible compared to the $1.09M risk of unauthorized actions. Braintrust turns AI engineering into quantifiable business math."*

---

### M6: Online Scoring & Automation Alerting
**Discovery Trigger:** Panel mentions monitoring, proactive alerting, on-call visibility, or asks *"How do we find out when things break in production before customers complain?"*  
**Goal:** Demonstrate configuring online scoring rules live, applying a 20% sampling rate for cost control, targeting the retrieval span, and showing automated threshold alerts on Day 9.

#### 1. Terminal Action: Start Alert Receiver & Run Stream Simulation
In terminal tab 1:
```bash
make m6-alert
```
In terminal tab 2:
```bash
make m6-rules
```

#### 2. Click Path in Braintrust UI
- In Braintrust project settings, click **Automations** ➜ **Online Scoring**.
- Show active rules:
  1. `Trace-Safety-Audit`: Scorer `no_unauthorized_action`, Scope `Trace Root`, Sampling Rate `20%`.
  2. `Retrieval-Grounding-Check`: Scorer `grounding`, Scope `Span search_kb`, Sampling Rate `20%`.
- In left sidebar, click **Logs** ➜ inspect the 14-day production time series.
- Point to Day 9: Safety score stepped down from 0.99 to 0.88 mid-day when v2 shipped.
- Switch to terminal tab 1: Show the webhook alert captured live on port 8383!

#### 3. Talk Track
> *(Cue Rev 4 §4.1: Sampling rate is the cost-control lever; 14-day history reflects online scorer running continuously).*
> *"Here is how we ensure production safety without blowing the budget. In project settings, we configured two online scoring rules:*
> *First, notice the sampling rate: we set 20%, not 100%. Online scoring incurs LLM inference costs, so a 20% sample cuts our evaluation bill by 80% while retaining high statistical power.*
> *Second, notice span targeting: we targeted `grounding` specifically at the child retrieval span (`search_kb`), rather than the root conversation, isolating search quality from generation.*
> *Third, look at our automation: when `no_unauthorized_action` dropped below 0.90 on Day 9, an automated webhook fired immediately—as you see in our alert receiver terminal. We knew about the regression within 2 hours of deployment, rather than discovering it weeks later from customer churn."*

---

### M7: SME Review Loop & Launch Readiness Trust Curve
**Discovery Trigger:** Regulated industry buyer (healthcare, tax, finance) asking: *"How do non-technical reviewers audit traces?"* or *"How do we prove to compliance that this agent is ready to launch?"*  
**Goal:** Show no-code human review mode on negative feedback traces, followed by the 6-iteration trust curve.

#### 1. Click Path in Braintrust UI (Part 1 — Reviewers Without Engineers)
- Open saved view: `user_feedback = 0` (or `user_feedback = 0 AND is_money_moving = true`).
- Click **Review** mode toggle in the top bar.
- Point to the clean, non-engineer interface:
  - Binary review scores: `policy_correct` (thumbs up/down) and `escalation_appropriate` (thumbs up/down).
  - Free-form auditor critique text box.
- Show that pushed scorers (`no_unauthorized_action`) are selectable in the Playground dropdown by a clinical/compliance SME without touching code.

#### 2. Terminal Action (Part 2 — The Pre-Launch Trust Curve)
Run in terminal:
```bash
make m7-history
```

#### 3. Talk Track
> *(Cue Rev 4 §4.2: Reviewer disagreement disclosure—Nick is single auditor; rubric is frontline mitigation).*
> *"In regulated vertical AI, you cannot deploy an agent until compliance and subject matter experts sign off. Braintrust solves this for two distinct personas:*
> *For our non-technical reviewers, we created a saved view filtering for negative customer feedback (`user_feedback = 0`). In Review mode, reviewers evaluate traces using simple binary scores and write qualitative critique notes—completely abstracted from raw code.*
> *And for leadership and compliance, we generate the pre-launch Trust Curve you see in the terminal:*
> *This isn't fabricated marketing data; these are real evaluation runs across 6 prompt iterations in our repository—from a 60% naive chatbot to our 100% compliant, regression-gated final candidate (`v3-fixed`).*
> *This chart is the launch artifact you present to your risk committee to prove production readiness."*

---

### M8: Model Swap & Cost Optimization
**Discovery Trigger:** Panel asks about model migration, cost optimization, or *"Claude 3.7 / GPT-5 just came out—how do we evaluate whether to switch?"*  
**Goal:** Demonstrate the Playground summary comparative layout (Task A Haiku vs Task B Sonnet) and show production A/B grouping.

#### 1. Terminal Action
```bash
make m8-models
```

#### 2. Click Path in Braintrust UI
- Open **Playground** ➜ attach `meridian-cases` dataset.
- Show Task A (`claude-3-5-haiku`) next to Task B (`claude-3-5-sonnet`).
- Toggle **Summary** layout in the top right:
  - Side-by-side comparison per scorer, duration, token counts, and cost.
- In **Logs**, group by `metadata.model` to show the 20% production A/B slice.

#### 3. Talk Track
> *"Every few weeks a faster or cheaper model drops and engineering asks: should we migrate?*
> *In Braintrust's Playground, you clone your prompt, select the new model from the dropdown, and toggle the Summary view.*
> *Look at the comparative breakdown in the terminal:*
> *Sonnet gives us a +10.5% lift in factual grounding and +8.0% in action overlap, with identical 100% safety compliance.*
> *Now look at the trade-off: Sonnet is 2.2x slower (310ms vs 142ms) and costs 4.3x more in tokens ($0.0063 vs $0.0014 per ticket).*
> *At 3,000 tickets a week, that premium equals +$758 a year. Compare that to the $1.09M annual risk of unauthorized actions we saw in M2!*
> *Braintrust turns model migration from an anxious debate into an objective cost-benefit calculation."*

---

### M3: First-Failure Step Attribution & Tool Transitions
**Discovery Trigger:** Panel asks about multi-step tool-use agents, cyclic execution, or root cause debugging.  
**Goal:** Show that multi-turn agents don't fail at the final response—they derail early in the tool trajectory.

#### 1. Terminal Action
```bash
make transitions
```

#### 2. Talk Track
> *"When a multi-step agent fails, engineers often waste hours prompt-engineering the final response generation. But in reality, the failure happened multiple steps earlier.*
> *We instrumented `first_failure_step` and tool-to-tool transition matrices across our failing traces.*
> *Notice the breakdown: in 100% of these traces, the failure occurs at Step 2 or Step 3. Specifically, look at the transition from `get_account` directly to `open_dispute` or `issue_refund` without an intervening `escalate` call.*
> *This diagnostic tells engineering exactly where to intervene: instead of re-prompting the LLM, we implemented a deterministic pre-condition assertion on the `open_dispute` tool binding that validates account age before execution."*

---

### M4: Retrieval vs. Generation Split (Crowded Context)
**Discovery Trigger:** Panel asks about RAG quality, search accuracy, or asks "is the agent hallucinating or is search broken?"  
**Goal:** Disentangle retrieval failures from generation failures using `retrieval_recall_at_4`.

#### 1. Click Path in Braintrust UI
- Open `meridian-cases` dataset or `v1-baseline` experiment.
- Sort by `retrieval_recall_at_4 = 0.0`.
- Click on Case `MP-0008` (Foreign ATM dispute with competing runbooks):
  - Show retrieved chunks: at k=4, three generic ATM docs crowded out the specialized `tier2-dispute-resolution.md`.
  - Scorer `grounding = 0.0`, but `retrieval_recall_at_4 = 0.0`.

#### 2. Talk Track
> *"When an agent gives an incorrect answer, teams often blame the model for 'hallucinating'. But if the correct policy document was never retrieved into context, the model had zero chance of succeeding.*
> *We decoupled retrieval from generation by evaluating `retrieval_recall_at_4` alongside `grounding`.*
> *In 10 of our benchmark cases, the model failed grounding solely because BM25 search at k=4 returned competing commercial card runbooks that crowded out the required policy document.*
> *This diagnostic told us to fix our chunking and reranker, rather than tweaking model temperature or prompts."*

---

### M5: Production Trace Sampling (Active Learning)
**Discovery Trigger:** Panel asks how to monitor high-volume production traffic (100k+ traces/month) without drowning in noise.  
**Goal:** Compare naive random sampling against targeted active learning sampling.

#### 1. Terminal Action
```bash
make sample
```

#### 2. Talk Track
> *"In production, you can't manually audit 50,000 customer traces every week. But if you only sample uniformly at random, rare but critical failure modes remain invisible.*
> *Here we compare random sampling against targeted active learning sampling:*
> *Under uniform random sampling, discovering our `relative_date_resolution` cluster required auditing ~75 traces.*
> *Under targeted sampling—filtering for fuzzy date phrases, low confidence scores, or tool retry loops—we uncovered 13 failure cases in just 15 reviewed traces.*
> *That is a 5.2x efficiency multiplier. It allows a single QA engineer to uncover emerging failure modes in 15 minutes of review per week."*

---

## 🎯 Positioning Prep: Answers to Critical Buyer Questions (PRD Rev 4 §7)

When the panel probes during role-play or Q&A, use these tested two-sentence positioning responses:

### 1. "Can this data live in our main Datadog dashboard?"
> *"Braintrust is purpose-built for the AI evaluation, playground iteration, and dataset flywheel loop, whereas Datadog excels at full-stack APM and infrastructure telemetry.*
> *Through Braintrust's SDK, daily scorer aggregates and safety metrics can be published directly into Datadog via custom metrics (`scripts/export_scores_to_datadog.py`), allowing you to correlate prompt quality drops with infrastructure latency and error spikes in one pane of glass."*

### 2. "Are LLM-judge scores absolute or relative?"
> *"Zero-shot LLM judges are frequently only reliable comparatively, which is why naive judge setups fail when tracking absolute SLA thresholds.*
> *As demonstrated in Module M1, the solution is validating your judge against human ground truth and calibrating with few-shot failure critiques, which lifted our grounding True Positive Rate from 33% to 73%."*

### 3. "How do you handle reviewer disagreement?"
> *"Braintrust captures individual audit events with user attribution, but multi-reviewer statistical consensus (like Cohen's or Fleiss' Kappa) is currently computed downstream via SDK export.*
> *In production workflows, strict rubric definitions and binary scoring criteria—rather than subjective 1–5 scales—remain the most reliable operational defense against reviewer drift."*

### 4. "Can I A/B test models in production?"
> *"Yes. By logging model identifiers in trace metadata (`metadata.model`), Braintrust's log viewer allows you to group by model in one click and compare real-world pass rates, latency distributions, and customer feedback side-by-side across production cohorts."*

### 5. "What does online scoring cost?"
> *"Online scoring calls cost inference tokens, which is why running 100% sampling on high-volume traffic is an anti-pattern.*
> *Braintrust allows configuring granular sampling rates (such as 10%–20%) per rule, giving you statistical confidence for alerting at an 80% discount on LLM spend."*

---

## 🛑 Fallback & Troubleshooting Matrix

| Potential Issue | Immediate Fallback Action |
|---|---|
| **Braintrust Web UI slow / unreachable** | Switch to terminal output. All commands (`make s2`, `make flywheel`, `make gate`, `make impact`, `make align`, `make m6-rules`, `make m7-history`, `make m8-models`) print standalone tables with zero external dependencies. |
| **LLM Provider API rate limits / network drop** | The harness automatically uses deterministic policy simulation if `GEMINI_API_KEY` is omitted or errors occur (<50ms execution, 100% reproducible numbers). |
| **Accidental dataset edits in UI** | Run `make push` or `python scripts/push_dataset.py` to restore all 50 cases to clean baseline in 3 seconds. |
| **Pre-flight fails on stage** | Run `make preflight` within 1 hour before the call. If any provider key is down, default to documented artifacts (`docs/loop-session.md`, `docs/feature-verification.md`). |
| **Terminal output font wrapping** | Maximize terminal window width (>110 columns) before starting the screen share. |
