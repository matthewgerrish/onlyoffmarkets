"""Identity resolver — bridges the legacy X-User-Id header and JWT auth.

Every authenticated route calls `resolve_user_id(authorization, x_user_id)`.
- If `Authorization: Bearer <jwt>` is present and valid → that user_id wins.
- Else if `X-User-Id` is present → treated as a legacy anonymous user
  (still trust-on-first-use; fine until everyone has signed in).
- Else → 401.

Once real auth is universal we'll flip the legacy header off via env
flag (REQUIRE_AUTH=1) and only JWTs will be accepted.
"""
from __future__ import annotations

import logging
import os

from fastapi import HTTPException

from services import auth as auth_svc
from storage import users_db

log = logging.getLogger(__name__)


def _strict() -> bool:
    return os.environ.get("REQUIRE_AUTH", "").strip().lower() in ("1", "true", "yes")


def resolve_user_id(authorization: str | None, x_user_id: str | None, *, allow_anon: bool = True) -> str:
    token = auth_svc.parse_authorization(authorization)
    if token:
        try:
            payload = auth_svc.verify_session_token(token)
            user_id = str(payload["sub"])
            users_db.ensure_anon(user_id)  # idempotent; backstops old data
            return user_id
        except Exception as exc:
            log.info("Bearer token rejected: %s", exc)
            raise HTTPException(401, "Invalid or expired session")

    if not allow_anon or _strict():
        raise HTTPException(401, "Authorization required")

    if not x_user_id or len(x_user_id.strip()) < 6:
        raise HTTPException(400, "X-User-Id header (or Bearer token) required")

    user_id = x_user_id.strip()[:64]
    users_db.ensure_anon(user_id)
    return user_id


def optional_user_id(authorization: str | None, x_user_id: str | None) -> str | None:
    """Return a user_id if any identity hint is present, else None.

    Used by read endpoints that don't require auth but want to apply
    per-user plan gating when possible (e.g. nationwide search).
    """
    try:
        return resolve_user_id(authorization, x_user_id, allow_anon=True)
    except HTTPException:
        return None
