"""
Calculate Commercial Unit Economics and Financial Impact of Model Regressions (M2 Module).
Braintrust SDK Version: 0.39.0

Implements Beat M2: Business Math for Corporate Development / Executive Buyers.
- Translates abstract scorer deltas (0.99 -> 0.88) into weekly & annualized dollars and analyst hours
- Highlights both the v2 Prompt Regression cost and the S2 Relative-Date Resolution failure cost
- Pushes derived metrics directly into Braintrust as experiment metadata
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import braintrust as bt
import requests
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = BASE_DIR / "config" / "unit_economics.yaml"


def load_unit_economics() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        # Fallback defaults per PRD §5
        return {
            "weekly_ticket_volume": 3000,
            "pct_money_moving": 0.18,
            "manual_reversal_cost_usd": 34,
            "compliance_touch_minutes": 25,
            "analyst_fully_loaded_hourly_usd": 68,
            "csat_points_per_pct_bad_resolution": 0.4,
        }

    # Lightweight YAML parsing without external pyyaml dependency
    config: Dict[str, Any] = {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                try:
                    if "." in val:
                        config[key] = float(val)
                    else:
                        config[key] = int(val)
                except ValueError:
                    config[key] = val
    return config


def compute_business_impact(config: Dict[str, Any]) -> Dict[str, Any]:
    vol = config.get("weekly_ticket_volume", 3000)
    pct_mm = config.get("pct_money_moving", 0.18)
    reversal_cost = config.get("manual_reversal_cost_usd", 34)
    touch_mins = config.get("compliance_touch_minutes", 25)
    hourly_rate = config.get("analyst_fully_loaded_hourly_usd", 68)
    csat_slope = config.get("csat_points_per_pct_bad_resolution", 0.4)

    # 1. v2 Prompt Regression Impact (High-Stakes Money Moving Failures)
    mm_weekly_volume = int(vol * pct_mm)  # 540 tickets/week
    # v1 baseline is 100% compliant; v2 fails 5 of 8 cases (62.5% failure rate)
    v2_fail_rate = 5 / 8  # 0.625
    v2_failures_per_week = int(mm_weekly_volume * v2_fail_rate)  # 337 failures/week

    v2_direct_cost_wk = v2_failures_per_week * reversal_cost
    v2_direct_cost_yr = v2_direct_cost_wk * 52

    v2_analyst_hours_wk = v2_failures_per_week * (touch_mins / 60.0)
    v2_analyst_fte_wk = v2_analyst_hours_wk / 40.0
    v2_labor_cost_wk = v2_analyst_hours_wk * hourly_rate
    v2_labor_cost_yr = v2_labor_cost_wk * 52

    v2_total_cost_wk = v2_direct_cost_wk + v2_labor_cost_wk
    v2_total_cost_yr = v2_total_cost_wk * 52
    v2_csat_drop = (v2_fail_rate * 100) * csat_slope

    # 2. S2 Relative Date Resolution Failure Impact (Ongoing in Production)
    # ~35% of dispute tickets contain relative dates; ~60% fail
    dispute_volume = int(vol * 0.25)  # 750 disputes/wk
    rel_date_volume = int(dispute_volume * 0.35)  # ~262 tickets/wk
    rel_date_failures_wk = int(rel_date_volume * 0.60)  # ~157 failures/wk

    rel_direct_cost_wk = rel_date_failures_wk * reversal_cost
    rel_direct_cost_yr = rel_direct_cost_wk * 52
    rel_analyst_hours_wk = rel_date_failures_wk * (touch_mins / 60.0)
    rel_total_cost_yr = (rel_direct_cost_wk + (rel_analyst_hours_wk * hourly_rate)) * 52

    # 3. Task Model Unit Economics (Module M8: Model Swap Analysis)
    # Average tokens per ticket: 1,200 input tokens, 120 output tokens
    in_tokens = 1200
    out_tokens = 120
    cost_fast_per_ticket = (in_tokens / 1_000_000 * 0.80) + (out_tokens / 1_000_000 * 4.00)
    cost_prem_per_ticket = (in_tokens / 1_000_000 * 3.00) + (out_tokens / 1_000_000 * 15.00)
    annual_ticket_vol = vol * 52  # 156,000 tickets/year
    annual_llm_cost_fast = annual_ticket_vol * cost_fast_per_ticket
    annual_llm_cost_prem = annual_ticket_vol * cost_prem_per_ticket

    return {
        "v2_failures_per_week": v2_failures_per_week,
        "v2_direct_cost_wk": v2_direct_cost_wk,
        "v2_direct_cost_yr": v2_direct_cost_yr,
        "v2_analyst_hours_wk": v2_analyst_hours_wk,
        "v2_analyst_fte": v2_analyst_fte_wk,
        "v2_labor_cost_yr": v2_labor_cost_yr,
        "v2_total_cost_yr": v2_total_cost_yr,
        "v2_csat_drop": v2_csat_drop,
        "rel_date_failures_wk": rel_date_failures_wk,
        "rel_direct_cost_yr": rel_direct_cost_yr,
        "rel_analyst_hours_wk": rel_analyst_hours_wk,
        "rel_total_cost_yr": rel_total_cost_yr,
        "cost_fast_per_ticket": cost_fast_per_ticket,
        "cost_prem_per_ticket": cost_prem_per_ticket,
        "annual_llm_cost_fast": annual_llm_cost_fast,
        "annual_llm_cost_prem": annual_llm_cost_prem,
    }


def print_business_report(config: Dict[str, Any], impact: Dict[str, Any]) -> None:
    print("\n" + "=" * 85)
    print("💼 MERIDIAN PAY — COMMERCIAL UNIT ECONOMICS & BUSINESS IMPACT (M2 MODULE)")
    print("Audience: Corporate Development & Operations | Source: config/unit_economics.yaml")
    print("=" * 85)

    print("\n📋 OPERATIONAL ASSUMPTIONS:")
    print(f"  • Weekly Support Volume:      {config.get('weekly_ticket_volume', 3000):,d} tickets/week")
    print(f"  • Money-Moving Ticket Share:   {config.get('pct_money_moving', 0.18)*100:.0f}% ({int(config.get('weekly_ticket_volume', 3000)*config.get('pct_money_moving', 0.18))} tickets/wk)")
    print(f"  • Manual Reversal Fee:         ${config.get('manual_reversal_cost_usd', 34):.2f} (ops overhead + network dispute fee)")
    print(f"  • Compliance Review Time:      {config.get('compliance_touch_minutes', 25)} minutes per unauthorized event")
    print(f"  • Analyst Loaded Comp:         ${config.get('analyst_fully_loaded_hourly_usd', 68):.2f} / hour ($141K annualized)")

    print("\n" + "-" * 85)
    print("🚨 IMPACT 1: v2-CONCISE PROMPT REGRESSION (What our CI gate prevented!)")
    print("-" * 85)
    print(f"  • Unauthorized Actions Generated:   {impact['v2_failures_per_week']:,d} cases / week")
    print(f"  • Direct Payment Reversal Losses:   ${int(impact['v2_direct_cost_wk']):,d} / week  ➜  ${int(impact['v2_direct_cost_yr']):,d} / year")
    print(f"  • Risk Analyst Capacity Burn:       {impact['v2_analyst_hours_wk']:.1f} hours / week  ({impact['v2_analyst_fte']:.1f} full-time analysts!)")
    print(f"  • Excess Compliance Labor Cost:     ${int(impact['v2_labor_cost_yr']):,d} / year")
    print("  " + "─" * 50)
    print(f"  💰 TOTAL ANNUAL FINANCIAL DRAG:      ${int(impact['v2_total_cost_yr']):,d} / year")
    print(f"  📉 Projected CSAT Regressions:      -{impact['v2_csat_drop']:.1f} CSAT points")

    print("\n" + "-" * 85)
    print("🔍 IMPACT 2: S2 RELATIVE-DATE RESOLUTION (The failure already in production!)")
    print("-" * 85)
    print(f"  • Misattributed Dispute Filings:    {impact['rel_date_failures_wk']:,d} cases / week (60% error rate on fuzzy dates)")
    print(f"  • Erroneous Chargeback Filing Cost: ${int(impact['rel_direct_cost_yr']):,d} / year")
    print(f"  • Analyst Investigation Time:       {impact['rel_analyst_hours_wk']:.1f} hours / week")
    print("  " + "─" * 50)
    print(f"  💰 ONGOING PRODUCTION ACCUMULATION:  ${int(impact['rel_total_cost_yr']):,d} / year")

    print("\n" + "-" * 85)
    print("🤖 IMPACT 3: TASK MODEL UNIT ECONOMICS (Module M8 Model Swap Analysis)")
    print("-" * 85)
    print(f"  • Fast Model (Claude Haiku / Gemini Flash):    ${impact['cost_fast_per_ticket']:.5f} / ticket  ➜  ${int(impact['annual_llm_cost_fast']):,d} / year")
    print(f"  • Premium Model (Claude Sonnet / Gemini Pro):  ${impact['cost_prem_per_ticket']:.5f} / ticket  ➜  ${int(impact['annual_llm_cost_prem']):,d} / year")
    print(f"  • Model Inference Cost Ratio:                  3.75x (${int(impact['annual_llm_cost_prem'] - impact['annual_llm_cost_fast']):,d} annual delta)")
    print("  " + "─" * 50)
    print(f"  💡 Operational Takeaway: Annual LLM inference fee (${int(impact['annual_llm_cost_prem']):,d}/yr) is completely")
    print(f"     dwarfed by unauthorized action risk (${int(impact['v2_total_cost_yr']):,d}/yr). Choose the model that gates risk.")

    print("\n" + "=" * 85)
    print("💡 THE COMMERCIAL TAKEAWAY:")
    print("   'A scorer drop from 0.99 to 0.88 is a mathematical abstraction.")
    print(f"    In commercial terms, deploying v2 without a gate costs over $1.09 Million per year")
    print(f"    and burns {impact['v2_analyst_fte']:.1f} full-time risk analysts on preventable manual reversals.'")
    print("=" * 85 + "\n")


def push_metadata_to_braintrust(config: Dict[str, Any], impact: Dict[str, Any], project_name: Optional[str] = None) -> None:
    api_key = os.getenv("BRAINTRUST_API_KEY")
    if not api_key:
        print("⚠️  No BRAINTRUST_API_KEY found. Skipping metadata push.")
        return

    proj = project_name or os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    print(f"📡 Pushing commercial unit economics metadata into Braintrust project [{proj}]...")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    p_res = requests.get(
        "https://api.braintrust.dev/v1/project",
        headers=headers,
        params={"project_name": proj},
    )

    if p_res.status_code == 200:
        objects = p_res.json().get("objects", [])
        if objects:
            p_id = objects[0]["id"]
            patch_data = {
                "metadata": {
                    "unit_economics": config,
                    "annual_regression_risk_usd": impact["v2_total_cost_yr"],
                    "annual_relative_date_cost_usd": impact["rel_total_cost_yr"],
                    "weekly_unauthorized_actions": impact["v2_failures_per_week"],
                    "analyst_fte_consumed": round(impact["v2_analyst_fte"], 2),
                }
            }
            res = requests.patch(f"https://api.braintrust.dev/v1/project/{p_id}", headers=headers, json=patch_data)
            if res.status_code == 200:
                print("✅ Commercial metrics pushed to Braintrust project metadata!")
            else:
                print(f"ℹ️  Project metadata patch status: {res.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Calculate commercial financial impact of eval deltas.")
    parser.add_argument("--project", type=str, default=None, help="Braintrust project name")
    parser.add_argument("--skip-push", action="store_true", help="Skip pushing metadata to Braintrust")
    args = parser.parse_args()

    config = load_unit_economics()
    impact = compute_business_impact(config)
    print_business_report(config, impact)

    if not args.skip_push:
        push_metadata_to_braintrust(config, impact, args.project)


if __name__ == "__main__":
    main()
