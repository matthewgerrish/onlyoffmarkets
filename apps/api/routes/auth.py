"""Auth routes — magic-link sign-in.

Flow:
  1. POST /auth/magic-link  {email, anon_user_id?}
       → emails a verify link, returns {ok: true}
       (anon_user_id is the visitor's localStorage UUID — recorded
        inside the magic token so we can migrate their wallet on verify.)
  2. GET  /auth/verify?token=...
       → verifies the magic token, finds-or-creates the user, migrates
         the anon wallet, issues a session JWT. Redirects to the
         frontend with the session token in the URL fragment so we
         keep it out of server logs / referers.
  3. GET  /auth/me
       → returns the current user (Authorization: Bearer ...)
  4. POST /auth/logout
       → no-op server-side (JWTs are stateless); frontend drops the
         token from localStorage.
"""
from __future__ import annotations

import logging
import os

import jwt as pyjwt  # type: ignore[import-untyped]
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from services import auth as auth_svc
from services import email_client
from services.rate_limit import limiter
from storage import users_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

PUBLIC_WEB_URL = os.environ.get("PUBLIC_WEB_URL", "https://onlyoffmarkets.com").rstrip("/")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "https://onlyoffmarkets-api.fly.dev").rstrip("/")


class MagicLinkIn(BaseModel):
    email: EmailStr
    anon_user_id: str | None = None  # legacy localStorage UUID


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkIn, request: Request) -> dict:
    email = str(body.email).strip().lower()
    # Rate-limit per email AND per IP — blocks email-spamming and a
    # single attacker churning emails to flood our inbox.
    ip = request.client.host if request.client else "_anon"
    limiter.check("magic_link_email", email, max=5, per_seconds=300)
    limiter.check("magic_link_ip", f"ip:{ip}", max=20, per_seconds=300)

    # Embed the optional anon_user_id inside the token so verify can
    # migrate without trusting an incoming query param. Pack via a
    # second JWT payload field (custom 'anon').
    anon = (body.anon_user_id or "").strip()[:64] or None

    token = auth_svc.issue_magic_link_token(email)
    # If anon present, re-issue with the extra claim. Slightly redundant
    # but keeps the issue helper API tight.
    if anon:
        secret = auth_svc._ensure_secret()
        from datetime import datetime, timezone
        from secrets import token_urlsafe
        now = datetime.now(timezone.utc)
        token = pyjwt.encode(
            {
                "type": "magic",
                "email": email,
                "anon": anon,
                "iat": int(now.timestamp()),
                "exp": int((now + auth_svc.MAGIC_LINK_TTL).timestamp()),
                "jti": token_urlsafe(16),
            },
            secret,
            algorithm=auth_svc.JWT_ALG,
        )

    link = f"{PUBLIC_API_URL}/auth/verify?token={token}"
    res = email_client.send_magic_link(email, link)

    out: dict = {"ok": True, "email": email, "live_email": email_client.is_live()}
    if not email_client.is_live():
        # Surface the link in the response so dev can copy-paste it
        # without rooting around in fly logs. NEVER do this in prod —
        # gated by RESEND_API_KEY presence.
        out["dev_link"] = link
    if isinstance(res, dict) and res.get("error"):
        out["delivery_error"] = res["error"]
    return out


@router.get("/verify")
async def verify_magic_link(token: str = Query(...)):
    """Trade a magic-link token for a session JWT. Redirects to the web app."""
    try:
        secret = auth_svc._ensure_secret()
        payload = pyjwt.decode(token, secret, algorithms=[auth_svc.JWT_ALG])
    except pyjwt.ExpiredSignatureError:
        return RedirectResponse(f"{PUBLIC_WEB_URL}/?auth=expired", status_code=302)
    except Exception as exc:
        log.warning("magic-link verify failed: %s", exc)
        return RedirectResponse(f"{PUBLIC_WEB_URL}/?auth=invalid", status_code=302)

    if payload.get("type") != "magic":
        return RedirectResponse(f"{PUBLIC_WEB_URL}/?auth=invalid", status_code=302)
    email = (payload.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return RedirectResponse(f"{PUBLIC_WEB_URL}/?auth=invalid", status_code=302)
    anon_user_id = (payload.get("anon") or "").strip()[:64] or None

    user = users_db.upsert_by_email(email)
    new_user_id = user["id"]

    # Migrate anonymous-UUID wallet/plan into the email-keyed user.
    migrated = 0
    if anon_user_id and anon_user_id != new_user_id:
        try:
            migrated = users_db.migrate_user_id(anon_user_id, new_user_id)
        except Exception as exc:
            log.warning("migration anon=%s → %s failed: %s", anon_user_id, new_user_id, exc)

    session = auth_svc.issue_session_token(new_user_id, email=email)

    # Pass the token in the URL fragment so it never hits server logs /
    # referers. Frontend reads location.hash, stores in localStorage,
    # then strips the hash.
    redirect = (
        f"{PUBLIC_WEB_URL}/?auth=success#"
        f"token={session}&user_id={new_user_id}&migrated={migrated}"
    )
    return RedirectResponse(redirect, status_code=302)


def _resolve_user(authorization: str | None) -> dict:
    token = auth_svc.parse_authorization(authorization)
    if not token:
        raise HTTPException(401, "Authorization header required")
    try:
        payload = auth_svc.verify_session_token(token)
    except Exception as exc:
        log.info("session verify failed: %s", exc)
        raise HTTPException(401, "Invalid or expired session")
    return payload


@router.get("/me")
async def me(authorization: str | None = Header(default=None)) -> dict:
    payload = _resolve_user(authorization)
    user_id = payload["sub"]
    row = users_db.get_by_id(user_id) or {"id": user_id, "email": payload.get("email")}
    return {"user_id": row["id"], "email": row.get("email"), "session_exp": payload.get("exp")}


@router.post("/logout")
async def logout() -> dict:
    # JWTs are stateless — server-side logout is a no-op. Frontend
    # drops the token from localStorage on its own.
    return {"ok": True}


class ClaimAnonIn(BaseModel):
    anon_user_id: str


@router.post("/claim-anon")
async def claim_anon(
    body: ClaimAnonIn,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict:
    """Re-run the anon → email migration after sign-in.

    Use case: a previous sign-in attempt's migration failed (eg. a
    poisoned-transaction bug, or the user signed in from a fresh
    browser and we want to claim their old anon device's wallet).

    Auth required. The authed user_id becomes the migration target.
    """
    payload = _resolve_user(authorization)
    target_user_id = payload["sub"]
    anon = (body.anon_user_id or "").strip()[:64]
    if not anon or anon == target_user_id:
        raise HTTPException(400, "anon_user_id required and must differ from current user")
    n = users_db.migrate_user_id(anon, target_user_id)
    return {"ok": True, "migrated_rows": n, "from": anon, "to": target_user_id}
