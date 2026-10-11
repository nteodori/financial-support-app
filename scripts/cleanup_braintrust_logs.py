#!/usr/bin/env python3
"""
===============================================================================
Meridian Pay Support Agent — Braintrust Log Cleanup Utility
===============================================================================
Audits and purges low-quality duplicates, dummy test traces, and incomplete logs
from Braintrust project logs while strictly preserving human-reviewed audit notes
and canonical evaluation scenarios.

Features:
- Safe dry-run mode by default (use --execute to perform deletions).
- Child-span cascading: deletes all child spans belonging to deleted root spans.
- Strict safeguards: explicitly protects traces tagged 'annotated' or containing
  audit_id / failure_category (required by demo runbook S2 & M1-M8).
- Batch deletion via /logs3 with automatic pacing and rate-limit handling.
===============================================================================
"""

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

import braintrust as bt

# ANSI formatting
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def fetch_all_root_spans(conn, project_name: str) -> List[Dict[str, Any]]:
    """Fetches all root spans from Braintrust using cursor pagination."""
    print(f"{CYAN}🔍 Querying root spans for project '{project_name}'...{RESET}")
    root_spans = []
    cursor = None
    page = 1

    while True:
        offset_clause = f"OFFSET '{cursor}'" if cursor else ""
        query = f"""
            SELECT
                id,
                root_span_id,
                span_id,
                span_attributes.name as name,
                span_attributes.type as span_type,
                input,
                output,
                metadata,
                tags,
                scores,
                metrics,
                comments,
                is_root,
                created
            FROM project_logs("{project_name}")
            WHERE is_root = true
            LIMIT 1000
            {offset_clause}
        """
        res = conn.post("btql", json={"query": query})
        if res.status_code == 429:
            print(f"{YELLOW}⏳ Rate limit hit while querying. Cooling down 20s...{RESET}")
            time.sleep(20)
            continue
        elif res.status_code != 200:
            raise RuntimeError(f"BTQL error: {res.status_code} - {res.text}")

        data = res.json().get("data", [])
        root_spans.extend(data)
        cursor = res.json().get("cursor")
        print(f"  • Page {page}: fetched {len(data)} root spans (Total: {len(root_spans)})")

        if not cursor or len(data) < 1000:
            break
        page += 1
        time.sleep(1)

    print(f"{GREEN}✅ Fetched {len(root_spans)} total root spans.{RESET}\n")
    return root_spans


