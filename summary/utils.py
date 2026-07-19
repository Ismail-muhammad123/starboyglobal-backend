import requests
from django.conf import settings
from orders.services.clubkonnect import ClubKonnectClient
from payments.utils import PaystackGateway


def get_api_wallet_balance():
    from orders.services.clubkonnect import ClubKonnectClient
    try:
        client = ClubKonnectClient()
        balance = client.get_balance()
      
        if balance and isinstance(balance, dict):
            balance_amount = balance.get("balance", 0)
            balance_amount = float(str(balance_amount).replace(',', ''))
            return balance_amount
    except Exception:
        return 0.0
    
    return 0.0

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
