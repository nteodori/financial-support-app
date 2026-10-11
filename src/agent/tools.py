"""
Tool definitions and backend ledger bindings for Meridian Pay Support Agent.
Braintrust SDK Version: 0.39.0
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.agent.retrieval import get_retriever

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_FILE = BASE_DIR / "data" / "backend.json"


class ToolContext:
    def __init__(self, backend_path: Path = BACKEND_FILE):
        self.backend_path = backend_path
        self.data: Dict[str, Any] = {}
        self.action_ledger: List[Dict[str, Any]] = []
        self.retrieved_citations: List[str] = []
        self.reload()

    def reload(self):
        if self.backend_path.exists():
            with open(self.backend_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "accounts": [],
                "transactions": [],
                "disputes": [],
                "refunds": [],
                "action_ledger": []
            }
        self.action_ledger = []
        self.retrieved_citations = []

    def log_action(self, action: str, params: Dict[str, Any], money_moving: bool = False):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "params": params,
            "money_moving": money_moving
        }
        self.action_ledger.append(entry)
        # Also append to backend data in memory
        if "action_ledger" not in self.data:
            self.data["action_ledger"] = []
        self.data["action_ledger"].append(entry)

    # -------------------------------------------------------------------------
    # Tool Implementations
    # -------------------------------------------------------------------------
    def search_kb(self, query: str) -> List[Dict[str, Any]]:
        retriever = get_retriever()
        results = retriever.search(query, top_k=4)
        for r in results:
            doc_path = r["doc_path"]
            if doc_path not in self.retrieved_citations:
                self.retrieved_citations.append(doc_path)
        return results

    def get_account(self, account_id: str) -> Dict[str, Any]:
        acc = next((a for a in self.data.get("accounts", []) if a["account_id"] == account_id), None)
        if not acc:
            return {"error": f"Account {account_id} not found."}
        return {
            "account_id": acc["account_id"],
            "company_name": acc["company_name"],
            "tier": acc["tier"],
            "age_days": acc["age_days"],
            "kyc_status": acc["kyc_status"],
            "credit_limit": acc["credit_limit"],
            "current_balance": acc["current_balance"],
            "active_card_id": acc["active_card_id"],
            "risk_flags": acc["risk_flags"],
            "fraud_score": acc["fraud_score"]
        }

    def list_transactions(self, account_id: str, days: int = 30) -> List[Dict[str, Any]]:
        txns = [t for t in self.data.get("transactions", []) if t["account_id"] == account_id]
        return txns[:15]

    def get_dispute_history(self, account_id: str) -> List[Dict[str, Any]]:
        disputes = [d for d in self.data.get("disputes", []) if d["account_id"] == account_id]
        return disputes

    def open_dispute(self, transaction_id: str, reason: str) -> Dict[str, Any]:
        self.log_action("open_dispute", {"transaction_id": transaction_id, "reason": reason}, money_moving=True)
        return {
            "status": "success",
            "dispute_id": f"DISP-{len(self.data.get('disputes', [])) + 101}",
            "transaction_id": transaction_id,
            "message": f"Dispute opened for {transaction_id}. Reason: {reason}"
        }

    def issue_refund(self, account_id: str, amount: float, reason: str) -> Dict[str, Any]:
        self.log_action("issue_refund", {"account_id": account_id, "amount": amount, "reason": reason}, money_moving=True)
        return {
            "status": "success",
            "account_id": account_id,
            "amount": amount,
            "message": f"Refund of ${amount:.2f} credited to account {account_id}."
        }

    def replace_card(self, card_id: str, reason: str) -> Dict[str, Any]:
        self.log_action("replace_card", {"card_id": card_id, "reason": reason}, money_moving=False)
        new_card_id = f"CARD-{card_id.replace('CARD-', '')}-NEW"
        return {
            "status": "success",
            "old_card_id": card_id,
            "new_card_id": new_card_id,
            "message": f"Card {card_id} blocked and replacement {new_card_id} issued ({reason})."
        }

    def adjust_limit(self, account_id: str, new_limit: float) -> Dict[str, Any]:
        self.log_action("adjust_limit", {"account_id": account_id, "new_limit": new_limit}, money_moving=True)
        return {
            "status": "success",
            "account_id": account_id,
            "new_limit": new_limit,
            "message": f"Credit limit adjusted to ${new_limit:.2f}."
        }

    def request_documents(self, account_id: str, doc_type: str) -> Dict[str, Any]:
        self.log_action("request_documents", {"account_id": account_id, "doc_type": doc_type}, money_moving=False)
        return {
            "status": "success",
            "account_id": account_id,
            "doc_type": doc_type,
            "message": f"Document upload request sent for {doc_type} to account billing email."
        }

    def escalate(self, reason: str, queue: str = "fraud") -> Dict[str, Any]:
        self.log_action("escalate", {"reason": reason, "queue": queue}, money_moving=False)
        return {
            "status": "success",
            "queue": queue,
            "ticket_escalated": True,
            "message": f"Case escalated to {queue.upper()} investigation queue. Reason: {reason}"
        }


# -------------------------------------------------------------------------
# Anthropic Tool Schemas
# -------------------------------------------------------------------------
ANTHROPIC_TOOLS = [
    {
        "name": "search_kb",
        "description": "Search the Meridian Pay knowledge base for company policy, card rules, settlement rails, refund authority, and runbooks. Always consult when answering policy or procedure questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query keywords, e.g. 'unrecognized charge policy fraud threshold' or 'card replacement'."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_account",
        "description": "Retrieve comprehensive account context including account age (age_days), tier, KYC status, credit limit, balance, risk flags, and fraud score. MUST be fetched before making decisions on money-moving actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID, e.g. 'ACC-0001'."
                }
            },
            "required": ["account_id"]
        }
    },
    {
        "name": "list_transactions",
        "description": "List recent transactions for an account including transaction ID, date, merchant, dollar amount, category, and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID."
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of transaction history to retrieve (default 30)."
                }
            },
            "required": ["account_id"]
        }
    },
    {
        "name": "get_dispute_history",
        "description": "Retrieve historical charge disputes and chargeback outcomes on an account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID."
                }
            },
            "required": ["account_id"]
        }
    },
    {
        "name": "open_dispute",
        "description": "Open a formal payment dispute against a settled transaction. MONEY-MOVING ACTION: Subject to strict fraud thresholds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "The transaction ID being disputed, e.g. 'TXN-1001'."
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the dispute, e.g. 'unrecognized_merchant', 'duplicate_charge'."
                }
            },
            "required": ["transaction_id", "reason"]
        }
    },
    {
        "name": "issue_refund",
        "description": "Issue a direct cash refund/credit to the customer's account balance. MONEY-MOVING ACTION: Limited to $50 goodwill fee concessions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID."
                },
                "amount": {
                    "type": "number",
                    "description": "Refund amount in USD."
                },
                "reason": {
                    "type": "string",
                    "description": "Justification for the refund."
                }
            },
            "required": ["account_id", "amount", "reason"]
        }
    },
    {
        "name": "replace_card",
        "description": "Block an existing compromised, lost, or damaged card and immediately issue a replacement card.",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_id": {
                    "type": "string",
                    "description": "Card ID to block and reissue, e.g. 'CARD-0001'."
                },
                "reason": {
                    "type": "string",
                    "enum": ["lost_stolen", "damaged", "compromised"],
                    "description": "Reason for replacement."
                }
            },
            "required": ["card_id", "reason"]
        }
    },
    {
        "name": "adjust_limit",
        "description": "Adjust the commercial revolving credit limit on an account. MONEY-MOVING ACTION: Must satisfy strict underwriting criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID."
                },
                "new_limit": {
                    "type": "number",
                    "description": "New credit limit in USD."
                }
            },
            "required": ["account_id", "new_limit"]
        }
    },
    {
        "name": "request_documents",
        "description": "Send an official compliance document request to the account holder for KYC or heightened due diligence verification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID."
                },
                "doc_type": {
                    "type": "string",
                    "description": "Type of documents required, e.g. 'government_id_business_license' or 'proof_of_address_utility'."
                }
            },
            "required": ["account_id", "doc_type"]
        }
    },
    {
        "name": "escalate",
        "description": "Escalate a high-stakes, ambiguous, or fraud-flagged case to a specialized human review queue (fraud, compliance, underwriting, finance, or security).",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Detailed justification for the escalation."
                },
                "queue": {
                    "type": "string",
                    "enum": ["fraud", "compliance", "underwriting", "finance", "security"],
                    "description": "Target escalation queue."
                }
            },
            "required": ["reason", "queue"]
        }
    },
    {
        "name": "reply",
        "description": "Send the final resolution response to the customer. Calling this ends the agent execution loop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The message to send to the customer."
                }
            },
            "required": ["text"]
        }
    }
]


def execute_tool(tool_context: ToolContext, name: str, arguments: Dict[str, Any]) -> Any:
    if name == "search_kb":
        return tool_context.search_kb(arguments.get("query", ""))
    elif name == "get_account":
        return tool_context.get_account(arguments.get("account_id", ""))
    elif name == "list_transactions":
        return tool_context.list_transactions(arguments.get("account_id", ""), arguments.get("days", 30))
    elif name == "get_dispute_history":
        return tool_context.get_dispute_history(arguments.get("account_id", ""))
    elif name == "open_dispute":
        return tool_context.open_dispute(arguments.get("transaction_id", ""), arguments.get("reason", ""))
    elif name == "issue_refund":
        return tool_context.issue_refund(arguments.get("account_id", ""), float(arguments.get("amount", 0)), arguments.get("reason", ""))
    elif name == "replace_card":
        return tool_context.replace_card(arguments.get("card_id", ""), arguments.get("reason", "lost_stolen"))
    elif name == "adjust_limit":
        return tool_context.adjust_limit(arguments.get("account_id", ""), float(arguments.get("new_limit", 0)))
    elif name == "request_documents":
        return tool_context.request_documents(arguments.get("account_id", ""), arguments.get("doc_type", ""))
    elif name == "escalate":
        return tool_context.escalate(arguments.get("reason", ""), arguments.get("queue", "fraud"))
    elif name == "reply":
        return {"reply_sent": True, "text": arguments.get("text", "")}
    else:
        return {"error": f"Unknown tool: {name}"}
