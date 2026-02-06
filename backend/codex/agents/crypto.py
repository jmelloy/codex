"""Encryption utilities for agent credentials.

Uses Fernet symmetric encryption derived from the application SECRET_KEY.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    """Create a Fernet instance from the app SECRET_KEY."""
    secret = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    # Derive a 32-byte key from SECRET_KEY using SHA-256
    key_bytes = hashlib.sha256(secret.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string, returning a base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext, returning the plaintext string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
