#!/usr/bin/env python3
"""
Launcher script for Braintrust Trace Review Studio.
Starts the FastAPI server and optionally opens your default browser.
"""

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.review_studio.server import run


def main():
    parser = argparse.ArgumentParser(description="Launch Braintrust Trace Review Studio in your local browser")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print("\n" + "=" * 75)
    print("🚀 BRAINTRUST TRACE REVIEW STUDIO")
    print(f"URL:        {url}")
    print(f"Project:    {os.getenv('BRAINTRUST_PROJECT_NAME', 'meridian-pay-support')}")
    print("Features:   Multi-turn threads, LLM reasoning, system evals & commentary sync")
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
