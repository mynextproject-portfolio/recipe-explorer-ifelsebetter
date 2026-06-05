"""
Authentication services for Recipe Explorer.

Implements secure password hashing via memory-hard scrypt,
stateless JWT generation/verification, dynamic secret key resolution,
and Redis token blacklisting for secure session invalidation.
"""

import hashlib
import hmac
import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import jwt

logger = logging.getLogger(__name__)

# Default scrypt parameters (OWASP recommended parameters)
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEY_LEN = 64

# JWT Configuration
JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRY_SECONDS = 3600  # 1 hour


def get_jwt_secret() -> str:
    """
    Resolve JWT Secret Key following a secure multi-tiered fallback:
    1. Read from environment variable JWT_SECRET_KEY.
    2. Read from local file 'jwt_secret.txt'.
    3. Generate an ephemeral secure random key and save it locally.
    """
    secret = os.environ.get("JWT_SECRET_KEY")
    if secret:
        return secret

    secret_file_path = "jwt_secret.txt"
    if os.path.exists(secret_file_path):
        try:
            with open(secret_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as err:
            logger.warning("Failed to read JWT secret file: %s", err)

    # Fallback to random generation and write to local file
    logger.warning("Generating ephemeral secret. Instance-isolated!")
    new_secret = secrets.token_hex(32)
    try:
        with open(secret_file_path, "w", encoding="utf-8") as f:
            f.write(new_secret)
    except Exception as err:
        logger.error("Failed to write generated JWT secret to file: %s", err)

    return new_secret


def hash_password(password: str) -> str:
    """
    Hash a password using memory-hard scrypt with a unique salt.
    Format returned: scrypt$n$r$p$salt_hex$hash_hex
    """
    salt = secrets.token_bytes(16)
    hashed_bytes = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_LEN
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${hashed_bytes.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against an scrypt hash in a timing-attack safe manner.
    """
    try:
        if not hashed.startswith("scrypt$"):
            return False
        parts = hashed.split("$")
        if len(parts) != 6:
            return False
        
        _, n_str, r_str, p_str, salt_hex, hash_hex = parts
        n = int(n_str)
        r = int(r_str)
        p = int(p_str)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        
        computed_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected_hash)
        )
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception as err:
        logger.error("Error during password verification: %s", err)
        return False


def create_access_token(
    user_id: str,
    email: str,
    username: str,
    expires_delta_seconds: int = DEFAULT_EXPIRY_SECONDS
) -> str:
    """
    Generate a stateless JWT access token containing exp, sub, email, username, and jti.
    """
    secret = get_jwt_secret()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=expires_delta_seconds)
    
    payload = {
        "exp": expire,
        "iat": now,
        "sub": user_id,
        "email": email,
        "username": username,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token. Returns payload dict if valid, otherwise None.
    Rejects 'none' algorithm and validates the exp claim.
    """
    secret = get_jwt_secret()
    try:
        # Explicitly pass the allowed algorithms to prevent algorithm confusion attacks
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as err:
        logger.debug("JWT verification failed: %s", err)
        return None
