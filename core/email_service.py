import os
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Tuple
from config.settings import PROJECT_ROOT

DISPATCH_LOG_FILE = PROJECT_ROOT / "db" / "email_dispatch_log.json"

def send_password_recovery_email(to_email: str, learner_name: str, password: str) -> Tuple[bool, str]:
    """
    Sends a password recovery email to the learner.
    If SMTP credentials are configured in .env, connects via SMTP/TLS.
    If SMTP credentials are not yet configured or if network fails, logs to db/email_dispatch_log.json
    and returns a simulated success response with clear instructions.
    """
    to_email = to_email.strip()
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    # Strip spaces in case 16-character app password contains spaces (e.g. Gmail)
    smtp_pass = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "noreply@aileaderlearn.com").strip()
    
    subject = "🔐 AI Leader Learn: Your Account Password Recovery"
    body = f"""Dear {learner_name},

You requested your account password for AI Leader Learn.

Account Credentials:
• Registered Email: {to_email}
• Password: {password}

Log in to continue your 90-day accelerator:
https://aileaderlearn.streamlit.app

Best regards,
The AI Leader Learn Executive Team
"""
    
    # 1. Attempt real SMTP dispatch if configured
    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email
            msg.set_content(body)
            
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                    
            record_email_dispatch(to_email, learner_name, "DELIVERED_SMTP")
            return True, f"Password recovery email sent successfully to {to_email} via SMTP ({smtp_host})."
        except Exception as e:
            record_email_dispatch(to_email, learner_name, f"SMTP_ERROR: {str(e)}")
            return True, f"SMTP delivery failed ({str(e)}). Fallback simulated dispatch logged."

    # 2. Local / Development simulation mode
    record_email_dispatch(to_email, learner_name, "SIMULATED_LOCAL")
    return True, f"SIMULATED: Password recovery email prepared for {to_email}."

def record_email_dispatch(to_email: str, learner_name: str, status: str) -> None:
    """Appends an email dispatch event to the local audit log."""
    DISPATCH_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = []
    if DISPATCH_LOG_FILE.exists():
        try:
            with open(DISPATCH_LOG_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []
    records.append({
        "timestamp": datetime.now().isoformat(),
        "to_email": to_email,
        "learner_name": learner_name,
        "status": status
    })
    with open(DISPATCH_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(records[-100:], f, indent=2)
