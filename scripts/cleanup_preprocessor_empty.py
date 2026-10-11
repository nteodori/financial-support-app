"""
Cleanup utility to delete records with metadata.preprocessor_empty = true from Braintrust project logs.
Braintrust SDK Version: 0.39.0
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

load_dotenv()


def cleanup_preprocessor_empty_records(project_name: str = "meridian-pay-support", batch_size: int = 250) -> int:
    bt_key = os.getenv("BRAINTRUST_API_KEY")
    if not bt_key:
        print("❌ Error: BRAINTRUST_API_KEY environment variable is not set.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {bt_key}",
        "Content-Type": "application/json"
    }

    # 1. Fetch project ID and org ID
    print(f"\n🔍 Connecting to project '{project_name}'...")
    proj_res = requests.get(f"https://api.braintrust.dev/v1/project?project_name={project_name}", headers=headers)
    if proj_res.status_code != 200 or not proj_res.json().get("objects"):
        print(f"❌ Failed to find project: {proj_res.text}")
        sys.exit(1)

    proj_obj = proj_res.json()["objects"][0]
    proj_id = proj_obj["id"]
    org_id = proj_obj["org_id"]
    print(f"  • Project ID: {proj_id}")
    print(f"  • Org ID:     {org_id}")

    total_deleted = 0

    while True:
        # 2. Query BTQL for records with preprocessor_empty = true
        btql_query = f"""
            SELECT id FROM project_logs("{project_name}")
            WHERE metadata.preprocessor_empty = true
            LIMIT {batch_size}
        """
        r = requests.post("https://api.braintrust.dev/btql", headers=headers, json={"query": btql_query})
        if r.status_code != 200:
            print(f"❌ Error querying BTQL: {r.status_code} - {r.text}")
            break

        records = r.json().get("data", [])
        if not records:
            print("✅ No more records with metadata.preprocessor_empty = true found.")
            break

        ids_to_delete = [rec["id"] for rec in records if rec.get("id")]
        print(f"🗑️ Found {len(ids_to_delete)} records to delete (Batch total: {total_deleted + len(ids_to_delete)})...")

        # 3. Batch delete via /logs3 endpoint
        del_rows = [
            {
                "id": rec_id,
                "log_id": "g",
                "org_id": org_id,
                "project_id": proj_id,
                "_object_delete": True,
            }
            for rec_id in ids_to_delete
        ]

        del_payload = {
            "rows": del_rows,
            "api_version": 2
        }

        del_resp = requests.post("https://api.braintrust.dev/logs3", headers=headers, json=del_payload)
        if del_resp.status_code == 200:
            total_deleted += len(ids_to_delete)
            print(f"  • Successfully deleted batch of {len(ids_to_delete)} records.")
        else:
            print(f"❌ Delete batch failed: {del_resp.status_code} - {del_resp.text}")
            break

        time.sleep(0.5)

    print(f"\n🎉 Total preprocessor_empty records cleaned up: {total_deleted}")
    return total_deleted


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.getenv("BRAINTRUST_PROJECT_NAME", "meridian-pay-support")
    cleanup_preprocessor_empty_records(project_name=proj)
