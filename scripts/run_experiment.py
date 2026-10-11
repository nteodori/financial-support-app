"""
Run Braintrust evaluation experiments across prompt versions.
Braintrust SDK Version: 0.39.0
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import braintrust as bt
from dotenv import load_dotenv

from src.agent.loop import run_agent
from src.scorers.scorers import ALL_SCORERS

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CASES_PATH = BASE_DIR / "data" / "cases.jsonl"


def load_eval_data() -> List[Dict[str, Any]]:
    cases = []
    with open(CASES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_experiment(
    prompt_version: str = "v1",
    experiment_name: str = "v1-baseline",
    baseline_name: str = None,
    project_name: str = None,
) -> Any:
    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    cases = load_eval_data()

    print("\n" + "=" * 75)
    print(f"🔬 RUNNING BRAINTRUST EVAL: {experiment_name}")
    print(f"Project: {proj} | Prompt Version: {prompt_version} | Cases: {len(cases)}")
    if baseline_name:
        print(f"Comparing against baseline: {baseline_name}")
    print("=" * 75 + "\n")

    # Format cases for Braintrust Eval
    eval_cases = [
        {
            "id": c["id"],
            "input": c["input"],
            "expected": c["expected"],
            "metadata": c.get("metadata", {}),
        }
        for c in cases
    ]

    def task(input_data: Dict[str, Any], hooks: Any = None) -> Dict[str, Any]:
        ticket = input_data.get("ticket", "")
        account_id = input_data.get("account_id", "ACC-0001")
        channel = input_data.get("channel", "email")

        # Execute agent run
        result = run_agent(
            ticket=ticket,
            account_id=account_id,
            channel=channel,
            prompt_version=prompt_version,
        )

        return {
            "reply": result.reply,
            "actions": result.actions,
            "escalated": result.escalated,
            "citations": result.citations,
            "latency_ms": result.latency_ms,
            "reply_word_count": result.reply_word_count,
        }

    eval_kwargs = {
        "name": proj,
        "experiment_name": experiment_name,
        "data": eval_cases,
        "task": task,
        "scores": ALL_SCORERS,
        "metadata": {
            "prompt_version": prompt_version,
            "description": f"Meridian Pay agent evaluation for {prompt_version}",
        },
    }

    if baseline_name:
        eval_kwargs["base_experiment_name"] = baseline_name

    eval_result = bt.Eval(**eval_kwargs)

    print("\n" + "=" * 75)
    print(f"📊 EVALUATION SUMMARY: {experiment_name}")
    print("=" * 75)
    summary = eval_result.summary
    if summary and hasattr(summary, "scores") and summary.scores:
        total_score = 0.0
        count = 0
        for s_name, s_stat in summary.scores.items():
            s_score = s_stat.score if hasattr(s_stat, "score") else (s_stat.get("score", 0.0) if isinstance(s_stat, dict) else s_stat)
            if s_score is not None:
                total_score += float(s_score)
                count += 1
                print(f"  • {s_name:25s}: {float(s_score):.3f}")
        if count > 0:
            mean_score = total_score / count
            print("-" * 75)
            print(f"  ⭐ AGGREGATE MEAN SCORE : {mean_score:.3f}")
    
    print("\n🔗 Braintrust Experiment Dashboard:")
    print(f"  https://www.braintrust.dev/app/NTeodori/p/{proj}/experiments/{experiment_name}")
    print("=" * 75 + "\n")

    return eval_result


def main():
    parser = argparse.ArgumentParser(description="Run Braintrust Eval experiment.")
    parser.add_argument("--prompt", type=str, default="v1", choices=["v1", "v2", "v3"], help="Prompt version")
    parser.add_argument("--name", type=str, default="v1-baseline", help="Experiment name")
    parser.add_argument("--baseline", type=str, default=None, help="Base experiment name to compare against")
    parser.add_argument("--project", type=str, default=None, help="Braintrust project name")
    args = parser.parse_args()

    run_experiment(
        prompt_version=args.prompt,
        experiment_name=args.name,
        baseline_name=args.baseline,
        project_name=args.project,
    )


if __name__ == "__main__":
    main()