def categorize_spans(
    root_spans: List[Dict[str, Any]]
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
    """
    Categorizes root spans into cleanup candidates and protected sets.
    Returns (cleanup_categories, preserved_categories).
    """
    cat_test = []
    cat_broken = []
    s2_protected = []
    remaining_agent = []
    threads = []

    for s in root_spans:
        name = s.get("name") or ""
        inp = s.get("input")
        out = s.get("output")
        meta = s.get("metadata") or {}
        tags = s.get("tags") or []

        # 1. Protected S2 Human Audit traces (MUST NEVER DELETE)
        is_s2 = (
            "annotated" in tags
            or "production-audit" in tags
            or bool(meta.get("audit_id"))
            or bool(meta.get("failure_category"))
        )
        if is_s2:
            s2_protected.append(s)
            continue

        # 2. Dummy / Test traces
        if name.startswith("test_"):
            cat_test.append(s)
            continue

        # 3. Broken / Incomplete traces (empty input or empty output)
        is_empty_inp = inp is None or inp == "" or inp == {} or inp == "{}" or inp == []
        is_empty_out = out is None or out == "" or out == {} or out == "{}" or out == []
        if is_empty_inp or is_empty_out:
            cat_broken.append(s)
            continue

        # 4. Multi-turn threads
        if name == "meridian_support_thread":
            threads.append(s)
            continue

        # 5. Agent traces
        if name == "meridian_support_agent":
            remaining_agent.append(s)
            continue

        # Other traces default to preserved
        remaining_agent.append(s)

    # Multi-turn thread duplicates
    thread_scenarios = defaultdict(list)
    for t in threads:
        inp = t.get("input") or {}
        meta = t.get("metadata") or {}
        key = (inp.get("account_id"), inp.get("company_name"), inp.get("initial_ticket"))
        thread_scenarios[key].append(t)

    cat_thread_dups = []
    preserved_threads = []
    for k, tlist in thread_scenarios.items():
        # Keep latest run
        sorted_th = sorted(tlist, key=lambda x: x.get("created", ""), reverse=True)
        preserved_threads.append(sorted_th[0])
        for extra in sorted_th[1:]:
            cat_thread_dups.append(extra)

    # Single-turn agent duplicates
    agent_clusters = defaultdict(list)
    for a in remaining_agent:
        inp = a.get("input") or {}
        meta = a.get("metadata") or {}
        if isinstance(inp, dict):
            ticket = inp.get("ticket") or ""
            acc = inp.get("account_id") or ""
        else:
            ticket = str(inp)
            acc = ""
        ticket_norm = " ".join(ticket.strip().lower().split())
        agent_clusters[(ticket_norm, acc)].append(a)

    cat_agent_dups = []
    preserved_agent = []
    for k, cluster in agent_clusters.items():
        # Priority for canonical preservation:
        # 1. Has comments
        # 2. Has reviewer / feedback
        # 3. Has tags
        # 4. Latest created
        def get_pri(x):
            meta = x.get("metadata") or {}
            c_cnt = len(x.get("comments") or [])
            t_cnt = len(x.get("tags") or [])
            has_rev = 1 if (meta.get("reviewer") or meta.get("human_review")) else 0
            return (c_cnt, has_rev, t_cnt, x.get("created", ""))

        sorted_c = sorted(cluster, key=get_pri, reverse=True)
        preserved_agent.append(sorted_c[0])
        for extra in sorted_c[1:]:
            cat_agent_dups.append(extra)

    cleanup_categories = {
        "dummy_tests": cat_test,
        "broken_incomplete": cat_broken,
        "thread_duplicates": cat_thread_dups,
        "agent_duplicates": cat_agent_dups,
    }

    preserved_categories = {
        "s2_protected_audits": s2_protected,
        "canonical_agent_traces": preserved_agent,
        "canonical_thread_traces": preserved_threads,
    }

    return cleanup_categories, preserved_categories


def resolve_child_spans(conn, project_name: str, candidate_root_spans: List[Dict[str, Any]]) -> List[str]:
    """
    Given candidate root spans, finds all child spans sharing their root_span_id
    so both root and child spans are deleted.
    Returns list of all span IDs to delete.
    """
    root_span_ids = [s["root_span_id"] for s in candidate_root_spans if s.get("root_span_id")]
    unique_root_span_ids = list(set(root_span_ids))
    print(f"{CYAN}🔍 Resolving child spans for {len(unique_root_span_ids)} candidate root span trees...{RESET}")

    all_ids_to_delete = set()
    # Also include the root span primary IDs
    for s in candidate_root_spans:
        all_ids_to_delete.add(s["id"])

    # Query in batches of 100 root_span_ids
    batch_size = 100
    for i in range(0, len(unique_root_span_ids), batch_size):
        chunk = unique_root_span_ids[i:i + batch_size]
        in_clause = ", ".join(f"'{rid}'" for rid in chunk)
        q = f"""
            SELECT id
            FROM project_logs("{project_name}")
            WHERE root_span_id IN ({in_clause})
            LIMIT 1000
        """
        while True:
            res = conn.post("btql", json={"query": q})
            if res.status_code == 429:
                print(f"{YELLOW}⏳ Rate limit hit while resolving children. Waiting 20s...{RESET}")
                time.sleep(20)
                continue
            elif res.status_code != 200:
                print(f"{RED}Warning: error fetching child spans batch: {res.text}{RESET}")
                break
            rows = res.json().get("data", [])
            for r in rows:
                all_ids_to_delete.add(r["id"])
            break

        time.sleep(0.5)

    print(f"{GREEN}✅ Resolved {len(all_ids_to_delete)} total records to delete (root + children).{RESET}\n")
    return list(all_ids_to_delete)


def execute_batch_delete(
    conn,
    project_id: str,
    org_id: str,
    ids_to_delete: List[str],
    batch_size: int = 250
) -> int:
    """Deletes records in batches via /logs3 endpoint."""
    total = len(ids_to_delete)
    deleted_count = 0
    print(f"{BOLD}{RED}🚀 Deleting {total} records from Braintrust in batches of {batch_size}...{RESET}")

    for i in range(0, total, batch_size):
        batch = ids_to_delete[i:i + batch_size]
        del_rows = [
            {
                "id": rid,
                "log_id": "g",
                "org_id": org_id,
                "project_id": project_id,
                "_object_delete": True,
            }
            for rid in batch
        ]
        payload = {
            "rows": del_rows,
            "api_version": 2,
        }

        while True:
            res = conn.post("logs3", json=payload)
            if res.status_code == 429:
                print(f"{YELLOW}⏳ Rate limit on logs3. Waiting 15s...{RESET}")
                time.sleep(15)
                continue
            elif res.status_code != 200:
                print(f"{RED}❌ Batch delete failed: {res.status_code} - {res.text}{RESET}")
                return deleted_count
            break

        deleted_count += len(batch)
        pct = (deleted_count / total) * 100
        print(f"  • Progress: {deleted_count}/{total} records deleted ({pct:.1f}%)")
        time.sleep(0.3)

    print(f"\n{BOLD}{GREEN}🎉 Deletion complete! Successfully removed {deleted_count} records.{RESET}\n")
    return deleted_count


def main():
    parser = argparse.ArgumentParser(description="Clean up old/duplicate Braintrust logs.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the deletion. By default, script runs in safe --dry-run mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate cleanup without modifying data (default).",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support"),
        help="Target Braintrust project name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=250,
        help="Batch size for /logs3 delete requests.",
    )
    args = parser.parse_args()

    # Determine execution mode
    is_live = args.execute
    mode_str = f"{RED}{BOLD}LIVE EXECUTION{RESET}" if is_live else f"{CYAN}{BOLD}SAFE DRY-RUN{RESET}"

    print("\n" + "=" * 75)
    print(f"{BOLD} Meridian Pay Support Agent — Braintrust Log Cleanup Utility{RESET}")
    print(f" Target Project: {BOLD}{args.project}{RESET} | Mode: {mode_str}")
    print("=" * 75 + "\n")

    # 1. Login and get project info
    bt.login()
    conn = bt.api_conn()

    proj_res = conn.get("v1/project", params={"project_name": args.project})
    if proj_res.status_code != 200 or not proj_res.json().get("objects"):
        print(f"{RED}❌ Failed to find project '{args.project}': {proj_res.text}{RESET}")
        sys.exit(1)

    proj_obj = proj_res.json()["objects"][0]
    project_id = proj_obj["id"]
    org_id = proj_obj["org_id"]
    print(f"Connected to Braintrust (Org: {org_id}, Project: {project_id})\n")

    # 2. Fetch all root spans
    root_spans = fetch_all_root_spans(conn, args.project)

    # 3. Categorize spans
    cleanup_cats, preserved_cats = categorize_spans(root_spans)

    # Flatten candidates
    candidates = []
    for cat_name, items in cleanup_cats.items():
        candidates.extend(items)

    # Explicit Safety Check: Verify NO protected traces are candidates
    for c in candidates:
        tags = c.get("tags") or []
        meta = c.get("metadata") or {}
        if "annotated" in tags or "production-audit" in tags or meta.get("audit_id") or meta.get("failure_category"):
            print(f"{RED}FATAL ERROR: Protected trace {c['id']} was categorized as a cleanup candidate! Aborting immediately!{RESET}")
            sys.exit(1)

    # Print Breakdown Table
    print(f"{BOLD}📊 Audit & Cleanup Partition Summary:{RESET}")
    print(f"┌─────────────────────────────────────────────────────────────┬──────────┐")
    print(f"│ Category                                                    │ Count    │")
    print(f"├─────────────────────────────────────────────────────────────┼──────────┤")
    print(f"│ 1. Dummy / Test Root Spans (test_*)                         │ {len(cleanup_cats['dummy_tests']):>8} │")
    print(f"│ 2. Broken / Incomplete Traces (empty output/input)          │ {len(cleanup_cats['broken_incomplete']):>8} │")
    print(f"│ 3. Multi-Turn Thread Redundant Duplicates                   │ {len(cleanup_cats['thread_duplicates']):>8} │")
    print(f"│ 4. Single-Turn Agent Redundant Duplicates                   │ {len(cleanup_cats['agent_duplicates']):>8} │")
    print(f"├─────────────────────────────────────────────────────────────┼──────────┤")
    print(f"│ {RED}TOTAL CANDIDATE ROOT TRACES TO DELETE{RESET}                       │ {len(candidates):>8} │")
    print(f"├─────────────────────────────────────────────────────────────┼──────────┤")
    print(f"│ 5. Protected S2 Human Audit Spans (PRESERVED)               │ {len(preserved_cats['s2_protected_audits']):>8} │")
    print(f"│ 6. Canonical Single-Turn Agent Traces (PRESERVED)           │ {len(preserved_cats['canonical_agent_traces']):>8} │")
    print(f"│ 7. Canonical Multi-Turn Thread Traces (PRESERVED)           │ {len(preserved_cats['canonical_thread_traces']):>8} │")
    print(f"├─────────────────────────────────────────────────────────────┼──────────┤")
    total_preserved = (
        len(preserved_cats['s2_protected_audits'])
        + len(preserved_cats['canonical_agent_traces'])
        + len(preserved_cats['canonical_thread_traces'])
    )
    print(f"│ {GREEN}TOTAL ROOT TRACES PRESERVED{RESET}                                 │ {total_preserved:>8} │")
    print(f"└─────────────────────────────────────────────────────────────┴──────────┘")

    if not candidates:
        print(f"\n{GREEN}🎉 No low-quality duplicate or incomplete traces found! Braintrust logs are clean.{RESET}")
        return

    # 4. Resolve Child Spans for full cascading deletion
    all_target_ids = resolve_child_spans(conn, args.project, candidates)

    if not is_live:
        print(f"\n{YELLOW}{BOLD}ℹ️ [DRY RUN COMPLETED]{RESET}")
        print(f"  • In live mode, this would delete {len(candidates)} root traces and {len(all_target_ids) - len(candidates)} child spans.")
        print(f"  • {total_preserved} root traces would remain preserved.")
        print(f"  • To execute live cleanup, re-run with: {CYAN}python scripts/cleanup_braintrust_logs.py --execute{RESET}\n")
        return

    # 5. Live Execution
    execute_batch_delete(
        conn=conn,
        project_id=project_id,
        org_id=org_id,
        ids_to_delete=all_target_ids,
        batch_size=args.batch_size,
    )

    # 6. Final verification
    print(f"{CYAN}🔍 Verifying remaining log count in Braintrust...{RESET}")
    time.sleep(2)
    verify_res = conn.post("btql", json={"query": f'SELECT count(*) as total_count FROM project_logs("{args.project}") WHERE is_root = true'})
    if verify_res.status_code == 200:
        remaining_roots = verify_res.json().get("data", [{}])[0].get("total_count", "unknown")
        print(f"{GREEN}✅ Post-cleanup verification: {remaining_roots} root traces remain in '{args.project}'.{RESET}")


if __name__ == "__main__":
    main()
