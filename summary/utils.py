import requests
from django.conf import settings
from django.core.cache import cache
from orders.services.clubkonnect import ClubKonnectClient
from payments.utils import PaystackGateway


def get_api_wallet_balance():
    cached_val = cache.get("total_vtu_wallet_balance")
    if cached_val is not None:
        return cached_val

    total_balance = 0.0
    try:
        from orders.models import VTUProviderConfig
        from orders.router import ProviderRouter
        for provider in VTUProviderConfig.objects.filter(is_active=True):
            try:
                cache_key = f"vtu_provider_balance_{provider.id}"
                cached_prov_bal = cache.get(cache_key)
                if cached_prov_bal is not None:
                    total_balance += cached_prov_bal
                    continue

                impl = ProviderRouter.get_provider_implementation(provider.name)
                if impl:
                    raw_bal = impl.get_wallet_balance()
                    if raw_bal is not None:
                        bal_float = float(str(raw_bal).replace(',', '').strip())
                        cache.set(cache_key, bal_float, 60)
                        total_balance += bal_float
            except Exception:
                pass
    except Exception:
        pass

    cache.set("total_vtu_wallet_balance", total_balance, 60)
    return total_balance

def get_paystack_balance():
    cached_val = cache.get("paystack_wallet_balance")
    if cached_val is not None:
        return cached_val

    gateway = PaystackGateway()
    try:
        url = f"{gateway.base_url}/balance"
        response = requests.get(url, headers=gateway.headers, timeout=3)
        if response.ok:
            data = response.json().get("data", [])
            for item in data:
                if item.get("currency") == "NGN":
                    bal = (float(item.get("balance", 0)) / 100) + 40000
                    cache.set("paystack_wallet_balance", bal, 60)
                    return bal

        cache.set("paystack_wallet_balance", 0.0, 30)
        return 0.0
    except Exception:
        return 0.0
