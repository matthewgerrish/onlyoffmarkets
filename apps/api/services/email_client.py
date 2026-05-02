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


_BRAND_PRIMARY = "#1d6cf2"
_BRAND_PRIMARY_DARK = "#0a6bd6"
_BRAND_NAVY = "#0f1f3d"
_BRAND_50 = "#e8f1ff"
_LOGO_URL = "https://onlyoffmarkets.com/logo.png"
_PUBLIC_WEB_URL = "https://onlyoffmarkets.com"
# Poppins is loaded via @import for clients that allow it (Apple Mail, iOS Mail,
# most webmails). Outlook/Gmail strip <style>, but every place we ship a font
# also lists web-safe fallbacks inline. Net result: Poppins in modern clients,
# clean sans-serif everywhere else — never an ugly serif.
_FONT_STACK = (
    "'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Helvetica, Arial, sans-serif"
)


def send_magic_link(to: str, link: str) -> dict[str, Any]:
    subject = "Your OnlyOffMarkets sign-in link"

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in to OnlyOffMarkets</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
  /* Bulletproof button hover for clients that allow it. */
  .oom-btn:hover {{ background: {_BRAND_PRIMARY_DARK} !important; }}
  /* Dark-mode hint — most clients honor color-scheme without rewriting palette. */
  :root {{ color-scheme: light; supported-color-schemes: light; }}
</style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:{_FONT_STACK};
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
  color:{_BRAND_NAVY};">

<!-- Preheader (preview text in inbox list) -->
<div style="display:none;overflow:hidden;line-height:1px;opacity:0;max-height:0;max-width:0;">
  Tap the button to sign in. Link expires in 15 minutes 🔐
</div>

<!-- Outer table for Outlook compat -->
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"
  style="background:#f1f5f9;padding:32px 16px;">
