"""Password hashing and sign-in checks.

Passwords are never stored in plain text: PBKDF2-HMAC-SHA256 with a random
per-user salt.
"""

import hashlib
import hmac
import os

ITERATIONS = 200_000


def hash_password(password, salt=None):
    """Return (hex_hash, hex_salt)."""
    if salt is None:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS
    )
    return dk.hex(), salt


def verify_password(password, stored_hash, salt):
    calc, _ = hash_password(password, salt)
    return hmac.compare_digest(calc, stored_hash)


def authenticate(username, password):
    """Return a user row on success, or None."""
    import database

    if not username.strip() or not password:
        return None
    user = database.get_user_by_username(username)
    if user is None:
        return None
    if verify_password(password, user["password_hash"], user["salt"]):
        return user
    return None
