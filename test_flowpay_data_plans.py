#!/usr/bin/env python3
"""
test_flowpay_data_plans.py
──────────────────────────
Fetches live data plans from the FlowPay API and prints each plan
structured exactly as it would be saved to the DataVariation model.

Usage:
    # Option A – let Django find the API key from the DB:
    python manage.py shell < test_flowpay_data_plans.py

    # Option B – run standalone with an env-var for the key:
    FLOWPAY_API_KEY=<your_token> python test_flowpay_data_plans.py
"""

import os
import sys
import json
import logging
import requests
from decimal import Decimal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Network code → (internal service_id, display name) ────────────────────────
NETWORK_CODE_MAP = {
    "mtn":     ("1", "MTN"),
    "airtel":  ("4", "Airtel"),
    "glo":     ("2", "Glo"),
    "9mobile": ("3", "9mobile"),
    "etisalat":("3", "9mobile"),
}

BASE_URL = "https://app.flowpay.ng"


def resolve_api_key() -> str:
    """
    Try to pull the FlowPay API key from:
      1. FLOWPAY_API_KEY environment variable
      2. The Django VtuProviderConfig DB record (requires Django to be set up)
    """
    key = os.environ.get("FLOWPAY_API_KEY", "").strip()
    if key:
        return key

    # Attempt Django DB lookup
    try:
        import django
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        django.setup()
        from orders.models import VTUProviderConfig
        config = VTUProviderConfig.objects.filter(name="flowpay").first()
        if config and config.api_key:
            key = config.api_key.strip()
        if key:
            logger.info("API key loaded from Django DB (VtuProviderConfig).")
            return key
    except Exception as e:
        logger.warning(f"Django DB lookup failed: {e}")

    raise ValueError(
        "No FlowPay API key found.\n"
        "Set env var  FLOWPAY_API_KEY=<token>  or configure it in the Django admin."
    )


def fetch_data_plans(api_key: str) -> dict:
    """Hit /api/data_plans and return the raw JSON response."""
    url = f"{BASE_URL}/api/data_plans"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    logger.info(f"GET {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_plans(raw: dict, margin: Decimal = Decimal("0.00")) -> list[dict]:
    """
    Traverse  mobile_networks → plan_types → data_plans
    and return a list of dicts shaped like DataVariation model fields.

    Each dict contains:
        variation_id  – plan id (str)  ← used as the DB lookup key
        service_id    – "1" / "2" / "3" / "4"  (network)
        service_name  – "MTN" / "Airtel" / etc.
        plan_type     – plan type code  e.g. "sme", "gifting"
        name          – human-readable e.g. "MTN SME 500 MB (30 DAYS)"
        cost_price    – Decimal from API "amount" field
        selling_price – cost_price + margin
        agent_price   – same as cost_price
        is_active     – True
    """
    mobile_networks = raw.get("mobile_networks") if isinstance(raw, dict) else None
    if not mobile_networks:
        logger.error("Response does not contain 'mobile_networks'. Raw keys: %s", list(raw.keys()) if isinstance(raw, dict) else type(raw))
        return []

    results = []

    for network in mobile_networks:
        if not isinstance(network, dict):
            continue

        # ── Resolve network ────────────────────────────────────────────────
        net_code     = str(network.get("code", "")).lower().strip()
        net_name_raw = str(network.get("name", "")).lower().strip()

        mapping = NETWORK_CODE_MAP.get(net_code) or NETWORK_CODE_MAP.get(net_name_raw)
        if not mapping:
            for key, val in NETWORK_CODE_MAP.items():
                if key in net_name_raw or key in net_code:
                    mapping = val
                    break

        if not mapping:
            logger.debug(f"Unknown network '{network.get('name')}', skipping.")
            continue

        db_service_id, net_name = mapping

        # ── Loop plan types ────────────────────────────────────────────────
        for plan_type in network.get("plan_types", []):
            if not isinstance(plan_type, dict):
                continue
            if not plan_type.get("active", 1):
                continue

            pt_name = str(plan_type.get("name", "General")).strip()
            pt_code = str(plan_type.get("code", pt_name)).strip().lower()

            # ── Loop individual data plans ─────────────────────────────────
            for plan in plan_type.get("data_plans", []):
                if not isinstance(plan, dict):
                    continue
                if not plan.get("active", 1):
                    continue

                plan_id  = str(plan.get("id", ""))
                size     = plan.get("size", "")
                volume   = str(plan.get("volume", "")).upper()
                validity = str(plan.get("validity", "")).strip()
                amount   = plan.get("amount", "0")

                size_str = f"{size} {volume}" if volume else str(size)
                name     = f"{net_name} {pt_name} {size_str}"
                if validity:
                    name += f" ({validity})"

                cost_price = Decimal(str(amount))

                results.append({
                    "variation_id":  plan_id,
                    "service_id":    db_service_id,
                    "service_name":  net_name,
                    "plan_type":     pt_code,
                    "name":          name,
                    "cost_price":    cost_price,
                    "selling_price": cost_price + margin,
                    "agent_price":   cost_price,
                    "is_active":     True,
                })

    return results


def print_results(plans: list[dict]) -> None:
    """Pretty-print the parsed plan list."""
    if not plans:
        print("\n⚠️  No plans parsed.\n")
        return

    # Group by service for readability
    from collections import defaultdict
    grouped: dict[str, list] = defaultdict(list)
    for p in plans:
        grouped[p["service_name"]].append(p)

    total = 0
    for net_name, net_plans in grouped.items():
        print(f"\n{'='*60}")
        print(f"  {net_name}  ({len(net_plans)} plans)")
        print(f"{'='*60}")
        for p in net_plans:
            print(
                f"  [{p['variation_id']:>5}] "
                f"{p['name']:<45} "
                f"₦{p['cost_price']:>10}  "
                f"type={p['plan_type']}"
            )
        total += len(net_plans)

    print(f"\n{'─'*60}")
    print(f"  Total plans parsed: {total}")
    print(f"{'─'*60}\n")

    # Also dump as JSON for easy copy-paste
    print("\n── JSON dump (ready for inspection) ──\n")
    print(json.dumps(
        [{**p, "cost_price": str(p["cost_price"]), "selling_price": str(p["selling_price"]), "agent_price": str(p["agent_price"])} for p in plans],
        indent=2
    ))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    margin_input = sys.argv[1] if len(sys.argv) > 1 else "0"
    margin = Decimal(margin_input)

    try:
        api_key = resolve_api_key()
    except ValueError as e:
        print(f"\n❌  {e}\n")
        sys.exit(1)

    try:
        raw = fetch_data_plans(api_key)
    except Exception as e:
        print(f"\n❌  API call failed: {e}\n")
        sys.exit(1)

    plans = parse_plans(raw, margin=margin)
    print_results(plans)
