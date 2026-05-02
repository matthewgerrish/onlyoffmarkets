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
_LOGO_URL = "https://onlyoffmarkets.com/icon.png"  # 256x256 square icon-only mark
_PUBLIC_WEB_URL = "https://onlyoffmarkets.com"
_FONT_STACK = (
    "'Poppins', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
    "Helvetica, Arial, sans-serif"
)


def send_magic_link(to: str, link: str) -> dict[str, Any]:
    subject = "Sign in to OnlyOffMarkets"

    # Wordmark-only branding (no <img>) — the site logo PNG is 3:2 and
    # gets squished by email clients that respect explicit dimensions.
    # The Only(navy)/OffMarkets(blue) wordmark is the brand IS the
    # type, so we lead with it directly.
    #
    # Copy is functional, not pitchy: tells the user what the tools do
    # so they recognize what they're signing into.
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sign in · OnlyOffMarkets</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800;900&display=swap');
  :root {{ color-scheme: light; supported-color-schemes: light; }}

  /* Slow rotation for the brand mark in the header. Gmail web, Apple
     Mail and iOS Mail honor CSS animations in <style>; Outlook
     strips them and shows the static logo. Both look good. */
  @keyframes oom-spin {{
    0%   {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
  }}
  .oom-spin {{
    animation: oom-spin 8s linear infinite;
    transform-origin: 50% 50%;
  }}

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

    <!-- Header — animated icon mark + wordmark, navy/blue split. Logo
         spins slowly via CSS animation in clients that honor it; the
         static centered icon also looks correct in Outlook. -->
    <tr><td class="oom-pad" align="center"
      style="padding:32px 36px 24px 36px;border-bottom:1px solid #f1f5f9;">
      <div style="width:72px;height:72px;margin:0 auto 16px auto;
        background:radial-gradient(closest-side,{_BRAND_50} 0%,#ffffff 70%);
        border-radius:999px;line-height:0;font-size:0;">
        <img src="{_LOGO_URL}" alt=""
          width="72" height="72"
          class="oom-spin"
          style="display:block;border:0;outline:none;width:72px;height:72px;
          margin:0 auto;">
      </div>
      <div style="line-height:1;">
        <span style="font-family:{_FONT_STACK};font-weight:800;font-size:24px;
          letter-spacing:-0.02em;color:{_BRAND_NAVY};">Only</span><span
          style="font-family:{_FONT_STACK};font-weight:800;font-size:24px;
          letter-spacing:-0.02em;color:{_BRAND_PRIMARY};">OffMarkets</span><span
          style="font-family:{_FONT_STACK};font-weight:600;font-size:24px;
          letter-spacing:-0.02em;color:{_BRAND_NAVY};">.com</span>
      </div>
    </td></tr>

    <!-- Hero — short, functional, no marketing -->
    <tr><td class="oom-pad" align="left" style="padding:40px 44px 8px 44px;">
      <h1 class="oom-h1" style="font-family:{_FONT_STACK};font-weight:800;
        font-size:30px;line-height:1.15;letter-spacing:-0.02em;color:{_BRAND_NAVY};
        margin:0 0 12px 0;">
        Your sign-in link is ready.
      </h1>
      <p style="font-family:{_FONT_STACK};color:#475569;line-height:1.55;
        font-size:15px;margin:0 0 26px 0;">
        Tap below to sign in. The link is good for 15 minutes — once it's used
        or expires, request a new one anytime.
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

    <!-- Tools you'll see inside — functional, no pitch -->
    <tr><td class="oom-pad" style="padding:32px 44px 12px 44px;">
      <div style="font-family:{_FONT_STACK};font-size:11px;font-weight:700;
        letter-spacing:0.16em;text-transform:uppercase;color:#64748b;
        margin-bottom:14px;">
        What's inside
      </div>
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr><td style="padding:8px 0;font-family:{_FONT_STACK};">
          <strong style="color:{_BRAND_NAVY};font-weight:700;font-size:14px;">Search</strong>
          <span style="color:#64748b;font-size:14px;line-height:1.5;">
            &nbsp;— off-market signal feed across 25 states. Filter by source,
            equity, value, beds/baths, sqft.
          </span>
        </td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #f1f5f9;font-family:{_FONT_STACK};">
          <strong style="color:{_BRAND_NAVY};font-weight:700;font-size:14px;">Owner lookup</strong>
          <span style="color:#64748b;font-size:14px;line-height:1.5;">
            &nbsp;— skip-trace any property's owner: phone, email, mailing
            address. 1 token Standard / 3 tokens Pro.
          </span>
        </td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #f1f5f9;font-family:{_FONT_STACK};">
          <strong style="color:{_BRAND_NAVY};font-weight:700;font-size:14px;">Mailers</strong>
          <span style="color:#64748b;font-size:14px;line-height:1.5;">
            &nbsp;— send postcards through Lob from any property page or in
            bulk from your selections. 4 tokens / postcard.
          </span>
        </td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #f1f5f9;font-family:{_FONT_STACK};">
          <strong style="color:{_BRAND_NAVY};font-weight:700;font-size:14px;">Alerts</strong>
          <span style="color:#64748b;font-size:14px;line-height:1.5;">
            &nbsp;— save a search, get an email the moment a new signal
            matches. Daily digest or instant.
          </span>
        </td></tr>
        <tr><td style="padding:8px 0;border-top:1px solid #f1f5f9;font-family:{_FONT_STACK};">
          <strong style="color:{_BRAND_NAVY};font-weight:700;font-size:14px;">Wallet</strong>
          <span style="color:#64748b;font-size:14px;line-height:1.5;">
            &nbsp;— tokens cover lookups + mailers. Your balance and history
            live on the Tokens page.
          </span>
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
        "OnlyOffMarkets.com\n"
        "Sign in\n"
        "──────────────────\n\n"
        "Your sign-in link is ready. Tap to open in your browser:\n\n"
        f"  {link}\n\n"
        "Good for 15 minutes. Didn't request it? Ignore — nothing happens\n"
        "until you tap.\n\n"
        "What's inside:\n"
        "  • Search       off-market signal feed across 25 states\n"
        "  • Owner lookup skip-trace phone / email / address\n"
        "  • Mailers      postcards via Lob, single or bulk\n"
        "  • Alerts       email when new signals match your saved search\n"
        "  • Wallet       tokens cover lookups + mailers\n\n"
        "—\n"
        "OnlyOffMarkets.com · signals, not listings · public-record data only\n"
    )
    return send(to, subject, html, text=text)
