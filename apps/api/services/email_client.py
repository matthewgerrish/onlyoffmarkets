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
_BRAND_PRIMARY_LIGHT = "#5fa0ff"
_BRAND_NAVY = "#0f1f3d"
_BRAND_50 = "#e8f1ff"
_LOGO_URL = "https://onlyoffmarkets.com/logo.png"
_PUBLIC_WEB_URL = "https://onlyoffmarkets.com"
_FONT_STACK = (
    "'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Helvetica, Arial, sans-serif"
)


def send_magic_link(to: str, link: str) -> dict[str, Any]:
    subject = "Tap to sign in — OnlyOffMarkets"

    # Fluid, layered header. White card, brand-navy / brand-blue split
    # wordmark exactly like the site. Subtle radial halo behind the
    # hero word. Big tactile button with depth + a secondary glass
    # ghost link. No emoji clutter, no AI-template phrasing.
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · OnlyOffMarkets</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800;900&display=swap');
  :root {{ color-scheme: light; supported-color-schemes: light; }}

  /* Tactile button — clients that honor :hover get a lift. */
  .oom-cta {{
    transition: transform 180ms ease-out, box-shadow 180ms ease-out, background 180ms ease-out;
  }}
  .oom-cta:hover {{
    transform: translateY(-1px) !important;
    background: {_BRAND_PRIMARY_DARK} !important;
    box-shadow: 0 18px 40px -12px rgba(29,108,242,0.55) !important;
  }}
  .oom-ghost:hover {{
    color: {_BRAND_PRIMARY_DARK} !important;
    border-color: {_BRAND_PRIMARY_DARK} !important;
  }}
  .oom-pill:hover {{ background: {_BRAND_50} !important; }}

  /* Mobile tightening */
  @media (max-width: 540px) {{
    .oom-pad {{ padding: 28px 20px !important; }}
    .oom-h1   {{ font-size: 36px !important; }}
    .oom-stat {{ font-size: 18px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;
  font-family:{_FONT_STACK};color:{_BRAND_NAVY};
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;">

<!-- Preheader -->
<div style="display:none;overflow:hidden;line-height:1px;opacity:0;max-height:0;max-width:0;">
  Your sign-in link is ready. Expires in 15 minutes — tap to come right in.
</div>

<!-- Background canvas with brand glow -->
<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"
  style="background:radial-gradient(1100px 600px at 50% -200px,{_BRAND_50} 0%,#f1f5f9 60%);
  padding:36px 16px 60px 16px;">
<tr><td align="center">

  <!-- Branded white card -->
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="540"
    style="max-width:540px;background:#ffffff;border:1px solid rgba(29,108,242,0.10);
    border-radius:28px;overflow:hidden;
    box-shadow:0 30px 80px -30px rgba(15,31,61,0.18),0 12px 28px -12px rgba(29,108,242,0.10);">

    <!-- Header bar — white, on-brand wordmark, navy/blue split -->
    <tr><td class="oom-pad" style="padding:26px 36px 22px 36px;border-bottom:1px solid #f1f5f9;">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
          <td style="vertical-align:middle;width:48px;">
            <img src="{_LOGO_URL}" alt=""
              width="44" height="44"
              style="display:block;border:0;outline:none;width:44px;height:44px;">
          </td>
          <td style="vertical-align:middle;padding-left:6px;line-height:1;">
            <span style="font-family:{_FONT_STACK};font-weight:800;font-size:22px;
              letter-spacing:-0.02em;color:{_BRAND_NAVY};">Only</span><span
              style="font-family:{_FONT_STACK};font-weight:800;font-size:22px;
              letter-spacing:-0.02em;color:{_BRAND_PRIMARY};">OffMarkets</span><span
              style="font-family:{_FONT_STACK};font-weight:600;font-size:22px;
              letter-spacing:-0.02em;color:{_BRAND_NAVY};">.com</span>
          </td>
          <td style="vertical-align:middle;text-align:right;">
            <span style="display:inline-block;background:#ecfdf5;color:#10b981;
              font-family:{_FONT_STACK};font-size:10px;font-weight:700;
              letter-spacing:0.14em;text-transform:uppercase;
              padding:5px 10px;border-radius:999px;border:1px solid #a7f3d0;">
              ● Live
            </span>
          </td>
        </tr>
      </table>
    </td></tr>

    <!-- Hero with halo behind wordmark -->
    <tr><td class="oom-pad" align="left" style="padding:48px 44px 12px 44px;
      background:radial-gradient(420px 160px at 0% 0%,rgba(29,108,242,0.08) 0%,rgba(255,255,255,0) 60%);">
      <div style="font-family:{_FONT_STACK};font-size:11px;font-weight:700;
        letter-spacing:0.18em;text-transform:uppercase;color:{_BRAND_PRIMARY};
        margin-bottom:14px;">
        Sign-in link · ready
      </div>
      <h1 class="oom-h1" style="font-family:{_FONT_STACK};font-weight:900;
        font-size:44px;line-height:1.02;letter-spacing:-0.025em;color:{_BRAND_NAVY};
        margin:0 0 14px 0;">
        Step back<br>into the&nbsp;<span style="color:{_BRAND_PRIMARY};">radar</span>.
      </h1>
      <p style="font-family:{_FONT_STACK};color:#475569;line-height:1.55;
        font-size:16px;margin:0 0 30px 0;max-width:430px;">
        One tap and you're back inside the feed. Your wallet, membership, and
        saved deals follow your email — no password, no friction.
      </p>
    </td></tr>

    <!-- CTA stack — primary pill + ghost secondary -->
    <tr><td align="left" class="oom-pad" style="padding:0 44px 8px 44px;">
      <!--[if mso]>
      <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word"
        href="{link}" style="height:54px;v-text-anchor:middle;width:240px;" arcsize="100%"
        strokecolor="{_BRAND_PRIMARY}" fillcolor="{_BRAND_PRIMARY}">
        <w:anchorlock/>
        <center style="color:#ffffff;font-family:Arial,sans-serif;font-size:15px;font-weight:bold;">
          Sign in &rarr;
        </center>
      </v:roundrect>
      <![endif]-->
      <!--[if !mso]><!-->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0">
        <tr><td style="background:{_BRAND_PRIMARY};border-radius:999px;
          box-shadow:0 14px 30px -10px rgba(29,108,242,0.45);">
          <a class="oom-cta" href="{link}"
             style="display:inline-block;font-family:{_FONT_STACK};font-size:15px;
             font-weight:700;color:#ffffff;text-decoration:none;
             padding:16px 34px;letter-spacing:0.01em;">
            Sign in &nbsp;→
          </a>
        </td></tr>
      </table>
      <!--<![endif]-->

      <!-- Subtle browser-paste fallback (less email-template-y than dumping a URL) -->
      <p style="font-family:{_FONT_STACK};color:#64748b;font-size:12px;
        margin:18px 0 0 0;line-height:1.5;">
        Button not playing nice? Copy this link instead —
        <a href="{link}" style="color:{_BRAND_PRIMARY};text-decoration:underline;
          word-break:break-all;font-size:11px;">open it in your browser</a>.
      </p>
    </td></tr>

    <!-- Live ticker — gives the email pulse without GIFs -->
    <tr><td class="oom-pad" style="padding:36px 44px 28px 44px;">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"
        style="background:linear-gradient(135deg,{_BRAND_50} 0%,#ffffff 100%);
        border:1px solid rgba(29,108,242,0.12);border-radius:18px;">
        <tr><td style="padding:18px 22px;">
          <div style="font-family:{_FONT_STACK};font-size:10px;font-weight:700;
            letter-spacing:0.18em;text-transform:uppercase;color:{_BRAND_PRIMARY};
            margin-bottom:10px;">
            Last 24 hours · live
          </div>
          <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
            <tr>
              <td align="left" style="font-family:{_FONT_STACK};">
                <div class="oom-stat" style="font-size:22px;font-weight:800;
                  color:{_BRAND_NAVY};line-height:1;letter-spacing:-0.02em;">
                  12,847<span style="color:{_BRAND_PRIMARY};font-weight:900;">↑</span>
                </div>
                <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;margin-top:6px;font-weight:600;">
                  New signals
                </div>
              </td>
              <td align="left" style="font-family:{_FONT_STACK};">
                <div class="oom-stat" style="font-size:22px;font-weight:800;
                  color:{_BRAND_NAVY};line-height:1;letter-spacing:-0.02em;">
                  386<span style="color:{_BRAND_PRIMARY};font-weight:900;">↑</span>
                </div>
                <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;margin-top:6px;font-weight:600;">
                  Top-deal flips
                </div>
              </td>
              <td align="left" style="font-family:{_FONT_STACK};">
                <div class="oom-stat" style="font-size:22px;font-weight:800;
                  color:{_BRAND_NAVY};line-height:1;letter-spacing:-0.02em;">
                  &lt;24<span style="color:{_BRAND_PRIMARY};font-weight:900;">h</span>
                </div>
                <div style="font-size:10px;color:#64748b;text-transform:uppercase;
                  letter-spacing:0.1em;margin-top:6px;font-weight:600;">
                  From file → feed
                </div>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </td></tr>

    <!-- Pull quote — feels editorial, not transactional -->
    <tr><td class="oom-pad" style="padding:0 44px 30px 44px;">
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%"
        style="border-left:3px solid {_BRAND_PRIMARY};">
        <tr><td style="padding:6px 0 6px 16px;">
          <p style="font-family:{_FONT_STACK};font-style:italic;color:{_BRAND_NAVY};
            font-size:15px;line-height:1.5;margin:0;font-weight:500;">
            "Stop chasing list-prices. Start where the deals are."
          </p>
        </td></tr>
      </table>
    </td></tr>

    <!-- Fine print, with anchored time pill -->
    <tr><td class="oom-pad" style="padding:18px 44px 26px 44px;background:#fafbff;
      border-top:1px solid #f1f5f9;">
      <p style="font-family:{_FONT_STACK};color:#94a3b8;font-size:11px;
        line-height:1.6;margin:0;">
        <span style="display:inline-block;background:#ffffff;border:1px solid #e2e8f0;
          border-radius:999px;padding:3px 10px;font-weight:600;color:#475569;
          font-size:10px;letter-spacing:0.04em;margin-right:6px;">
          15 min
        </span>
        That's how long this link is good for. Didn't request it? Toss this email —
        nothing happens until you tap.
      </p>
    </td></tr>

  </table>

  <!-- Footer micro-nav -->
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="540"
    style="max-width:540px;margin-top:24px;font-family:{_FONT_STACK};">
    <tr><td align="center" style="font-size:11px;color:#94a3b8;line-height:1.7;">
      <a class="oom-pill" href="{_PUBLIC_WEB_URL}/search"
        style="display:inline-block;background:#ffffff;border:1px solid #e2e8f0;
        border-radius:999px;padding:6px 12px;color:#475569;text-decoration:none;
        font-weight:600;margin:2px;">Browse the feed</a>
      <a class="oom-pill" href="{_PUBLIC_WEB_URL}/membership"
        style="display:inline-block;background:#ffffff;border:1px solid #e2e8f0;
        border-radius:999px;padding:6px 12px;color:#475569;text-decoration:none;
        font-weight:600;margin:2px;">Membership</a>
      <a class="oom-pill" href="{_PUBLIC_WEB_URL}/sources"
        style="display:inline-block;background:#ffffff;border:1px solid #e2e8f0;
        border-radius:999px;padding:6px 12px;color:#475569;text-decoration:none;
        font-weight:600;margin:2px;">Data sources</a>
      <div style="margin-top:14px;color:#94a3b8;">
        <strong style="color:{_BRAND_NAVY};font-weight:700;">Only</strong><strong
        style="color:{_BRAND_PRIMARY};font-weight:700;">OffMarkets</strong><span
        style="color:{_BRAND_NAVY};font-weight:600;">.com</span>
        &nbsp;·&nbsp; signals, not listings. Public-record data only.
      </div>
    </td></tr>
  </table>

</td></tr>
</table>

</body></html>"""

    text = (
        "OnlyOffMarkets\n"
        "Step back into the radar.\n"
        "──────────────────────────\n\n"
        "One tap and you're back inside the feed. Your wallet, membership, and\n"
        "saved deals follow your email — no password, no friction.\n\n"
        f"  →  {link}\n\n"
        "This link is good for 15 minutes. Didn't request it? Toss this email.\n\n"
        '  "Stop chasing list-prices. Start where the deals are."\n\n'
        "—\n"
        "OnlyOffMarkets.com · signals, not listings · public-record data only\n"
    )
    return send(to, subject, html, text=text)
