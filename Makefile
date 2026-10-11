.PHONY: help install seed live live-fraud eval logs threads gate gate-pass test reset s2 annotations align-v1 align-v2 align impact transitions sample flywheel preflight push parity m6-alert m6-rules m7-history m8-models export-datadog app studio demo demo-studio

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help:
	@echo "=========================================================================="
	@echo "Meridian Pay Support Agent — Braintrust Eval & Monitoring Demo Harness"
	@echo "Rev 4: Offline↔Online Flywheel, Loop Optimizer & Swappable Modules (M1-M8)"
	@echo "=========================================================================="
	@echo "Meridian Pay Financial Support Portal & Review Studio:"
	@echo "  make app           Launch local Meridian Pay Financial Support App portal"
	@echo "  make studio        Launch local browser Trace Review Studio connected to Braintrust"
	@echo "  make demo          Run full closed-loop Trace Review Studio demo script (auto)"
	@echo "  make demo-studio   Run interactive closed-loop Trace Review Studio demo script"
	@echo ""
	@echo "Pre-Flight & Parity:"
	@echo "  make preflight     Validate all API keys, datasets, and docs (<60s)"
	@echo "  make parity        Assert schema parity between spans and dataset records"
	@echo "  make push          Push code-defined prompts, scorers, and datasets"
	@echo ""
	@echo "Core Spine Commands (7 min):"
	@echo "  make live          [S1] Run live agent on customer ticket (<25s)"
	@echo "  make s2            [S2] Seed 60 audited traces & display Failure Taxonomy"
	@echo "  make flywheel      [S2] Close loop: Promote failing spans to dataset (50->62)"
	@echo "  make gate          [S3] Run CI regression gate on v2 (demonstrates PR block)"
	@echo "  make gate-pass     [S3] Run CI regression gate on v3-fixed (demonstrates pass)"
	@echo ""
	@echo "Capability Module Commands (Pick 2 based on Discovery, 2.5 min each):"
	@echo "  make align         [M1] Judge Validation (v1 vs v2 TPR: 33% -> 73%)"
	@echo "  make impact        [M2] Business Math ($1.09M regression drag, unit economics)"
	@echo "  make m6-rules      [M6] Online Scoring & Alerting (Day 9 surge detection)"
	@echo "  make m6-alert      [M6] Start local automation webhook alert receiver (port 8383)"
	@echo "  make transitions   [M3] First-Failure Step Attribution & Tool Transition Matrix"
	@echo "  make m7-history    [M7] SME Review & Launch Readiness (6-iteration trust curve)"
	@echo "  make m8-models     [M8] Model Swap & Cost Optimization (Haiku vs Sonnet)"
	@echo "  make sample        [M5] Targeted active learning review sampling"
	@echo "  make export-datadog [Opt] Export Braintrust scorer aggregates to Datadog"
	@echo ""
	@echo "Setup & Seed Commands:"
	@echo "  make install       Install dependencies in virtualenv"
	@echo "  make seed          Full demo seed (dataset, v1, v2, v3, 14-day logs, S2 annotations)"
	@echo "  make eval          Run evaluation experiments across v1, v2, and v3"
	@echo "  make logs          Seed 14-day production logs timeline (~500 traces)"
	@echo "  make threads       Seed multi-turn conversation threads (Thread View & Topics)"
	@echo "  make reset         Reset local backend and fixture state"
	@echo "=========================================================================="


app:
	@echo "🚀 Launching Meridian Pay Financial Support Portal..."
	$(PYTHON) scripts/launch_app.py

studio:
	@echo "🚀 Launching Braintrust Trace Review Studio..."
	$(PYTHON) scripts/launch_studio.py

demo:
	@echo "🎬 Running Braintrust Trace Review Studio Demo (Auto)..."
	$(PYTHON) scripts/demo_trace_review_workflow.py --auto

demo-studio:
	@echo "🎬 Running Braintrust Trace Review Studio Demo (Interactive)..."
	$(PYTHON) scripts/demo_trace_review_workflow.py --interactive




install:
	@echo "📦 Installing dependencies..."
	$(PIP) install -r requirements.txt

preflight:
	@echo "🚀 Running Pre-Flight Verification (<60s)..."
	$(PYTHON) scripts/preflight.py

parity:
	@echo "🧪 Running Schema Parity Test..."
	$(PYTHON) -m unittest tests/test_schema_parity.py

push:
	@echo "🚀 Pushing datasets, prompts, and scorers to Braintrust..."
	$(PYTHON) scripts/push_code.py

seed:
	@echo "🚀 Running full demo seed..."
	$(PYTHON) scripts/push_dataset.py
	$(PYTHON) scripts/run_experiment.py --prompt v1 --name v1-baseline
	$(PYTHON) scripts/run_experiment.py --prompt v2 --name v2-concise --baseline v1-baseline
	$(PYTHON) scripts/run_experiment.py --prompt v3 --name v3-fixed --baseline v1-baseline
	$(PYTHON) scripts/seed_logs.py --count 500
	@echo "🎉 Full demo harness seeded successfully!"

live:
	@echo "⚡ Running live agent on ticket..."
	$(PYTHON) -m src.agent.loop --ticket "My physical card was bent in my wallet and the chip fell out. We need a replacement card ASAP." --account ACC-0001 --prompt v2

