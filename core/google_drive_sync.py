import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import requests
from config.settings import PROJECT_ROOT

GOOGLE_DRIVE_CSV_FILE = PROJECT_ROOT / "db" / "google_drive_emails.csv"

def init_google_drive_csv() -> None:
    """Initializes the local CSV sync ledger if it does not exist."""
    GOOGLE_DRIVE_CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not GOOGLE_DRIVE_CSV_FILE.exists():
        with open(GOOGLE_DRIVE_CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "learner_id", "name", "email", "role", "sync_status", "error_message"])

def sync_email_to_google_sheet(learner_id: str, name: str, email: str, role: str) -> Tuple[bool, str]:
    """
    Appends learner email details to Google Drive.
    1. Always logs to local ledger db/google_drive_emails.csv.
    2. If GOOGLE_SHEET_WEBHOOK_URL is configured in .env, transmits payload via HTTP POST.
    3. Returns success boolean and descriptive message.
    """
    init_google_drive_csv()
    now_str = datetime.now().isoformat()
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()
    
    sync_status = "PENDING_CONFIG"
    message = "Saved to local ledger. Awaiting Google Drive Sheet Webhook/API configuration."
    
    if webhook_url:
        try:
            payload = {
                "timestamp": now_str,
                "learner_id": learner_id,
                "name": name,
                "email": email,
                "role": role
            }
            resp = requests.post(webhook_url, json=payload, timeout=8)
            if resp.status_code in (200, 201):
                sync_status = "SYNCED_GOOGLE_DRIVE"
                message = f"Successfully synced {email} to Google Drive Sheet via Webhook."
            else:
                sync_status = f"HTTP_{resp.status_code}"
                message = f"Google Sheet Webhook returned HTTP {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            sync_status = "ERROR"
            message = f"Google Sheet sync error: {str(e)}"
            
    # Record in CSV ledger
    with open(GOOGLE_DRIVE_CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([now_str, learner_id, name, email, role, sync_status, message])
        
    return (sync_status == "SYNCED_GOOGLE_DRIVE", message)

def get_google_drive_sync_records() -> List[Dict[str, str]]:
    """Returns all sync records from the local ledger."""
    init_google_drive_csv()
    records = []
    if GOOGLE_DRIVE_CSV_FILE.exists():
        with open(GOOGLE_DRIVE_CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
    return records

def get_google_drive_sync_status() -> Dict[str, Any]:
    """Returns connectivity and ledger statistics for Google Drive integration."""
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()
    records = get_google_drive_sync_records()
    synced_count = sum(1 for r in records if r.get("sync_status") == "SYNCED_GOOGLE_DRIVE")
    pending_count = len(records) - synced_count
    
    return {
        "webhook_configured": bool(webhook_url),
        "webhook_url": (webhook_url[:25] + "..." + webhook_url[-10:]) if len(webhook_url) > 35 else webhook_url,
        "total_emails_captured": len(records),
        "synced_to_drive": synced_count,
        "pending_sync": pending_count,
        "ledger_file": str(GOOGLE_DRIVE_CSV_FILE)
    }

def retry_pending_syncs() -> int:
    """Attempts to sync any previously pending emails if a webhook URL has been configured."""
    webhook_url = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return 0
    records = get_google_drive_sync_records()
    re_synced = 0
    updated_records = []
    for r in records:
        if r.get("sync_status") != "SYNCED_GOOGLE_DRIVE":
            try:
                payload = {
                    "timestamp": r.get("timestamp", datetime.now().isoformat()),
                    "learner_id": r.get("learner_id", ""),
                    "name": r.get("name", ""),
                    "email": r.get("email", ""),
                    "role": r.get("role", "")
                }
                resp = requests.post(webhook_url, json=payload, timeout=8)
                if resp.status_code in (200, 201):
                    r["sync_status"] = "SYNCED_GOOGLE_DRIVE"
                    r["error_message"] = "Retried and synced successfully."
                    re_synced += 1
            except Exception as e:
                r["error_message"] = f"Retry error: {str(e)}"
        updated_records.append(r)
        
    # Rewrite ledger
    init_google_drive_csv()
    with open(GOOGLE_DRIVE_CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "learner_id", "name", "email", "role", "sync_status", "error_message"])
        for u in updated_records:
            writer.writerow([
                u.get("timestamp"), u.get("learner_id"), u.get("name"),
                u.get("email"), u.get("role"), u.get("sync_status"), u.get("error_message")
            ])
    return re_synced
