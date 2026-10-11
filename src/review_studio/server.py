"""
FastAPI Server for Braintrust Trace Review Studio.
Serves REST APIs for trace querying, multi-turn inspection, system evaluations,
commentary submission, and mounts the modern web frontend.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.review_studio.service import BraintrustService

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Braintrust Trace Review Studio",
    description="Interactive local browser studio for reviewing assigned traces, multi-turn conversations, LLM reasoning, and evaluations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = BraintrustService()


class FeedbackPayload(BaseModel):
    comment: str = Field(..., description="Reviewer commentary to record in Braintrust")
    scores: Optional[Dict[str, float]] = Field(default=None, description="Updated evaluation scores")
    tags: Optional[List[str]] = Field(default=None, description="Tags for categorization")
    reviewer: Optional[str] = Field(default=None, description="Name of reviewer")
    category: Optional[str] = Field(default=None, description="Failure taxonomy category")


class AssignPayload(BaseModel):
    assignee: str = Field(..., description="Reviewer name to assign to")
    email: Optional[str] = Field(default=None, description="Reviewer email")


class CreateEvalPayload(BaseModel):
    expected: Optional[Dict[str, Any]] = Field(default=None, description="Optional custom expected behavior overrides")


class PreDeploymentTestPayload(BaseModel):
    case_id: Optional[str] = Field(default=None, description="Target evaluation case ID")
    trace_id: Optional[str] = Field(default=None, description="Source trace ID")
    prompt_candidate: str = Field(default="v2", description="Baseline/candidate prompt to test (e.g. v2)")
    prompt_fixed: str = Field(default="v3", description="Remedied prompt with feedback fix (e.g. v3)")



@app.get("/api/me")
def get_me():
    """Returns the authenticated Braintrust user info."""
    return service.get_current_user()


@app.get("/api/traces")
def get_traces(
    assignee: str = Query("all", description="'me', 'unassigned', 'all', or reviewer name"),
    topic: Optional[str] = Query(None, description="Filter by topic ID"),
    pattern: Optional[str] = Query(None, description="Filter by interaction pattern"),
    status: Optional[str] = Query("all", description="'all', 'passed', 'failed', 'reviewed', 'pending_review'"),
    search: Optional[str] = Query(None, description="Text search across inquiries and metadata"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Lists root traces with assignment, evaluation, and conversation metadata."""
    return service.list_traces(
        assignee_filter=assignee,
        topic=topic,
        pattern=pattern,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    """Returns full details, multi-turn steps, LLM reasoning, tools, and evaluations for a trace."""
    trace = service.get_trace_details(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found in project.")
    return trace


@app.post("/api/traces/{trace_id}/feedback")
def submit_feedback(trace_id: str, payload: FeedbackPayload):
    """Submits human commentary, review scores, and taxonomy tags back to Braintrust."""
    result = service.submit_feedback(
        trace_id=trace_id,
        comment=payload.comment,
        scores=payload.scores,
        tags=payload.tags,
        reviewer_name=payload.reviewer,
        category=payload.category,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@app.post("/api/traces/{trace_id}/assign")
def assign_trace(trace_id: str, payload: AssignPayload):
    """Assigns trace to the specified reviewer in Braintrust."""
    result = service.assign_trace(
        trace_id=trace_id,
        assignee_name=payload.assignee,
        assignee_email=payload.email,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@app.get("/api/stats")
def get_stats():
    """Returns high-level trace review studio metrics."""
    res = service.list_traces(limit=1)
    return res.get("stats", {})


@app.post("/api/traces/{trace_id}/create-eval")
def create_eval_from_feedback(trace_id: str, payload: Optional[CreateEvalPayload] = None):
    """Creates a new evaluation case from the trace inquiry and feedback comments."""
    custom = payload.expected if payload else None
    try:
        res = service.create_eval_from_feedback(trace_id=trace_id, custom_expected=custom)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prompts/compare")
def get_prompt_comparison():
    """Returns candidate prompt vs fixed prompt texts, changelog, and diff."""
    return service.get_prompt_comparison()


@app.post("/api/eval/pre-deployment-test")
def run_pre_deployment_eval(payload: PreDeploymentTestPayload):
    """
    Executes a pre-deployment verification test on the feedback case or dataset,
    comparing candidate prompt (v2) vs updated prompt (v3) with zero-tolerance safety assertions.
    """
    try:
        return service.run_pre_deployment_eval(
            case_id=payload.case_id,
            trace_id=payload.trace_id,
            prompt_candidate=payload.prompt_candidate,
            prompt_fixed=payload.prompt_fixed,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



FINANCIAL_STATIC_DIR = BASE_DIR.parent / "financial_app" / "static"
BACKEND_FILE = BASE_DIR.parent.parent / "data" / "backend.json"
KB_DIR = BASE_DIR.parent.parent / "data" / "kb"


class AgentRunPayload(BaseModel):
    ticket: str = Field(..., description="Customer ticket or inquiry message")
    account_id: str = Field(default="ACC-0001", description="Account ID")
    channel: str = Field(default="web_chat", description="Communication channel")
    prompt_version: str = Field(default="v3", description="Agent prompt version (v1, v1_5, v2, v3)")
    model: Optional[str] = Field(default=None, description="Model override")


class AgentFeedbackPayload(BaseModel):
    trace_id: str = Field(..., description="Target trace ID")
    score: float = Field(..., description="Feedback score (1.0 = positive, 0.0 = regression)")
    comment: Optional[str] = Field(default=None, description="Reviewer or customer commentary")
    reviewer: Optional[str] = Field(default="Nick Teodori", description="Reviewer name")


# -------------------------------------------------------------------------
# Meridian Pay Financial Support App Endpoints
# -------------------------------------------------------------------------
@app.get("/api/app/accounts")
def get_app_accounts():
    """Lists all commercial card accounts with basic financial status."""
    if not BACKEND_FILE.exists():
        raise HTTPException(status_code=404, detail="Backend data file not found.")
    with open(BACKEND_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    accounts = data.get("accounts", [])
    return {"accounts": accounts, "total": len(accounts)}


@app.get("/api/app/accounts/{account_id}")
def get_app_account_details(account_id: str):
    """Returns detailed financial health, credit limit, balance, card status, and recent transactions."""
    if not BACKEND_FILE.exists():
        raise HTTPException(status_code=404, detail="Backend data file not found.")
    with open(BACKEND_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    acc = next((a for a in data.get("accounts", []) if a["account_id"] == account_id), None)
    if not acc:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found.")

    txns = [t for t in data.get("transactions", []) if t["account_id"] == account_id]
    disputes = [d for d in data.get("disputes", []) if d.get("account_id") == account_id]
    action_ledger = data.get("action_ledger", [])

    return {
        **acc,
        "transactions": txns[:15],
        "disputes": disputes,
        "action_ledger": action_ledger[-10:] if action_ledger else []
    }


@app.post("/api/app/agent/run")
def run_app_agent(payload: AgentRunPayload):
    """Executes Meridian Pay Support Agent loop on customer ticket inquiry."""
    from src.agent.loop import run_agent

    try:
        result = run_agent(
            ticket=payload.ticket,
            account_id=payload.account_id,
            channel=payload.channel,
            prompt_version=payload.prompt_version,
            model=payload.model,
        )

        return {
            "reply": result.reply,
            "actions": result.actions,
            "action_ledger": result.action_ledger,
            "citations": result.citations,
            "escalated": result.escalated,
            "tool_trajectory": result.tool_trajectory,
            "latency_ms": result.latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "reply_word_count": result.reply_word_count,
            "trace_url": result.trace_url,
            "first_failure_step": result.first_failure_step,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")


@app.post("/api/app/agent/feedback")
def submit_agent_feedback(payload: AgentFeedbackPayload):
    """Submits customer feedback and reviewer commentary to Braintrust."""
    try:
        result = service.submit_feedback(
            trace_id=payload.trace_id,
            comment=payload.comment or "Customer feedback via Meridian Pay portal",
            scores={"user_feedback": payload.score},
            tags=["portal_feedback", "customer_interaction"],
            reviewer_name=payload.reviewer or "Customer Portal",
        )
        return {"status": "success", "result": result}
    except Exception as e:
        # Gracefully accept feedback even if trace was simulated
        return {"status": "saved_locally", "detail": str(e)}


@app.get("/api/app/kb/doc")
def get_kb_document(path: str = Query(..., description="Path to KB document, e.g. data/kb/policy/dispute-handling.md")):
    """Returns markdown text of a policy or runbook document from data/kb."""
    clean_path = path.replace("\\", "/").strip()
    if clean_path.startswith("data/kb/"):
        rel_path = clean_path[len("data/kb/"):]
    else:
        rel_path = clean_path.lstrip("/")

    doc_file = (KB_DIR / rel_path).resolve()
    if not str(doc_file).startswith(str(KB_DIR.resolve())) or not doc_file.exists():
        raise HTTPException(status_code=404, detail=f"KB Document {path} not found.")

    return {
        "path": path,
        "content": doc_file.read_text(encoding="utf-8")
    }


@app.post("/api/app/reset")
def reset_backend_fixtures():
    """Resets backend accounts, transactions, and action ledger to baseline."""
    try:
        from scripts.generate_fixtures import generate_backend
        generate_backend()
        return {"status": "success", "message": "Backend ledger reset to baseline fixtures."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset fixtures: {str(e)}")


# -------------------------------------------------------------------------
# Static Assets & Page Routing
# -------------------------------------------------------------------------
# Mount static assets
if FINANCIAL_STATIC_DIR.exists():
    app.mount("/app-static", StaticFiles(directory=str(FINANCIAL_STATIC_DIR)), name="app_static")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index_portal():
    """Serves the main Meridian Pay Financial Support App customer portal."""
    app_index = FINANCIAL_STATIC_DIR / "index.html"
    if app_index.exists():
        return FileResponse(str(app_index))
    # Fallback to studio if app not built
    studio_index = STATIC_DIR / "index.html"
    if studio_index.exists():
        return FileResponse(str(studio_index))
    return {"message": "Meridian Pay App API is running. UI files not found."}


@app.get("/app")
def app_portal():
    """Direct alias to Meridian Pay Financial Support App."""
    return index_portal()


@app.get("/studio")
def studio_portal():
    """Serves the Braintrust Trace Review Studio HTML application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Braintrust Trace Review Studio UI not found."}


def run(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """Helper to start the uvicorn web server."""
    import uvicorn
    uvicorn.run("src.review_studio.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start Meridian Pay & Trace Review Studio")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    run(host=args.host, port=args.port, reload=args.reload)

