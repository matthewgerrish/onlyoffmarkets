"""Email delivery — Resend wrapper with log fallback.

Resend was chosen over Mailgun/SendGrid because:
  - simplest auth (one POST + Bearer token)
  - 3,000 free emails / month, 100/day — covers MVP magic links
  - no SMTP plumbing

Set RESEND_API_KEY to send for real. Without it, magic-link emails are
written to logs instead so dev can copy-paste the link from the API
log to verify the flow without burning quota.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

log = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_URL = "https://api.resend.com/emails"
RESEND_FROM = os.environ.get("RESEND_FROM", "OnlyOffMarkets <noreply@onlyoffmarkets.com>")
HTTP_TIMEOUT = 10.0


def is_live() -> bool:
    return bool(RESEND_API_KEY)


def send(to: str, subject: str, html: str, *, text: str | None = None) -> dict[str, Any]:
    """Send a transactional email. Returns provider response or {mock: True}."""
    if not RESEND_API_KEY:
        log.info(
            "EMAIL[mock] to=%s subject=%r html=%s",
            to, subject, html[:300].replace("\n", " "),
        )
        return {"mock": True}
    body = {
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        body["text"] = text
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as cx:
            r = cx.post(
                RESEND_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if r.status_code >= 400:
                log.warning("Resend %d: %s", r.status_code, r.text[:300])
            r.raise_for_status()
            return r.json()
    except Exception as exc:  # pragma: no cover
        log.exception("Resend send failed: %s", exc)
        return {"error": str(exc)}


def send_magic_link(to: str, link: str) -> dict[str, Any]:
    subject = "Sign in to OnlyOffMarkets"
    html = f"""<!doctype html>
<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background:#f8fafc; padding:40px 20px; color:#0f1f3d">
  <div style="max-width:480px;margin:0 auto;background:#fff;border:1px solid #e2e8f0;
    border-radius:16px;padding:32px">
    <div style="font-weight:800;font-size:22px;letter-spacing:-0.02em">onlyoffmarkets</div>
    <h2 style="margin-top:24px;font-size:18px;font-weight:700">Sign in</h2>
    <p style="color:#475569;line-height:1.5">
      Click the button below to sign in. The link expires in 15 minutes.
    </p>
    <p style="margin:24px 0">
      <a href="{link}"
         style="display:inline-block;background:#1d6cf2;color:#fff;text-decoration:none;
                font-weight:600;padding:12px 22px;border-radius:999px">Sign in</a>
    </p>
    <p style="color:#94a3b8;font-size:12px;line-height:1.5">
      Didn't ask for this? Ignore this email — no account changes will be made.
    </p>
  </div>
  <p style="text-align:center;color:#94a3b8;font-size:11px;margin-top:24px">
    OnlyOffMarkets · onlyoffmarkets.com
  </p>
</body></html>"""
    text = f"Sign in to OnlyOffMarkets:\n\n{link}\n\nLink expires in 15 minutes."
    return send(to, subject, html, text=text)
