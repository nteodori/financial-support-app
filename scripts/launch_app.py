#!/usr/bin/env python3
"""
Launcher script for Meridian Pay Financial Support App & Customer Portal.
Starts the FastAPI server and optionally opens your default browser at http://127.0.0.1:8000/
"""

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv()

from src.review_studio.server import run


def main():
    parser = argparse.ArgumentParser(description="Launch Meridian Pay Financial Support App in your local browser")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print("\n" + "=" * 75)
    print("💳 MERIDIAN PAY — COMMERCIAL CARD & FINANCIAL SUPPORT PORTAL")
    print(f"Customer Portal: {url}")
    print(f"Review Studio:   {url}/studio")
    print(f"Braintrust Proj: {os.getenv('BRAINTRUST_PROJECT_NAME', 'meridian-pay-support')}")
    print("Features:        Live AI Agent Concierge, Tool Spans, Action Ledger, KB Runbooks")
    print("=" * 75 + "\n")

    if not args.no_browser:
        def open_browser():
            time.sleep(1.0)
            print(f"🌐 Opening {url} in your default browser...")
            webbrowser.open(url)

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    run(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
