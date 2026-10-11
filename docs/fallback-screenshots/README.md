# Offline Fallback Guide & Screenshots

This directory serves as the emergency backup in the event of venue Wi-Fi failure, Braintrust hosted UI latency, or third-party service degradation during the 10–15 minute live demo.

---

## 1. Live Terminal Fallbacks

Even without opening a web browser, the entire narrative can be demonstrated purely from the terminal:

1. **Beat 1 (Live Agent Run):**
   ```bash
   make live
   ```
   *Executes the agent in <1s, prints the full trajectory, actions taken, and the Braintrust trace permalink.*

2. **Beat 3 & 4 (The Regression Trap & CI Gate):**
   ```bash
   make gate
   ```
   *Displays the full diagnostic table, showing that v2 aggregate score improved (+1.8%), but Rule 1 (Zero-Tolerance Safety Gate) failed on 5 high-stakes cases.*

3. **Beat 4 (The Fix):**
   ```bash
   make gate-pass
   ```
   *Shows that v3-fixed resolves all 5 regressions (100% compliant) while improving aggregate score to 0.905.*

---

## 2. Key Braintrust UI Screens to Pre-Cache / Tab Open

Before entering the demo call, pre-open these 4 tabs in Chrome:

1. **Tab 1: Datasets View**
   `https://www.braintrust.dev/app/NTeodori/p/meridian-pay-support/datasets/meridian-cases`
   *Shows the 50 cases with routine, ambiguous, and high-stakes metadata.*

2. **Tab 2: Experiment Comparison (`v2-concise` vs `v1-baseline`)**
   `https://www.braintrust.dev/app/NTeodori/p/meridian-pay-support/experiments/v2-concise`
   *Shows aggregate score green (+1.8%), latency improved, and filtering by `money_moving: true` shows the red 0.0s.*

3. **Tab 3: Corrected Experiment (`v3-fixed`)**
   `https://www.braintrust.dev/app/NTeodori/p/meridian-pay-support/experiments/v3-fixed`
   *Shows all checks green, 1.000 on no_unauthorized_action, and 0.905 aggregate score.*

4. **Tab 4: Production Logs Timeline**
   `https://www.braintrust.dev/app/NTeodori/p/meridian-pay-support/logs`
   *Shows the 14-day timeline with the Day 9 step-down and Day 14 red failure trace.*
