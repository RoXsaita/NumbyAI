"""Local authentication utilities."""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Tuple


def _hash_with_salt(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)


def hash_password(password: str) -> str:
    """Return a salted password hash in the form salt$hash (hex)."""
    salt = os.urandom(16)
    hashed = _hash_with_salt(password, salt)
    return f"{salt.hex()}${hashed.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash string."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt_hex, hash_hex = stored_hash.split("$", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    candidate = _hash_with_salt(password, salt)
    return hmac.compare_digest(candidate, expected)
