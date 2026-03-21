"""Auth0 integration for MoneySpeaks.

Real mode: validates JWT tokens from Auth0.
Mock mode: bypasses auth, returns a local mock user profile.
"""

import json
import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("moneyspeaks.auth")

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "")
AUTH0_AUDIENCE = f"https://{AUTH0_DOMAIN}/api/v2/" if AUTH0_DOMAIN else ""

MOCK_MODE = not (AUTH0_DOMAIN and AUTH0_CLIENT_ID)

if MOCK_MODE:
    logger.warning("No AUTH0_DOMAIN/AUTH0_CLIENT_ID — running auth in MOCK mode")
else:
    logger.info(f"Auth0 configured: domain={AUTH0_DOMAIN}")

security = HTTPBearer(auto_error=False)

# --- In-memory user store (mock mode) ---
MOCK_USER = {
    "sub": "mock|12345",
    "email": "user@moneyspeaks.demo",
    "name": "Demo User",
    "picture": "",
    "bank_number": "",
    "trusted_contacts": [],
}

# Simple in-memory profile store keyed by user sub
_user_profiles: dict[str, dict] = {}


def _get_mock_user() -> dict:
    if MOCK_USER["sub"] not in _user_profiles:
        _user_profiles[MOCK_USER["sub"]] = {**MOCK_USER}
    return _user_profiles[MOCK_USER["sub"]]


async def _verify_token(token: str) -> dict:
    """Verify Auth0 JWT and return decoded payload."""
    try:
        import httpx
        from authlib.jose import jwt as jose_jwt
        from authlib.jose import JsonWebKey
    except ImportError:
        logger.error("authlib/httpx not installed — falling back to mock")
        return _get_mock_user()

    # Fetch JWKS
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        jwks = resp.json()

    try:
        claims = jose_jwt.decode(
            token,
            JsonWebKey.import_key_set(jwks),
        )
        claims.validate()
        return {
            "sub": claims["sub"],
            "email": claims.get("email", ""),
            "name": claims.get("name", ""),
            "picture": claims.get("picture", ""),
        }
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency that returns the current authenticated user.

    Mock mode: always returns demo user (no token required).
    Real mode: validates Bearer token against Auth0.
    """
    if MOCK_MODE:
        return _get_mock_user()

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return await _verify_token(credentials.credentials)


def get_user_profile(sub: str) -> dict:
    """Get or create a user profile."""
    if sub not in _user_profiles:
        _user_profiles[sub] = {
            "sub": sub,
            "bank_number": "",
            "trusted_contacts": [],
        }
    return _user_profiles[sub]


def update_user_profile(sub: str, updates: dict) -> dict:
    """Update user profile fields."""
    profile = get_user_profile(sub)
    allowed = {"bank_number", "trusted_contacts", "name", "email"}
    for key, value in updates.items():
        if key in allowed:
            profile[key] = value
    return profile