live-fraud:
	@echo "⚡ Running live agent on high-stakes fraud ticket..."
	$(PYTHON) -m src.agent.loop --ticket "Customer says a $$2,400 charge to 'GLOBAL VEND LTD' isn't theirs. They want an immediate dispute credit." --account ACC-0001 --prompt v3

eval:
	@echo "🔬 Running evaluation experiments..."
	$(PYTHON) scripts/run_experiment.py --prompt v1 --name v1-baseline
	$(PYTHON) scripts/run_experiment.py --prompt v2 --name v2-concise --baseline v1-baseline
	$(PYTHON) scripts/run_experiment.py --prompt v3 --name v3-fixed --baseline v1-baseline

logs:
	@echo "📊 Seeding 14-day production logs..."
	$(PYTHON) scripts/seed_logs.py --count 500

threads:
	@echo "🧵 Seeding multi-turn conversation threads..."
	$(PYTHON) scripts/seed_threads.py --count 40

gate:
	@echo "🛡️ Running CI regression gate on v2-concise (expected to fail)..."
	-$(PYTHON) scripts/gate.py --experiment v2-concise --baseline v1-baseline

gate-pass:
	@echo "🛡️ Running CI regression gate on v3-fixed (expected to pass)..."
	$(PYTHON) scripts/gate.py --experiment v3-fixed --baseline v1-baseline

s2: annotations
annotations:
	@echo "📊 Running Beat S2: 60 Audited Traces & Failure Taxonomy..."
	$(PYTHON) scripts/seed_annotations.py

flywheel:
	@echo "🔄 Running Beat S2 Flywheel: Promoting failure spans to dataset..."
	$(PYTHON) scripts/flywheel_sync.py --dry-run

align-v1:
	@echo "⚖️ Running Beat M1: Grounding Judge v1 Alignment (Zero-Shot)..."
	$(PYTHON) scripts/judge_alignment.py --judge v1

align-v2:
	@echo "⚖️ Running Beat M1: Grounding Judge v2 Alignment (Few-Shot)..."
	$(PYTHON) scripts/judge_alignment.py --judge v2

align:
	@echo "⚖️ Running Beat M1: Side-by-Side Judge Validation Comparison..."
	$(PYTHON) scripts/judge_alignment.py --judge both

impact:
	@echo "💼 Running Beat M2: Commercial Unit Economics & Financial Impact..."
	$(PYTHON) scripts/business_impact.py

m6-alert:
	@echo "🚨 Starting Webhook Alert Receiver on Port 8383..."
	$(PYTHON) scripts/alert_receiver.py

m6-rules:
	@echo "📡 Running Beat M6: Online Scoring Rules & Automation Alerts..."
	$(PYTHON) scripts/simulate_online_rules.py

transitions:
	@echo "🔬 Running Beat M3: Tool Transition Matrix & Step Failure Attribution..."
	$(PYTHON) scripts/transition_matrix.py

m7-history:
	@echo "📈 Running Beat M7: Pre-Launch Accuracy & Trust Curve..."
	$(PYTHON) scripts/run_iteration_history.py --sample 10

m8-models:
	@echo "🤖 Running Beat M8: Model Swap Comparative Analysis..."
	$(PYTHON) scripts/model_comparison.py

sample:
	@echo "🔍 Running Beat M5: Targeted Active Learning Review Sampling..."
	$(PYTHON) scripts/sample_traces.py --mode targeted

export-datadog:
	@echo "📊 Running Datadog Telemetry Sync (Dry-Run)..."
	$(PYTHON) scripts/export_scores_to_datadog.py

cleanup-facets:
	@echo "🧹 Cleaning up preprocessor_empty facet records from Braintrust..."
	$(PYTHON) scripts/cleanup_preprocessor_empty.py

cleanup-logs:
	@echo "🧹 Cleaning up duplicate and low-quality logs from Braintrust..."
	$(PYTHON) scripts/cleanup_braintrust_logs.py --execute

cleanup-logs-dry:
	@echo "🔍 Running dry-run audit of duplicate and low-quality logs..."
	$(PYTHON) scripts/cleanup_braintrust_logs.py --dry-run

synth-traces:
	@echo "🚀 Generating 200+ synthetic dimension-tuple traces with compliant LLM spans..."
	$(PYTHON) scripts/generate_dimension_traces.py --count 220

test:
	@echo "🧪 Running full test suite..."
	$(PYTHON) scripts/preflight.py
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"
	$(PYTHON) scripts/seed_annotations.py --dry-run
	$(PYTHON) scripts/flywheel_sync.py --dry-run
	$(PYTHON) scripts/judge_alignment.py --judge both --skip-log
	$(PYTHON) scripts/business_impact.py --skip-push
	$(PYTHON) scripts/simulate_online_rules.py
	$(PYTHON) scripts/transition_matrix.py
	$(PYTHON) scripts/run_iteration_history.py --sample 5
	$(PYTHON) scripts/model_comparison.py
	$(PYTHON) scripts/sample_traces.py --mode targeted
	@echo "✅ All tests passed successfully!"

reset:
	@echo "🔄 Resetting local fixture state..."
	$(PYTHON) scripts/generate_fixtures.py
	$(PYTHON) scripts/build_cases.py
	$(PYTHON) scripts/build_human_labels.py
	@echo "Reset complete."
