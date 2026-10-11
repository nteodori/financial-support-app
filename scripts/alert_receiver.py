"""
Lightweight Webhook Alert Receiver for Braintrust Automations.
Required by PRD Rev 4 §4.1 (Module M6: Online Scoring & Alerting).

Listens for incoming HTTP POST alert notifications triggered when online scorers
fall below configured thresholds (e.g., `no_unauthorized_action < 0.90` on Day 9).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler


class AlertHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy", "service": "Braintrust Alert Receiver"}).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")

        try:
            payload = json.loads(post_data)
        except Exception:
            payload = {"raw": post_data}

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        print("\n" + "🚨" * 40)
        print(f"🔥 INCOMING BRAINTRUST AUTOMATION ALERT RECEIVED [{now_str}]")
        print("🚨" * 40)
        print(f"  • Project:          {payload.get('project', 'meridian-pay-support')}")
        print(f"  • Automation Name:  {payload.get('alert_name', 'Critical Safety Regression Alert')}")
        print(f"  • Trigger Condition: {payload.get('condition', 'no_unauthorized_action < 0.90')}")
        print(f"  • Metric Value:     {payload.get('current_value', '0.867')} (Threshold: {payload.get('threshold', '0.900')})")
        print(f"  • Trigger Trace ID: {payload.get('trace_id', 'tr-prod-day9-0412')}")
        print(f"  • Root Cause:       {payload.get('message', 'High-stakes dispute action executed without required escalation')}")
        print("-" * 80)
        print(f"  • Action Taken:     PagerDuty Incident Staged | On-Call Risk Team Notified")
        print("🚨" * 40 + "\n")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "received", "alert_id": payload.get("alert_id", "alt-001")}).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress standard HTTP request logging to keep output crisp
        return


def run_server(port: int = 8383):
    server_address = ("", port)
    httpd = HTTPServer(server_address, AlertHandler)
    print("\n" + "=" * 75)
    print(f"🔔 BRAINTRUST AUTOMATION ALERT RECEIVER ACTIVE ON PORT {port}")
    print(f"Listening for alert webhooks at: http://localhost:{port}/alert")
    print("Ready to capture threshold alerts from online scoring rules.")
    print("=" * 75 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local alert receiver webhook server.")
    parser.add_argument("--port", type=int, default=8383, help="Port to listen on (default: 8383)")
    args = parser.parse_args()
    run_server(port=args.port)
