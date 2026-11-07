import base64
import hashlib
import os
import re
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from config.settings import ADMIN_PASSWORD

def get_fernet_cipher() -> Fernet:
    """Returns a Fernet cipher instance using SECRET_ENCRYPTION_KEY or a derived fallback."""
    env_key = os.getenv("SECRET_ENCRYPTION_KEY", "").strip()
    if env_key and len(env_key) == 44:
        try:
            return Fernet(env_key.encode())
        except Exception:
            pass
    # Deterministically derive 32-byte urlsafe-base64 key from ADMIN_PASSWORD
    derived_key = base64.urlsafe_b64encode(hashlib.sha256(f"aileader_{ADMIN_PASSWORD}".encode()).digest())
    return Fernet(derived_key)

def encrypt_password(plain_text: str) -> str:
    """Encrypts a plaintext password using Fernet symmetric encryption."""
    if not plain_text:
        return ""
    cipher = get_fernet_cipher()
    return cipher.encrypt(plain_text.strip().encode("utf-8")).decode("utf-8")

def decrypt_password(token: str) -> str:
    """Decrypts a Fernet token back into the original plaintext password."""
    if not token:
        return ""
    cipher = get_fernet_cipher()
    try:
        return cipher.decrypt(token.strip().encode("utf-8")).decode("utf-8")
    except Exception:
        # Graceful return if plaintext legacy string
        return token

def verify_password(plain_text: str, stored_token: str) -> bool:
    """Verifies whether the provided plaintext password matches the stored token."""
    if not stored_token:
        # Default fallback for demo/legacy profiles
        return plain_text.strip() == "leader_2025"
    decrypted = decrypt_password(stored_token)
    return plain_text.strip() == decrypted.strip()

def validate_email(email: str) -> bool:
    """Validates standard email address syntax."""
    if not email or not isinstance(email, str):
        return False
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(email_regex, email.strip()))
