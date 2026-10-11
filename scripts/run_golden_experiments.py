#!/usr/bin/env python3
"""
===============================================================================
Meridian Pay Support Agent — Golden Dataset Multi-Prompt & Multi-Model Eval
===============================================================================
Executes a 2x2 factorial evaluation matrix using the curated Golden Dataset:
- 2 Prompt Versions: v1 (Baseline) vs v2 (Concise Candidate)
- 2 LLM Models: Fast Tier (gemini-3.6-flash / haiku) vs Premium Tier (gemini-1.5-pro / sonnet)
- Experiments Created:
  1. golden-v1-fast     (Prompt v1, Fast Model) [Baseline]
  2. golden-v1-premium  (Prompt v1, Premium Model) [Model Delta]
  3. golden-v2-fast     (Prompt v2, Fast Model) [Prompt Delta]
  4. golden-v2-premium  (Prompt v2, Premium Model) [Full Matrix Synergy]
- Evaluated against ALL_SCORERS: action_match, escalation_match, no_unauthorized_action,
  grounding, citation_precision.
===============================================================================
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import braintrust as bt

from src.agent.loop import run_agent
from src.scorers.scorers import ALL_SCORERS

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

GOLDEN_DATASET_NAME = "meridian-golden-dataset"
LOCAL_GOLDEN_PATH = BASE_DIR / "data" / "golden_dataset.jsonl"


def load_golden_cases(project_name: str) -> List[Dict[str, Any]]:
    """Loads cases from Braintrust Dataset or local fallback."""
    cases = []
    # Try local file first
    if LOCAL_GOLDEN_PATH.exists():
        with open(LOCAL_GOLDEN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
        print(f"{GREEN}✓ Loaded {len(cases)} golden cases from {LOCAL_GOLDEN_PATH}{RESET}")
        return cases

    # Fallback to Braintrust Dataset directly
    try:
        ds = bt.init_dataset(project=project_name, name=GOLDEN_DATASET_NAME)
        for record in ds:
            cases.append({
                "id": record.get("id"),
                "input": record.get("input"),
                "expected": record.get("expected"),
                "metadata": record.get("metadata", {}),
            })
        print(f"{GREEN}✓ Loaded {len(cases)} golden cases from Braintrust Dataset '{GOLDEN_DATASET_NAME}'{RESET}")
    except Exception as e:
        print(f"{YELLOW}⚠️ Could not load from Braintrust dataset: {e}{RESET}")

    return cases


def run_single_eval(
    project_name: str,
    experiment_name: str,
    prompt_version: str,
    model_name: str,
    cases: List[Dict[str, Any]],
    baseline_name: Optional[str] = None,
) -> Any:
    """Executes a single Braintrust Eval experiment with the golden dataset."""
    print("\n" + "=" * 80)
    print(f"{BOLD}🔬 EXECUTING EXPERIMENT: {experiment_name}{RESET}")
    print(f"  • Prompt: {BOLD}{prompt_version}{RESET} | Model: {BOLD}{model_name}{RESET}")
    print(f"  • Cases: {len(cases)} (Golden Test Set)")
    if baseline_name:
        print(f"  • Comparing Against Baseline: {BOLD}{baseline_name}{RESET}")
    print("=" * 80)

    # Evaluation task
    def task(input_data: Dict[str, Any], hooks: Any = None) -> Dict[str, Any]:
        ticket = input_data.get("ticket", "")
        account_id = input_data.get("account_id", "ACC-0001")
        channel = input_data.get("channel", "email")

        result = run_agent(
            ticket=ticket,
            account_id=account_id,
            channel=channel,
            prompt_version=prompt_version,
            model=model_name,
        )

        return {
            "reply": result.reply,
            "actions": result.actions,
            "escalated": result.escalated,
            "citations": result.citations,
            "latency_ms": result.latency_ms,
            "reply_word_count": result.reply_word_count,
        }

    # Format eval cases
    eval_cases = [
        {
            "id": c["id"],
            "input": c["input"],
            "expected": c["expected"],
            "metadata": c.get("metadata", {}),
        }
        for c in cases
    ]

    eval_kwargs = {
        "name": project_name,
        "experiment_name": experiment_name,
        "data": eval_cases,
        "task": task,
        "scores": ALL_SCORERS,
        "metadata": {
            "prompt_version": prompt_version,
            "model": model_name,
            "dataset": GOLDEN_DATASET_NAME,
            "dataset_case_count": len(cases),
            "description": f"Golden test set evaluation for {prompt_version} using {model_name}",
        },
    }

    if baseline_name:
        eval_kwargs["base_experiment_name"] = baseline_name

    eval_result = bt.Eval(**eval_kwargs)

    # Print summary
    summary = eval_result.summary
    scores_dict = {}
    if summary and hasattr(summary, "scores") and summary.scores:
        print(f"\n{BOLD}📊 Experiment Scores ({experiment_name}):{RESET}")
        total = 0.0
        cnt = 0
        for s_name, s_stat in summary.scores.items():
            s_val = s_stat.score if hasattr(s_stat, "score") else (s_stat.get("score", 0.0) if isinstance(s_stat, dict) else s_stat)
            if s_val is not None:
                scores_dict[s_name] = float(s_val)
                total += float(s_val)
                cnt += 1
                print(f"  • {s_name:<26}: {float(s_val):.3f}")
        if cnt > 0:
            scores_dict["aggregate_mean"] = total / cnt
            print(f"  {BOLD}⭐ AGGREGATE MEAN SCORE : {scores_dict['aggregate_mean']:.3f}{RESET}")

    return {
        "experiment_name": experiment_name,
        "prompt_version": prompt_version,
        "model_name": model_name,
        "scores": scores_dict,
        "eval_result": eval_result,
        "url": f"https://www.braintrust.dev/app/NTeodori/p/{project_name}/experiments/{experiment_name}",
    }


def print_comparative_matrix(results: List[Dict[str, Any]]) -> None:
    """Prints the comparative matrix across all 4 experiments."""
    print("\n" + "=" * 105)
    print(f"{BOLD}🏆 MERIDIAN PAY GOLDEN TEST SET — 2x2 MULTI-PROMPT & MULTI-MODEL COMPARATIVE MATRIX{RESET}")
    print("=" * 105)

    headers = [r["experiment_name"] for r in results]
    header_line = f"{'Metric / Dimension':<28} " + " ".join(f"{h:<18}" for h in headers)
    print(BOLD + header_line + RESET)
    print("-" * 105)

    metrics = [
        ("aggregate_mean", "⭐ Aggregate Mean Score"),
        ("action_match", "action_match"),
        ("escalation_match", "escalation_match"),
        ("no_unauthorized_action", "no_unauthorized_action"),
        ("grounding", "grounding"),
        ("citation_precision", "citation_precision"),
    ]

    for key, label in metrics:
        vals = []
        for r in results:
            val = r["scores"].get(key)
            if val is not None:
                vals.append(f"{val:<18.3f}")
            else:
                vals.append(f"{'N/A':<18}")
        row_str = f"{label:<28} " + " ".join(vals)
        if key == "aggregate_mean":
            print(BOLD + GREEN + row_str + RESET)
        elif key == "no_unauthorized_action":
            print(BOLD + row_str + RESET)
        else:
            print(row_str)

    print("-" * 105)
    print(f"{BOLD}Prompt Version:{RESET}              " + " ".join(f"{r['prompt_version']:<18}" for r in results))
    print(f"{BOLD}Model Tier:{RESET}                  " + " ".join(f"{r['model_name'].split('-')[0]:<18}" for r in results))
    print("=" * 105)

    print(f"\n{BOLD}🔗 Braintrust Experiment Dashboards:{RESET}")
    for r in results:
        print(f"  • {r['experiment_name']:<24}: {r['url']}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Run 2-prompt x 2-model experiments with Golden Dataset.")
    parser.add_argument(
        "--project",
        type=str,
        default=os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support"),
        help="Target Braintrust project name.",
    )
    parser.add_argument(
        "--prompt-a",
        type=str,
        default="v1",
        help="First prompt version (default: v1).",
    )
    parser.add_argument(
        "--prompt-b",
        type=str,
        default="v2",
        help="Second prompt version (default: v2).",
    )
    parser.add_argument(
        "--model-fast",
        type=str,
        default="gemini-3.6-flash",
        help="Fast / Cost-optimized model (default: gemini-3.6-flash).",
    )
    parser.add_argument(
        "--model-premium",
        type=str,
        default="gemini-1.5-pro",
        help="Premium / High-reasoning model (default: gemini-1.5-pro).",
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print(f"{BOLD} Meridian Pay Support Agent — Golden Dataset Experimentation{RESET}")
    print(f" Project: {BOLD}{args.project}{RESET}")
    print(f" Prompts: {BOLD}{args.prompt_a}{RESET} vs {BOLD}{args.prompt_b}{RESET}")
    print(f" Models:  {BOLD}{args.model_fast}{RESET} vs {BOLD}{args.model_premium}{RESET}")
    print("=" * 80 + "\n")

    bt.login()
    cases = load_golden_cases(args.project)
    if not cases:
        print(f"{YELLOW}No golden cases found. Please run scripts/create_golden_dataset.py first.{RESET}")
        sys.exit(1)

    # 4 experiments
    # 1. Prompt A + Fast Model [Baseline]
    exp1_name = f"golden-{args.prompt_a}-fast"
    res1 = run_single_eval(
        project_name=args.project,
        experiment_name=exp1_name,
        prompt_version=args.prompt_a,
        model_name=args.model_fast,
        cases=cases,
        baseline_name=None,
    )

    # 2. Prompt A + Premium Model [Model Delta]
    exp2_name = f"golden-{args.prompt_a}-premium"
    res2 = run_single_eval(
        project_name=args.project,
        experiment_name=exp2_name,
        prompt_version=args.prompt_a,
        model_name=args.model_premium,
        cases=cases,
        baseline_name=exp1_name,
    )

    # 3. Prompt B + Fast Model [Prompt Delta]
    exp3_name = f"golden-{args.prompt_b}-fast"
    res3 = run_single_eval(
        project_name=args.project,
        experiment_name=exp3_name,
        prompt_version=args.prompt_b,
        model_name=args.model_fast,
        cases=cases,
        baseline_name=exp1_name,
    )

    # 4. Prompt B + Premium Model [Full Matrix Synergy]
    exp4_name = f"golden-{args.prompt_b}-premium"
    res4 = run_single_eval(
        project_name=args.project,
        experiment_name=exp4_name,
        prompt_version=args.prompt_b,
        model_name=args.model_premium,
        cases=cases,
        baseline_name=exp1_name,
    )

    all_results = [res1, res2, res3, res4]
    print_comparative_matrix(all_results)


if __name__ == "__main__":
    main()
