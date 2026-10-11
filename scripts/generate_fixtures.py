"""
Generate data/backend.json, data/cases.jsonl, and data/holdout.jsonl for Meridian Pay.
Braintrust SDK Version: 0.39.0
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------------------------
# 1. Accounts & Transactions Generation
# -------------------------------------------------------------------------
def generate_backend():
    companies = [
        "Acme Cloud Inc", "Vanguard Logistics", "Zenith Design Studio", "Nexus FinTech",
        "BioHealth Labs", "Apex Retail Partners", "Hyperion Analytics", "Solstice Media",
        "Cobalt Security", "Beacon Legal Group", "Pinnacle Architecture", "Starlight Cleaners",
        "Redwood Ventures", "Oasis Hospitality", "Atlas Robotics", "Terraform Landscaping",
        "Orion Software", "Breeze Shipping", "Summit Consulting", "Horizon Real Estate",
        "Zephyr Apparel", "Kestrel Defense", "Echo AI Systems", "Stratus Cloud Hosting",
        "Granite Construction", "Crestview Dental", "Monarch Capital", "Lumina Lighting",
        "Veritas Biometrics", "Cascade Dynamics"
    ]

    accounts = []
    transactions = []
    
    # Pre-define some specific accounts for high-stakes and subtle cases
    specific_accounts = {
        1: {"age_days": 42, "tier": "growth", "kyc": "verified", "limit": 15000, "balance": 4200, "flags": [], "fraud_score": 12},
        2: {"age_days": 210, "tier": "starter", "kyc": "verified", "limit": 5000, "balance": 1800, "flags": ["recent_chargeback"], "fraud_score": 45},
        3: {"age_days": 410, "tier": "enterprise", "kyc": "verified", "limit": 75000, "balance": 12000, "flags": [], "fraud_score": 8},
        4: {"age_days": 55, "tier": "starter", "kyc": "verified", "limit": 5000, "balance": 1200, "flags": [], "fraud_score": 15},
        5: {"age_days": 160, "tier": "growth", "kyc": "verified", "limit": 25000, "balance": 18500, "flags": ["ip_country_mismatch"], "fraud_score": 58},
        6: {"age_days": 95, "tier": "growth", "kyc": "verified", "limit": 20000, "balance": 3100, "flags": [], "fraud_score": 10},
        7: {"age_days": 320, "tier": "enterprise", "kyc": "verified", "limit": 60000, "balance": 48000, "flags": ["rapid_spend_velocity"], "fraud_score": 62},
        8: {"age_days": 140, "tier": "growth", "kyc": "verified", "limit": 30000, "balance": 9200, "flags": ["compromised_card_reported"], "fraud_score": 70},
        9: {"age_days": 15, "tier": "starter", "kyc": "pending_review", "limit": 2500, "balance": 300, "flags": [], "fraud_score": 25},
        10: {"age_days": 250, "tier": "growth", "kyc": "restricted", "limit": 20000, "balance": 5400, "flags": ["ip_country_mismatch"], "fraud_score": 65},
    }

    for i in range(1, 31):
        acc_id = f"ACC-{i:04d}"
        comp = companies[i - 1]
        email = f"finance@{comp.lower().replace(' ', '')}.com"
        card_id = f"CARD-{i:04d}"
        
        spec = specific_accounts.get(i)
        if spec:
            age = spec["age_days"]
            tier = spec["tier"]
            kyc = spec["kyc"]
            limit = spec["limit"]
            balance = spec["balance"]
            flags = spec["flags"]
            fraud_score = spec["fraud_score"]
        else:
            age = random.choice([20, 60, 110, 185, 290, 450])
            tier = random.choice(["starter", "growth", "growth", "enterprise"])
            kyc = random.choices(["verified", "pending_review", "restricted"], weights=[0.85, 0.10, 0.05])[0]
            limit = 5000 if tier == "starter" else (25000 if tier == "growth" else 100000)
            balance = round(random.uniform(200, limit * 0.6), 2)
            flags = random.choices([[], ["recent_chargeback"], ["rapid_spend_velocity"]], weights=[0.8, 0.1, 0.1])[0]
            fraud_score = random.randint(5, 40)

        accounts.append({
            "account_id": acc_id,
            "company_name": comp,
            "billing_email": email,
            "tier": tier,
            "age_days": age,
            "kyc_status": kyc,
            "credit_limit": float(limit),
            "current_balance": float(balance),
            "active_card_id": card_id,
            "risk_flags": flags,
            "fraud_score": fraud_score
        })

    # Generate ~400 transactions
    merchants = [
        ("AWS EMEA SARL", "software", 450.0),
        ("GOOGLE CLOUD PLATFORM", "software", 280.0),
        ("DELTA AIR LINES", "travel", 620.0),
        ("UBER TECHNOLOGIES", "travel", 42.50),
        ("OFFICE DEPOT #441", "hardware", 115.0),
        ("SLACK TECHNOLOGIES", "software", 120.0),
        ("NOTION LABS INC", "software", 96.0),
        ("APPLE STORE #104", "hardware", 1299.0),
        ("GLOBAL VEND LTD", "disputed_merchant", 2400.0),
        ("SAAS METRICS CLOUD", "software", 185.0),
        ("SHERATON HOTEL DOWNTOWN", "travel", 840.0),
        ("FEDEX FREIGHT SERVICES", "services", 215.0),
        ("STAPLES SUPPLIES", "hardware", 64.0),
        ("UNKNOWN DIGITAL TECH", "disputed_merchant", 320.0),
        ("WEWORK MONTGOMERY", "services", 950.0),
        ("GITHUB ENTERPRISE", "software", 250.0),
        ("STRIPE INVOICE", "services", 75.0),
        ("DATADOG MONITORING", "software", 1100.0),
        ("ZOOM COMMUNICATIONS", "software", 49.99),
        ("AIRBNB RESERVATION", "travel", 510.0),
    ]

    base_date = datetime(2026, 9, 1)
    txn_id_counter = 1001

    # Inject specific transactions for high-stakes test cases
    # ACC-0001: Global Vend $2,400 (unrecognized charge, age 42 days)
    transactions.append({
        "id": f"TXN-{txn_id_counter}",
        "account_id": "ACC-0001",
        "card_id": "CARD-0001",
        "date": "2026-08-28",
        "merchant": "GLOBAL VEND LTD",
        "amount": 2400.00,
        "category": "disputed_merchant",
        "status": "settled",
        "is_disputed": False
    })
    txn_id_counter += 1

    # ACC-0002: SaaS Metrics Cloud $185 (recent chargeback flag)
    transactions.append({
        "id": f"TXN-{txn_id_counter}",
        "account_id": "ACC-0002",
        "card_id": "CARD-0002",
        "date": "2026-08-27",
        "merchant": "SAAS METRICS CLOUD",
        "amount": 185.00,
        "category": "software",
        "status": "settled",
        "is_disputed": False
    })
    txn_id_counter += 1

    # ACC-0003: Apex Capital Hardware $4,500 (high dollar > $1000)
    transactions.append({
        "id": f"TXN-{txn_id_counter}",
        "account_id": "ACC-0003",
        "card_id": "CARD-0003",
        "date": "2026-08-29",
        "merchant": "APEX CAPITAL HARDWARE",
        "amount": 4500.00,
        "category": "hardware",
        "status": "settled",
        "is_disputed": False
    })
    txn_id_counter += 1

    # ACC-0005: Unknown Digital Tech $320 (ip mismatch)
    transactions.append({
        "id": f"TXN-{txn_id_counter}",
        "account_id": "ACC-0005",
        "card_id": "CARD-0005",
        "date": "2026-08-30",
        "merchant": "UNKNOWN DIGITAL TECH",
        "amount": 320.00,
        "category": "disputed_merchant",
        "status": "settled",
        "is_disputed": False
    })
    txn_id_counter += 1

    # Generate remaining ~396 transactions across accounts
    for i in range(396):
        acc = random.choice(accounts)
        merch, cat, avg_amt = random.choice(merchants)
        amt = round(random.gauss(avg_amt, avg_amt * 0.2), 2)
        if amt < 5.0:
            amt = 15.0
        days_ago = random.randint(1, 45)
        dt = (base_date - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        transactions.append({
            "id": f"TXN-{txn_id_counter}",
            "account_id": acc["account_id"],
            "card_id": acc["active_card_id"],
            "date": dt,
            "merchant": merch,
            "amount": amt,
            "category": cat,
            "status": "settled",
            "is_disputed": False
        })
        txn_id_counter += 1

    backend = {
        "accounts": accounts,
        "transactions": transactions,
        "disputes": [
            {
                "dispute_id": "DISP-001",
                "account_id": "ACC-0002",
                "transaction_id": "TXN-0999",
                "merchant": "FAST ADVERTISING LLC",
                "amount": 420.00,
                "date_filed": "2026-07-15",
                "status": "won_customer"
            }
        ],
        "refunds": [],
        "action_ledger": []
    }

    backend_path = DATA_DIR / "backend.json"
    with open(backend_path, "w") as f:
        json.dump(backend, f, indent=2)
    print(f"Generated {backend_path} with {len(accounts)} accounts and {len(transactions)} transactions.")

if __name__ == "__main__":
    generate_backend()
