import os
import time
import json
import requests
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler

# 1. Discord Webhook URL (Reads from environment or falls back to placeholder)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# 2. Path to audit logs directory
TARGET_FOLDER = r"D:\Hucdeline\audit_logs"

def send_discord_notification(message: str) -> bool:
    """Send notification payload to Discord webhook and log status to console."""
    if not DISCORD_WEBHOOK_URL.startswith("http"):
        print(f"[{time.strftime('%X')}] ❌ ERROR: Invalid DISCORD_WEBHOOK_URL format!")
        return False

    payload = {
        "content": message,
        "username": "MCP Auditor Bot"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code in (200, 204):
            print(f"[{time.strftime('%X')}] ✅ Discord notification sent successfully!")
            return True
        else:
            print(f"[{time.strftime('%X')}] ❌ Delivery failed (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[{time.strftime('%X')}] ❌ Network connection: {e}")
        return False

def format_audit_markdown(file_path: str, data: dict) -> str:
    filename = os.path.basename(file_path)
    status_str = str(data.get("status", "")).upper()
    
    if "APPROVED" in filename.upper() or "APPROVED" in status_str:
        status_badge = "✅ APPROVED (Code Passed Audit)"
    elif "REJECTED" in filename.upper() or "REJECTED" in status_str:
        status_badge = "❌ REJECTED (Violations Found)"
    else:
        status_badge = f"ℹ️ {status_str or 'AUDIT LOG'}"

    target = data.get("file") or data.get("target") or data.get("action") or data.get("file_name") or data.get("title")
    score = data.get("score") or data.get("rating")
    summary = data.get("summary") or data.get("reason") or data.get("message") or data.get("verdict")
    findings = data.get("violations") or data.get("issues") or data.get("findings") or data.get("errors")

    sections = []
    if target:
        sections.append(f"🎯 **Target / Action:** `{target}`")
    if score is not None:
        sections.append(f"📊 **Audit Score:** `{score}`")
    if summary:
        sections.append(f"📝 **Summary:**\n> {summary}")
    
    if findings:
        if isinstance(findings, list) and findings:
            finding_lines = "\n".join([f"• {str(item)[:120]}" for item in findings[:6]])
            if len(findings) > 6:
                finding_lines += f"\n• ... and {len(findings)-6} more items"
            sections.append(f"⚠️ **Issues / Findings:**\n{finding_lines}")
        elif isinstance(findings, dict):
            json_snippet = json.dumps(findings, ensure_ascii=False, indent=2)[:400]
            sections.append(f"⚠️ **Findings:**\n```json\n{json_snippet}\n```")

    if not sections:
        json_snippet = json.dumps(data, ensure_ascii=False, indent=2)
        if len(json_snippet) > 1000:
            json_snippet = json_snippet[:1000] + "\n...(content truncated)..."
        sections.append(f"📋 **Log Content:**\n```json\n{json_snippet}\n```")

    body = "\n\n".join(sections)
    msg = (
        f"🛡️ **[MCP Local Auditor] New Audit Report**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Status:** **{status_badge}**\n"
        f"📁 **File:** `{filename}`\n"
        f"🕒 **Time:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{body}"
    )
    if len(msg) > 1900:
        msg = msg[:1900] + "\n\n...(content truncated due to length limit)..."
    return msg

class AuditLogHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.processed = {}

    def process_file(self, file_path: str):
        if not file_path.lower().endswith(".json"):
            return

        filename = os.path.basename(file_path)
        current_time = time.time()
        
        # Debounce window: 2 seconds
        if current_time - self.processed.get(filename, 0) < 2:
            return
        self.processed[filename] = current_time

        print(f"[{time.strftime('%X')}] 📥 Detected JSON log file: {filename}")
        
        # Read JSON file with retry mechanism
        data = None
        for _ in range(5):
            time.sleep(0.3)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                break
            except Exception:
                continue

        if data is not None:
            msg = format_audit_markdown(file_path, data)
            send_discord_notification(msg)
        else:
            print(f"[{time.strftime('%X')}] ⚠️ Unable to parse JSON from {filename}")

    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.process_file(event.dest_path)

if __name__ == "__main__":
    target_dir = os.path.abspath(TARGET_FOLDER)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    print("====================================================")
    print("  Testing Discord Webhook Connection...")
    print("====================================================")
    
    test_ok = send_discord_notification("🚀 **[MCP Auditor Bot] Service Online** Monitoring`...")
    if not test_ok:
        print("\n⚠️ Connection failed. Please verify your network and webhook URL.")
    else:
        print("✅ Discord connection verified successfully.")

    event_handler = AuditLogHandler()
    observer = Observer()
    observer.schedule(event_handler, path=target_dir, recursive=False)
    observer.start()
    print(f"\n🛡️ Monitoring directory: {target_dir}")
    print("   (Place a new .json log into the folder to trigger. Press Ctrl+C to exit)...\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()