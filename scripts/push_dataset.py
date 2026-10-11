"""
Push data/cases.jsonl to Braintrust as a versioned Dataset.
Braintrust SDK Version: 0.39.0
"""

import json
import os
from pathlib import Path
import braintrust as bt
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CASES_PATH = BASE_DIR / "data" / "cases.jsonl"


def push_dataset(dataset_name: str = "meridian-cases", project_name: str = None) -> str:
    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    print(f"📦 Connecting to Braintrust Dataset '{dataset_name}' in project '{proj}'...")

    dataset = bt.init_dataset(
        project=proj,
        name=dataset_name,
        description="50 hand-reviewed customer support cases for Meridian Pay Tier 2 agent (32 routine, 10 ambiguous, 8 high-stakes).",
    )

    if not CASES_PATH.exists():
        raise FileNotFoundError(f"Cases file {CASES_PATH} not found.")

    count = 0
    with open(CASES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            dataset.insert(
                id=case["id"],
                input=case["input"],
                expected=case["expected"],
                metadata=case.get("metadata", {}),
            )
            count += 1

    dataset.flush()
    print(f"✅ Successfully pushed {count} cases to Braintrust Dataset '{dataset_name}'.")
    return dataset_name


if __name__ == "__main__":
    push_dataset()
