"""Billing — Stripe Checkout for token packs + memberships, plus webhook.

Auth still uses the X-User-Id header pattern — Stripe sees that as
`client_reference_id` so the webhook can credit the right wallet.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from services import memberships, stripe_client, tokens_pricing
from storage import memberships_db, tokens_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


def _user(x_user_id: str | None) -> str:
    if not x_user_id or len(x_user_id) < 6:
        raise HTTPException(400, "X-User-Id header required")
    return x_user_id.strip()[:64]


# ---------- Plans summary -----------------------------------------------------

@router.get("/plans")
async def list_plans() -> dict:
    return {
        "plans": memberships.list_plans(),
        "stripe_live": stripe_client.is_live(),
    }


@router.get("/membership")
async def get_membership(x_user_id: str | None = Header(default=None)) -> dict:
    user_id = _user(x_user_id)
    row = memberships_db.get(user_id)
    plan_id = row.get("plan", "free")
    plan_meta = memberships.get(plan_id)
    return {
        "user_id": user_id,
        "plan": plan_id,
        "plan_meta": plan_meta,
        "status": row.get("status", "active"),
        "current_period_end": row.get("current_period_end"),
        "cancel_at_period_end": bool(row.get("cancel_at_period_end")),
        "stripe_customer_id": row.get("stripe_customer_id"),
    }


# ---------- Checkout: token packs ---------------------------------------------

class TokenCheckoutIn(BaseModel):
    package_id: str


@router.post("/checkout/tokens")
async def checkout_tokens(
    body: TokenCheckoutIn,
    x_user_id: str | None = Header(default=None),
) -> dict:
    user_id = _user(x_user_id)
    try:
        pkg = tokens_pricing.get_package(body.package_id)
    except ValueError:
        raise HTTPException(400, "Unknown package")

    plan = memberships_db.get(user_id).get("plan", "free")
    bonus_pct = memberships.token_bonus_pct(plan)

    return stripe_client.checkout_token_pack(
        user_id=user_id,
        pack_id=pkg["id"],
        pack_label=pkg["label"],
        tokens=pkg["tokens"],
        price_usd=pkg["price_usd"],
        bonus_pct=bonus_pct,
    )


# ---------- Checkout: membership ----------------------------------------------

class MembershipCheckoutIn(BaseModel):
    plan: str  # "standard" | "premium"


@router.post("/checkout/membership")
async def checkout_membership(
    body: MembershipCheckoutIn,
    x_user_id: str | None = Header(default=None),
) -> dict:
    user_id = _user(x_user_id)
    if body.plan not in ("standard", "premium"):
        raise HTTPException(400, "Invalid plan")
    plan_meta = memberships.get(body.plan)
    pre_id = (
        stripe_client.PRICE_ID_PREMIUM if body.plan == "premium"
        else stripe_client.PRICE_ID_STANDARD
    )
    return stripe_client.checkout_membership(
        user_id=user_id,
        plan=body.plan,
        plan_label=plan_meta["label"],
        monthly_usd=plan_meta["price_usd"],
        pre_built_price_id=pre_id,
    )


# ---------- Confirm / sync (webhook-independent) ------------------------------

@router.post("/confirm-session")
async def confirm_session(
    body: dict,
    x_user_id: str | None = Header(default=None),
) -> dict:
    """Confirm a single Checkout Session by id.

    Frontend calls this on the `?status=success&session_id=...` landing.
    Idempotent — if the webhook already credited / activated, this becomes
    a no-op. Solves the case where Stripe's webhook delivery is delayed,
    rate-limited, or misconfigured.
    """
    user_id = _user(x_user_id)
    session_id = (body or {}).get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    if not stripe_client.is_live():
        return {"ok": True, "mock": True}

    import stripe  # type: ignore[import-untyped]

    stripe.api_key = stripe_client.STRIPE_SECRET
    try:
        s = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        log.warning("confirm-session retrieve failed: %s", exc)
        raise HTTPException(404, "Session not found")

    def _attr(obj, name, default=None):
        if hasattr(obj, name):
            return getattr(obj, name) or default
        try:
            return obj[name]
        except Exception:
            return default

    if _attr(s, "payment_status") not in ("paid", "no_payment_required"):
        return {"ok": False, "payment_status": _attr(s, "payment_status")}

    metadata = _attr(s, "metadata", {}) or {}
    md_user = metadata.get("user_id") if hasattr(metadata, "get") else _attr(metadata, "user_id")
    if md_user and md_user != user_id:
        raise HTTPException(403, "Session belongs to a different user")

    kind = metadata.get("kind") if hasattr(metadata, "get") else _attr(metadata, "kind")
    def _md(name, default=None):
        if hasattr(metadata, "get"):
            return metadata.get(name, default)
        return _attr(metadata, name, default)

    if kind == "tokens":
        pack_id = _md("pack_id") or "starter"
        try:
            pkg = tokens_pricing.get_package(pack_id)
        except ValueError:
            raise HTTPException(400, "Unknown pack")
        bonus_pct = int(_md("bonus_pct") or 0)
        bonus_tokens = pkg["tokens"] * bonus_pct // 100
        total = pkg["tokens"] + bonus_tokens
        marker = f"session:{session_id}"
        existing = tokens_db.transactions(user_id, limit=200)
        if any((tx.get("note") or "").endswith(marker + "]") or marker in (tx.get("note") or "")
               for tx in existing):
            return {"ok": True, "already_credited": True}
        tokens_db.credit(
            user_id, total,
            kind="purchase", package_id=pkg["id"],
            note=f"Stripe checkout — {pkg['label']} pack [{marker}]"
                 + (f" (+{bonus_tokens} Premium bonus)" if bonus_tokens else ""),
        )
        return {"ok": True, "credited": total, "bonus": bonus_tokens}

    if kind == "membership":
        plan = _md("plan") or "standard"
        memberships_db.set_plan(
            user_id, plan,
            status="active",
            stripe_customer_id=_attr(s, "customer"),
            stripe_subscription_id=_attr(s, "subscription"),
        )
        return {"ok": True, "plan": plan}

    raise HTTPException(400, f"Unknown checkout kind: {kind}")


@router.get("/debug/me")
async def debug_me(x_user_id: str | None = Header(default=None)) -> dict:
    """List recent Stripe activity tied to this user — diagnostic only."""
    user_id = _user(x_user_id)
    if not stripe_client.is_live():
        return {"ok": True, "mock": True}

    import stripe  # type: ignore[import-untyped]

    stripe.api_key = stripe_client.STRIPE_SECRET
    out: dict = {"user_id": user_id, "membership_row": memberships_db.get(user_id)}

    def _attr(obj, name, default=None):
        # Works for both StripeObject and plain dict.
        if hasattr(obj, name):
            return getattr(obj, name) or default
        try:
            return obj[name]
        except Exception:
            return default

    def _iter_data(resp):
        """Yield items from a Stripe ListObject regardless of SDK shape."""
        # Try attribute access first (most stable across v9-11+).
        items = getattr(resp, "data", None)
        if items is None:
            try:
                items = resp["data"]
            except Exception:
                items = []
        return items or []

    def _md_dict(obj):
        m = _attr(obj, "metadata", None)
        if m is None:
            return {}
        if hasattr(m, "to_dict_recursive"):
            try:
                return m.to_dict_recursive()
            except Exception:
                pass
        if hasattr(m, "to_dict"):
            try:
                return dict(m.to_dict())
            except Exception:
                pass
        try:
            return dict(m)
        except Exception:
            return {}

    sessions: list[dict] = []
    try:
        ses_resp = stripe.checkout.Session.list(limit=20)
        for s in _iter_data(ses_resp):
            md = _md_dict(s)
            sessions.append({
                "id": _attr(s, "id"),
                "client_reference_id": _attr(s, "client_reference_id"),
                "payment_status": _attr(s, "payment_status"),
                "mode": _attr(s, "mode"),
                "subscription": _attr(s, "subscription"),
                "customer": _attr(s, "customer"),
                "metadata": md,
                "created": _attr(s, "created"),
            })
    except Exception as exc:
        log.exception("debug_me sessions list failed")
        out["sessions_error"] = f"{type(exc).__name__}: {exc}"
    out["all_recent_sessions"] = sessions
    out["my_sessions"] = [s for s in sessions if s["client_reference_id"] == user_id]

    subs: list[dict] = []
    try:
        sub_resp = stripe.Subscription.list(status="all", limit=20)
        for s in _iter_data(sub_resp):
            md = _md_dict(s)
            subs.append({
                "id": _attr(s, "id"),
                "status": _attr(s, "status"),
                "customer": _attr(s, "customer"),
                "metadata": md,
                "created": _attr(s, "created"),
            })
    except Exception as exc:
        log.exception("debug_me subs list failed")
        out["subs_error"] = f"{type(exc).__name__}: {exc}"
    out["all_recent_subscriptions"] = subs
    out["my_subscriptions"] = [s for s in subs if s["metadata"].get("user_id") == user_id]

    return out


@router.post("/sync")
async def sync_from_stripe(x_user_id: str | None = Header(default=None)) -> dict:
    """Recover any active subscription on the user's Stripe account.

    Falls back to listing recent active subscriptions whose
    `metadata.user_id` matches. Used when the webhook never delivered
    (events not subscribed, URL typo, network) so users who paid still
    get their Premium.
    """
    user_id = _user(x_user_id)
    if not stripe_client.is_live():
        return {"ok": True, "mock": True}

    import stripe  # type: ignore[import-untyped]

    stripe.api_key = stripe_client.STRIPE_SECRET

    # 1) Look at this user's stored stripe_customer_id first (faster).
    row = memberships_db.get(user_id)
    cust_id = row.get("stripe_customer_id")
    sub: dict | None = None

    def _attr(obj, name, default=None):
        if hasattr(obj, name):
            return getattr(obj, name) or default
        try:
            return obj[name]
        except Exception:
            return default

    def _iter_data(resp):
        items = getattr(resp, "data", None)
        if items is None:
            try:
                items = resp["data"]
            except Exception:
                items = []
        return items or []

    def _md(obj, key):
        m = _attr(obj, "metadata", None)
        if m is None:
            return None
        if hasattr(m, "get"):
            return m.get(key)
        return _attr(m, key)

    if cust_id and not str(cust_id).startswith("mock_"):
        try:
            resp = stripe.Subscription.list(customer=cust_id, status="active", limit=5)
            for s in _iter_data(resp):
                sub = s
                break
        except Exception as exc:
            log.warning("sync stripe.Subscription.list(customer=) failed: %s", exc)

    # 2) Fall back to scanning recent active subs across the whole account.
    if not sub:
        try:
            resp = stripe.Subscription.list(status="active", limit=20)
            for s in _iter_data(resp):
                if _md(s, "user_id") == user_id:
                    sub = s
                    break
        except Exception as exc:
            log.warning("sync stripe.Subscription.list() failed: %s", exc)

    # 3) Walk recent Checkout Sessions — more reliable than Subscription
    #    metadata since we explicitly set client_reference_id = user_id.
    if not sub:
        try:
            resp = stripe.checkout.Session.list(limit=20)
            for ses in _iter_data(resp):
                if _attr(ses, "client_reference_id") != user_id:
                    continue
                if _attr(ses, "payment_status") not in ("paid", "no_payment_required"):
                    continue
                sub_id = _attr(ses, "subscription")
                if not sub_id:
                    continue
                try:
                    sub = stripe.Subscription.retrieve(sub_id)
                    break
                except Exception as exc:
                    log.warning("retrieve subscription %s failed: %s", sub_id, exc)
        except Exception as exc:
            log.warning("sync stripe.checkout.Session.list() failed: %s", exc)

    if not sub:
        return {"ok": False, "reason": "no_active_subscription"}

    plan = _md(sub, "plan") or "standard"
    period_end = _attr(sub, "current_period_end")
    period_end_str = None
    if period_end:
        from datetime import datetime, timezone
        try:
            period_end_str = datetime.fromtimestamp(int(period_end), tz=timezone.utc).isoformat()
        except Exception:
            period_end_str = None

    memberships_db.set_plan(
        user_id, plan,
        status=_attr(sub, "status", "active"),
        stripe_customer_id=_attr(sub, "customer"),
        stripe_subscription_id=_attr(sub, "id"),
        current_period_end=period_end_str,
        cancel_at_period_end=bool(_attr(sub, "cancel_at_period_end", False)),
    )
    return {"ok": True, "plan": plan, "subscription_id": _attr(sub, "id")}


# ---------- Customer portal ---------------------------------------------------

@router.post("/portal")
async def customer_portal(x_user_id: str | None = Header(default=None)) -> dict:
    user_id = _user(x_user_id)
    row = memberships_db.get(user_id)
    cust_id = row.get("stripe_customer_id")
    if not cust_id:
        raise HTTPException(400, "No active subscription")
    return stripe_client.customer_portal(cust_id)


# ---------- Mock-mode confirmation (dev / no-Stripe path) ---------------------

@router.get("/mock-confirm")
async def mock_confirm(type: str, user: str, pack: str = "", plan: str = ""):
    """Dev-only landing page when STRIPE_SECRET_KEY is unset.

    Real prod flow always returns a stripe.com Checkout URL — this only
    fires when running without keys, so we can demo the UX end-to-end.
    """
    if stripe_client.is_live():
        raise HTTPException(403, "Mock confirmation disabled in production")

    if type == "tokens" and pack:
        try:
            pkg = tokens_pricing.get_package(pack)
        except ValueError:
            raise HTTPException(400, "Unknown package")
        plan_id = memberships_db.get(user).get("plan", "free")
        bonus_pct = memberships.token_bonus_pct(plan_id)
        bonus_tokens = pkg["tokens"] * bonus_pct // 100
        total = pkg["tokens"] + bonus_tokens
        tokens_db.credit(
            user, total,
            kind="purchase",
            package_id=pkg["id"],
            note=f"Mock checkout — {pkg['label']} pack"
                 + (f" (+{bonus_tokens} Premium bonus)" if bonus_tokens else ""),
        )
        return RedirectResponse(f"{stripe_client.PUBLIC_WEB_URL}/tokens?status=success", status_code=302)

    if type == "membership" and plan:
        if plan not in ("standard", "premium"):
            raise HTTPException(400, "Invalid plan")
        memberships_db.set_plan(
            user, plan,
            status="active",
            stripe_customer_id="mock_cust_" + user[:12],
            stripe_subscription_id="mock_sub_" + user[:12],
        )
        return RedirectResponse(f"{stripe_client.PUBLIC_WEB_URL}/membership?status=success", status_code=302)

    raise HTTPException(400, "Bad mock-confirm payload")


# ---------- Stripe webhook ----------------------------------------------------

@router.post("/webhook")
async def stripe_webhook(request: Request) -> PlainTextResponse:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.verify_webhook(payload, sig)
    except RuntimeError:
        # Webhook secret not configured — accept silently in dev.
        log.warning("Stripe webhook hit without STRIPE_WEBHOOK_SECRET")
        return PlainTextResponse("ok", status_code=200)
    except Exception as exc:
        log.exception("Stripe webhook signature verification failed: %s", exc)
        raise HTTPException(400, "Invalid signature")

    etype = event["type"] if isinstance(event, dict) else event.type
    data = event["data"]["object"] if isinstance(event, dict) else event.data.object

    try:
        if etype == "checkout.session.completed":
            await _handle_checkout_completed(data)
        elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
            await _handle_subscription_change(data)
        elif etype == "invoice.payment_succeeded":
            await _handle_invoice_paid(data)
        # Other events ignored — return 200 so Stripe stops retrying.
    except Exception as exc:  # pragma: no cover
        log.exception("Webhook processing failed for %s: %s", etype, exc)

    return PlainTextResponse("ok", status_code=200)


async def _handle_checkout_completed(session: dict | object) -> None:
    """Token packs are one-shot Checkout sessions — credit on completion."""
    s = session if isinstance(session, dict) else dict(session)
    metadata = s.get("metadata") or {}
    kind = metadata.get("kind")
    user_id = metadata.get("user_id") or s.get("client_reference_id")
    if not user_id:
        log.warning("checkout.session.completed missing user_id")
        return

    if kind == "tokens":
        pack_id = metadata.get("pack_id") or "starter"
        try:
            pkg = tokens_pricing.get_package(pack_id)
        except ValueError:
            log.warning("Unknown pack id from Stripe: %s", pack_id)
            return
        bonus_pct = int(metadata.get("bonus_pct") or 0)
        bonus_tokens = pkg["tokens"] * bonus_pct // 100
        total = pkg["tokens"] + bonus_tokens
        tokens_db.credit(
            user_id,
            total,
            kind="purchase",
            package_id=pkg["id"],
            note=(
                f"Stripe checkout — {pkg['label']} pack"
                + (f" (+{bonus_tokens} Premium bonus)" if bonus_tokens else "")
            ),
        )
        log.info("Credited %d tokens to %s via Stripe", total, user_id)

    elif kind == "membership":
        plan = metadata.get("plan", "standard")
        memberships_db.set_plan(
            user_id,
            plan,
            status="active",
            stripe_customer_id=s.get("customer"),
            stripe_subscription_id=s.get("subscription"),
        )
        log.info("Activated %s plan for %s", plan, user_id)


async def _handle_subscription_change(sub: dict | object) -> None:
    s = sub if isinstance(sub, dict) else dict(sub)
    sub_id = s.get("id")
    status = s.get("status", "active")
    cancel_at_period_end = bool(s.get("cancel_at_period_end"))
    period_end = s.get("current_period_end")
    period_end_str = None
    if period_end:
        from datetime import datetime, timezone
        try:
            period_end_str = datetime.fromtimestamp(int(period_end), tz=timezone.utc).isoformat()
        except Exception:
            period_end_str = None
    metadata = s.get("metadata") or {}
    plan = metadata.get("plan") or "standard"
    if status in ("canceled", "incomplete_expired", "unpaid"):
        plan = "free"
    memberships_db.set_by_subscription_id(
        sub_id,
        plan=plan,
        status=status,
        current_period_end=period_end_str,
        cancel_at_period_end=cancel_at_period_end,
    )
    log.info("Subscription %s → %s (%s)", sub_id, plan, status)


async def _handle_invoice_paid(invoice: dict | object) -> None:
    """Monthly token grant — when a subscription renews, top up the wallet."""
    inv = invoice if isinstance(invoice, dict) else dict(invoice)
    sub_id = inv.get("subscription")
    if not sub_id:
        return
    # Look up the user_id via the subscription row we keep
    # (skip if the row doesn't exist — webhook ordering edge case).
    metadata = inv.get("subscription_details", {}).get("metadata", {}) or {}
    user_id = metadata.get("user_id")
    plan = metadata.get("plan")
    if not user_id or not plan:
        return
    grant = memberships.get(plan).get("monthly_token_grant", 0)
    if grant > 0:
        tokens_db.credit(
            user_id,
            grant,
            kind="grant",
            note=f"Monthly grant — {plan} plan",
        )
