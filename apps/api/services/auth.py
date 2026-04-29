"""Auth: magic-link sign-in + JWT issuance.

Two token types:
  - magic-link  short-lived (15 min), single-use, embeds email
                only. Verified server-side, traded in for a session.
  - session     long-lived (30 days), embeds user_id. Sent on every
                authenticated API call as `Authorization: Bearer ...`.

Symmetric HS256 signing — JWT_SECRET env var is the source of truth.
Loud failure if it isn't set in production (we'd be auto-signing
predictable tokens).
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt  # type: ignore[import-untyped]

log = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET") or os.environ.get("AUTH_JWT_SECRET") or ""
JWT_ALG = "HS256"

MAGIC_LINK_TTL = timedelta(minutes=15)
SESSION_TTL = timedelta(days=30)


def _ensure_secret() -> str:
    """Resolve the signing secret; refuse predictable fallbacks in prod."""
    if JWT_SECRET and len(JWT_SECRET) >= 16:
        return JWT_SECRET
    if os.environ.get("STRIPE_SECRET_KEY"):
        # Production-shaped env without a JWT secret = security hole.
        raise RuntimeError(
            "JWT_SECRET unset (or too short). Set with: "
            "fly secrets set JWT_SECRET=$(openssl rand -hex 32)"
        )
    # Dev fallback — randomized per-process so old tokens get invalidated
    # whenever the API restarts.
    log.warning("JWT_SECRET unset — generating ephemeral dev secret")
    return _DEV_SECRET


_DEV_SECRET = secrets.token_hex(32)


def issue_magic_link_token(email: str) -> str:
    secret = _ensure_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "type": "magic",
        "email": email.strip().lower(),
        "iat": int(now.timestamp()),
        "exp": int((now + MAGIC_LINK_TTL).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALG)


def verify_magic_link_token(token: str) -> str:
    """Returns the verified email, or raises."""
    secret = _ensure_secret()
    payload = jwt.decode(token, secret, algorithms=[JWT_ALG])
    if payload.get("type") != "magic":
        raise jwt.InvalidTokenError("not a magic-link token")
    email = payload.get("email")
    if not email or "@" not in email:
        raise jwt.InvalidTokenError("missing email")
    return email


def issue_session_token(user_id: str, email: str | None = None) -> str:
    secret = _ensure_secret()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "type": "session",
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + SESSION_TTL).timestamp()),
    }
    if email:
        payload["email"] = email.strip().lower()
    return jwt.encode(payload, secret, algorithm=JWT_ALG)


def verify_session_token(token: str) -> dict:
    """Returns the decoded payload, or raises."""
    secret = _ensure_secret()
    payload = jwt.decode(token, secret, algorithms=[JWT_ALG])
    if payload.get("type") != "session":
        raise jwt.InvalidTokenError("not a session token")
    if not payload.get("sub"):
        raise jwt.InvalidTokenError("missing sub")
    return payload


def parse_authorization(header_value: str | None) -> str | None:
    """Extract bearer token from `Authorization: Bearer <token>`."""
    if not header_value:
        return None
    parts = header_value.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None
