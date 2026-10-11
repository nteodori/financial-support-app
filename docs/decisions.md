# Architecture & Demo Decisions Log (Revs 2–4)

This record documents critical technical and methodological decisions made across PRD revisions for the Meridian Pay Braintrust Demo Harness.

---

## 1. Domain & Persona: Meridian Pay Tier 2 Fintech Support
- **Decision:** Use a commercial card and payments support workload (disputes, limits, card reissues, KYC, refunds) rather than clinical healthcare or generic conversational chat.
- **Rationale:** Meridian Pay bridges both key enterprise buyer personas:
  - Regulated vertical AI agents (care about unauthorized money-moving actions, compliance auditability, property gates).
  - Conversational support agents (care about latency, tool trajectories, escalation rate, grounding).

---

## 2. Methodology: Error Analysis First (Rev 3 S2)
- **Decision:** The demo opens on raw trace error analysis (60 traces with handwritten open-coded notes clustered into an axial taxonomy) rather than a pre-computed scoreboard.
- **Rationale (Hamel Husain & Shreya Shankar):** Scoreboards mask systemic flaws. Auditing real traces reveals that the #1 failure mode in production is *relative-date resolution* (55% failure rate), a failure nobody anticipated or built an eval for.

---

## 3. S3 Goodhart's Law & Loop Prompt Optimizer (Rev 4 §3.3)
- **Decision:** Prompt improvement is framed through Loop, Braintrust's AI prompt optimizer.
- **Rationale:** An optimizer naturally uncovers Goodhart's Law: when rewarded for high aggregate score and conciseness, it suppresses escalations on routine cases to boost scores, inadvertently causing unauthorized actions on high-stakes cases.
- **Live Fallback:** Preflight check determines live execution vs. referencing `docs/loop-session.md`.

---

## 4. Instrumentation & Flywheel Schema Parity (Rev 4 §3.1, §3.2)
- **Decision:** Root span `input` and `output` strictly match the evaluation dataset record keys:
  - `input`: `ticket`, `account_id`, `channel`
  - `output`: `resolution`, `actions`, `escalate`, `citations`
- **Rationale:** Enables seamless one-click trace promotion (*"Add to dataset"*) without data wrangling or reshaping.

---

## 5. Synthetic Feedback Disclosure (Rev 4 §3.1)
- **Decision:** Seeded feedback traces in the 14-day production history are explicitly marked with `metadata.feedback_source: "synthetic"`.
- **Rationale:** Maintains total honesty and transparency. Nick's 60 audited annotations are genuine human-in-the-loop work; seeded 14-day production feedback is transparently simulated.

---

## 6. Backdated 14-Day Timeline (Rev 2 §9 & Rev 4 §4.1)
- **Decision:** 14-day historical production logs are pre-populated with scores computed by identical scorer code offline.
- **Rationale:** Online scoring rules in Braintrust evaluate newly ingested live streams rather than retroactively scoring historical rows. Disclosed verbally on the call: *"Our 14-day history reflects the online scorer running continuously in production. Today we configure the rule live on incoming traffic."*

---

## 7. Reviewer Disagreement Handling (Rev 4 §4.2)
- **Decision:** Do not fake inter-rater agreement statistics (Fleiss' Kappa).
- **Rationale:** Nick is the single human labeler in this harness. When asked how Braintrust handles multi-reviewer consistency, honestly state that Braintrust captures user-attributed audit events, but mathematical consensus modeling is handled in downstream tools, with strict rubrics serving as the operational mitigation.
