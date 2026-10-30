import json
import subprocess
import time
import os

SEEN_FILE = "seen_ids.txt"
ACCOUNT = "openclawtesting00@gmail.com"

# Load existing seen IDs
seen_ids = set()
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE) as f:
        seen_ids = {line.strip() for line in f if line.strip()}

# On first run, seed all CURRENT unread messages as already seen
print("Initializing seen message cache from Gmail...")
try:
    init_raw = subprocess.check_output(
        ["gog", "gmail", "messages", "search", f"to:{ACCOUNT} is:unread", "--account", ACCOUNT, "--max", "50", "--json"],
        stderr=subprocess.DEVNULL
    )
    init_data = json.loads(init_raw.decode("utf-8", errors="ignore")) if init_raw.strip() else []
    init_msgs = init_data if isinstance(init_data, list) else init_data.get("messages", [])
    new_seeds = 0
    with open(SEEN_FILE, "a") as f:
        for m in init_msgs:
            mid = m.get("id")
            if mid and mid not in seen_ids:
                seen_ids.add(mid)
                f.write(f"{mid}\n")
                new_seeds += 1
    print(f"Cached {len(seen_ids)} existing messages (ignored so they won't repeat).")
except Exception as e:
    print(f"Warning during seed: {e}")

print("\n👀 Live Email Agent is RUNNING and WAITING for new incoming emails...")
print("👉 Send your test email now. (Press Ctrl+C to stop)\n")

while True:
    try:
        raw = subprocess.check_output(
            ["gog", "gmail", "messages", "search", f"to:{ACCOUNT} is:unread", "--account", ACCOUNT, "--max", "5", "--json"],
            stderr=subprocess.DEVNULL
        )
        data = json.loads(raw.decode("utf-8", errors="ignore")) if raw.strip() else []
        messages = data if isinstance(data, list) else data.get("messages", [])

        for msg in messages:
            msg_id = msg.get("id")
            if not msg_id or msg_id in seen_ids:
                continue

            # A genuinely new email arrived
            now = time.strftime("%H:%M:%S")
            print(f"[{now}] 📨 Incoming new email detected! ID: {msg_id}")
            seen_ids.add(msg_id)
            with open(SEEN_FILE, "a") as f:
                f.write(f"{msg_id}\n")

            # Ingest through the pipeline
            proc = subprocess.Popen(
                ["python3", "pipeline.py", "ingest"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            stdout, _ = proc.communicate(input=json.dumps([msg]))

            # Clean output display
            try:
                res = json.loads(stdout)
                for r in res.get("results", []):
                    print(f"   ✅ Subject:    {r.get('subject')}")
                    print(f"   🎯 Category:   {r.get('categories')}")
                    print(f"   📤 Dispatched: {r.get('recipients')}")
                    print(f"   ☁️  Archived:   Azure Blob Container 'openclaw-ul'")
            except Exception:
                print(f"   Processed email ID: {msg_id}")

            print(f"[{now}] ⏸️  Waiting for next email...\n")

    except Exception:
        pass

    time.sleep(5)