<tr><td align="center">

  <!-- Card -->
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="520"
    style="max-width:520px;background:#ffffff;border:1px solid #e2e8f0;
    border-radius:20px;overflow:hidden;box-shadow:0 8px 24px -8px rgba(29,108,242,0.12);">

    <!-- Brand header strip with gradient -->
    <tr><td style="background:linear-gradient(135deg,{_BRAND_NAVY} 0%,{_BRAND_PRIMARY} 100%);
      padding:28px 32px 22px 32px;color:#ffffff;">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
          <td style="vertical-align:middle;">
            <img src="{_LOGO_URL}" alt="OnlyOffMarkets"
              width="56" height="56"
              style="display:block;border:0;outline:none;width:56px;height:56px;
              border-radius:12px;background:#ffffff;padding:6px;
              box-shadow:0 4px 14px rgba(0,0,0,0.18);">
          </td>
          <td style="vertical-align:middle;padding-left:14px;">
            <div style="font-family:{_FONT_STACK};font-weight:800;font-size:24px;
              letter-spacing:-0.02em;line-height:1;color:#ffffff;">
              OnlyOffMarkets<span style="color:{_BRAND_50};font-weight:600;">.com</span>
            </div>
            <div style="font-family:{_FONT_STACK};font-size:11px;font-weight:600;
              letter-spacing:0.16em;text-transform:uppercase;opacity:0.85;
              margin-top:6px;color:#ffffff;">
              Every off-market lead · in one feed
            </div>
          </td>
        </tr>
      </table>
    </td></tr>

    <!-- Body -->
    <tr><td style="padding:36px 36px 16px 36px;">
      <div style="display:inline-block;background:{_BRAND_50};color:{_BRAND_PRIMARY};
        font-family:{_FONT_STACK};font-size:11px;font-weight:700;letter-spacing:0.12em;
        text-transform:uppercase;padding:5px 12px;border-radius:999px;">
        🔐 Magic link
      </div>
      <h1 style="font-family:{_FONT_STACK};font-weight:800;color:{_BRAND_NAVY};
        font-size:30px;line-height:1.15;margin:18px 0 8px 0;letter-spacing:-0.02em;">
        One click and<br>you're in.
      </h1>
      <p style="font-family:{_FONT_STACK};color:#475569;line-height:1.55;
        font-size:15px;margin:0 0 28px 0;">
        Tap the button below to sign in. No password to remember — your wallet,
        membership, and saved properties move with your email.
      </p>

      <!-- Big polished CTA button -->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr><td align="center"
          style="background:{_BRAND_PRIMARY};border-radius:999px;
          box-shadow:0 8px 24px -8px rgba(29,108,242,0.45);">
          <a class="oom-btn" href="{link}"
             style="display:inline-block;font-family:{_FONT_STACK};
             font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;
             padding:14px 32px;letter-spacing:0.01em;">
            Sign in to OnlyOffMarkets &nbsp;→
          </a>
        </td></tr>
      </table>

      <p style="font-family:{_FONT_STACK};color:#94a3b8;font-size:12px;
        margin:22px 0 0 0;line-height:1.5;">
        Or paste this link into your browser:<br>
        <a href="{link}" style="color:{_BRAND_PRIMARY};word-break:break-all;
          text-decoration:none;font-family:'SFMono-Regular',Menlo,Consolas,monospace;
          font-size:11px;">{link}</a>
      </p>
    </td></tr>

    <!-- Soft divider w/ stat-strip flavor -->
    <tr><td style="padding:24px 36px 28px 36px;border-top:1px solid #f1f5f9;">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
          <td align="center" style="font-family:{_FONT_STACK};">
            <div style="font-size:20px;font-weight:800;color:{_BRAND_NAVY};
              line-height:1;">7.6k<span style="color:{_BRAND_PRIMARY};">+</span></div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;
              letter-spacing:0.1em;margin-top:4px;font-weight:600;">Active signals</div>
          </td>
          <td align="center" style="font-family:{_FONT_STACK};">
            <div style="font-size:20px;font-weight:800;color:{_BRAND_NAVY};
              line-height:1;">25</div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;
              letter-spacing:0.1em;margin-top:4px;font-weight:600;">States covered</div>
          </td>
          <td align="center" style="font-family:{_FONT_STACK};">
            <div style="font-size:20px;font-weight:800;color:{_BRAND_NAVY};
              line-height:1;">19</div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;
              letter-spacing:0.1em;margin-top:4px;font-weight:600;">Source feeds</div>
          </td>
          <td align="center" style="font-family:{_FONT_STACK};">
            <div style="font-size:20px;font-weight:800;color:{_BRAND_NAVY};
              line-height:1;">&lt;24h</div>
            <div style="font-size:10px;color:#94a3b8;text-transform:uppercase;
              letter-spacing:0.1em;margin-top:4px;font-weight:600;">Avg lead age</div>
          </td>
        </tr>
      </table>
    </td></tr>

    <!-- Fine print -->
    <tr><td style="padding:18px 36px 26px 36px;background:#f8fafc;
      border-top:1px solid #f1f5f9;font-family:{_FONT_STACK};">
      <p style="color:#94a3b8;font-size:11px;line-height:1.55;margin:0;">
        ⏱ This link expires in <strong style="color:#475569;">15 minutes</strong>.
        Didn't request it? Ignore — no account changes were made.
      </p>
    </td></tr>

  </table>

  <!-- Footer -->
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="520"
    style="max-width:520px;margin-top:18px;font-family:{_FONT_STACK};">
    <tr><td align="center" style="font-size:11px;color:#94a3b8;line-height:1.6;">
      <a href="{_PUBLIC_WEB_URL}" style="color:#94a3b8;text-decoration:none;
        font-weight:600;">OnlyOffMarkets.com</a>
      &nbsp;·&nbsp;
      <a href="{_PUBLIC_WEB_URL}/sources" style="color:#94a3b8;text-decoration:none;">Data sources</a>
      &nbsp;·&nbsp;
      <a href="{_PUBLIC_WEB_URL}/about" style="color:#94a3b8;text-decoration:none;">Compliance</a>
      <div style="margin-top:8px;">
        Signals, not listings. Public-record data only.
      </div>
    </td></tr>
  </table>

</td></tr>
</table>

</body></html>"""

    text = (
        "OnlyOffMarkets — Sign-in link\n"
        "==============================\n\n"
        "One click and you're in. Tap to sign in:\n\n"
        f"  {link}\n\n"
        "This link expires in 15 minutes.\n"
        "Didn't request it? Ignore this email — no account changes were made.\n\n"
        "—\n"
        f"OnlyOffMarkets.com · 7.6k+ active signals · 25 states\n"
    )
    return send(to, subject, html, text=text)
