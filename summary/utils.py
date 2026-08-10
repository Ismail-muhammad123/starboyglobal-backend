import requests
from django.conf import settings
from orders.services.clubkonnect import ClubKonnectClient
from payments.utils import PaystackGateway


def get_api_wallet_balance():
    total_balance = 0.0
    try:
        from orders.models import VTUProviderConfig
        from orders.router import ProviderRouter
        for provider in VTUProviderConfig.objects.filter(is_active=True):
            try:
                impl = ProviderRouter.get_provider_implementation(provider.name)
                if impl:
                    raw_bal = impl.get_wallet_balance()
                    if raw_bal is not None:
                        total_balance += float(str(raw_bal).replace(',', '').strip())
            except Exception:
                pass
    except Exception:
        pass
    return total_balance

def get_paystack_balance():
    gateway = PaystackGateway()
    try:
        url = f"{gateway.base_url}/balance"
        response = requests.get(url, headers=gateway.headers)
        if response.ok:
            data = response.json().get("data", [])
            for item in data:
                if item.get("currency") == "NGN":
                    return (float(item.get("balance", 0)) / 100) + 40000
                    # return (float(item.get("balance", 0)) / 100)

        return 0.0
    except Exception:
        return 0.0
