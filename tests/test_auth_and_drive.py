import pytest
from core.auth import encrypt_password, decrypt_password, verify_password, validate_email
from core.db import create_learner, get_learner, get_learner_by_email, delete_learner
from core.email_service import send_password_recovery_email, DISPATCH_LOG_FILE
from core.google_drive_sync import sync_email_to_google_sheet, get_google_drive_sync_records, get_google_drive_sync_status

def test_password_encryption_and_decryption():
    raw_pass = "ExecutiveLeader2026!"
    token = encrypt_password(raw_pass)
    assert token != raw_pass
    assert len(token) > 20
    
    decrypted = decrypt_password(token)
    assert decrypted == raw_pass
    assert verify_password(raw_pass, token) is True
    assert verify_password("WrongPassword", token) is False

def test_email_validation():
    assert validate_email("alex.chen@company.com") is True
    assert validate_email("priya+lead@sub.domain.co.uk") is True
    assert validate_email("invalid-email") is False
    assert validate_email("@no-user.com") is False
    assert validate_email("no-domain@") is False
    assert validate_email("") is False

def test_get_learner_by_email():
    learner = get_learner_by_email("priya.sharma@omniretail.com")
    assert learner is not None
    assert learner["id"] == "priya_sharma"
    
    # Case insensitivity test
    learner_caps = get_learner_by_email("PRIYA.SHARMA@OMNIRETAIL.COM")
    assert learner_caps is not None
    assert learner_caps["id"] == "priya_sharma"

def test_email_recovery_dispatch():
    success, msg = send_password_recovery_email(
        to_email="test.recover@domain.com",
        learner_name="Test Recovery User",
        password="TempPassword789"
    )
    assert success is True
    assert "test.recover@domain.com" in msg
    assert DISPATCH_LOG_FILE.exists()

def test_google_drive_sync_ledger():
    synced, msg = sync_email_to_google_sheet(
        learner_id="test_drive_user",
        name="Test Drive User",
        email="drive.test@domain.com",
        role="Head of Analytics"
    )
    # Even if webhook URL is not set, it successfully records to local ledger
    assert "drive.test@domain.com" in msg or "local ledger" in msg
    
    records = get_google_drive_sync_records()
    assert any(r["email"] == "drive.test@domain.com" for r in records)
    
    status = get_google_drive_sync_status()
    assert status["total_emails_captured"] >= 1

def test_registration_flow_with_email_and_password():
    lid = "test_auth_full_user"
    email = "full.auth@leadership.io"
    password = "MyStrongPassword@99"
    encrypted = encrypt_password(password)
    
    created = create_learner(
        learner_id=lid,
        name="Full Auth User",
        track_id="data_ai_leadership",
        current_role="MIS Lead",
        years_of_experience=6,
        target_level="AI Lead",
        industry="Technology",
        tools_known=["Excel", "Python"],
        hours_per_week=10,
        start_date="2026-11-01",
        email=email,
        password_hash=encrypted
    )
    
    assert created is not None
    assert created["email"] == email
    assert verify_password(password, created["password_hash"]) is True
    
    by_email = get_learner_by_email(email)
    assert by_email is not None
    assert by_email["id"] == lid
    
    # Cleanup
    delete_learner(lid)
    assert get_learner(lid) is None
    assert get_learner_by_email(email) is None
