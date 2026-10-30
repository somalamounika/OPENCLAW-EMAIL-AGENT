import subprocess
import time
import json
import re
import sys
import os

ACCOUNT = os.environ.get("GMAIL_SENDER", "openclawtesting00@gmail.com")
POLL_INTERVAL = 10  # check every 10 seconds

print(f"[live-monitor] Starting continuous background watcher for {ACCOUNT}...")
print(f"[live-monitor] Polling interval: {POLL_INTERVAL}s")

while True:
    try:
        # Check for unread emails in INBOX
        cmd_list = [
            "gog", "-j", "--account", ACCOUNT,
            "gmail", "list", "label:INBOX is:unread", "--max", "10"
        ]
        res = subprocess.run(cmd_list, capture_output=True, text=True)

        if res.returncode == 0 and res.stdout.strip():
            msg_ids = re.findall(r'"id":\s*"([a-f0-9]+)"', res.stdout)
            # Deduplicate preserving order
            unique_ids = list(dict.fromkeys(msg_ids))

            for msg_id in unique_ids:
                print(f"\n[live-monitor] >>> New unread email detected: {msg_id}")
                
                # Fetch full email JSON payload
                p1 = subprocess.Popen(
                    ["gog", "-j", "--account", ACCOUNT, "gmail", "get", msg_id],
                    stdout=subprocess.PIPE
                )
                
                # Ingest & automatically route/dispatch
                p2 = subprocess.run(
                    [sys.executable, "pipeline.py", "ingest"],
                    stdin=p1.stdout,
                    capture_output=True,
                    text=True
                )
                p1.stdout.close()

                print("[live-monitor] Pipeline execution:")
                if p2.stdout.strip():
                    print(p2.stdout.strip())
                if p2.stderr.strip():
                    print("[live-monitor] Stderr:", p2.stderr.strip())

                # Mark email as read by removing UNREAD label to prevent duplicate processing
                sub_mod = subprocess.run(
                    ["gog", "--account", ACCOUNT, "gmail", "modify", msg_id, "--remove-labels", "UNREAD"],
                    capture_output=True,
                    text=True
                )
                if sub_mod.returncode == 0:
                    print(f"[live-monitor] Marked {msg_id} as processed (removed UNREAD).")
                else:
                    print(f"[live-monitor] Note: could not update labels for {msg_id}: {sub_mod.stderr.strip()}")

    except Exception as exc:
        print("[live-monitor] Polling loop error:", exc)

    time.sleep(POLL_INTERVAL)
