
import requests
import hmac
import hashlib
import json
from typing import Optional, Dict, Any, List
from django.conf import settings
from .models import PaystackConfig

class PaystackGateway:
    """
    Paystack implementation for handling transactions and webhooks.
    """

    def __init__(self, secret_key: Optional[str] = None):
        if not secret_key:
            config = PaystackConfig.objects.filter(is_active=True).first()
            if config:
                secret_key = config.secret_key
            else:
                secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', None)
        
        self.secret_key = secret_key
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, payload: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, headers=self.headers, json=payload, timeout=8)
        data = response.json()
        if not response.ok:
            raise Exception(data.get("message", "Paystack request failed"))
        return data

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=self.headers, timeout=8)
        data = response.json()
        if not response.ok:
            raise Exception(data.get("message", "Paystack request failed"))
        return data

    def initialize_deposit(self, email: str, amount: float, reference: str, callback_url: Optional[str] = None, metadata: Optional[dict] = None) -> Dict[str, Any]:
        payload = {
            "email": email,
            "amount": int(amount * 100),  # kobo
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata
        }
        res = self._post("/transaction/initialize", payload)
        return {
            "checkout_url": res["data"]["authorization_url"],
            "reference": res["data"]["reference"],
            "status": True,
            "raw_response": res
        }

    def create_virtual_account(self, email: str, first_name: str, last_name: str, phone: str, middle_name: str = "") -> Dict[str, Any]:
        """
        Provision a dedicated virtual account for a customer.
        1. Fetch/Create Paystack Customer
        2. Assign Dedicated Account
        """
        # Ensure customer exists
        try:
             # Try to get existing customer by email
             res = self._get(f"/customer/{email}")
             customer_id = res["data"]["id"]
        except:
             # Create new customer if not found
             payload = {
                 "email": email,
                 "first_name": first_name,
                 "last_name": last_name,
                 "phone": phone
             }
             if middle_name:
                 payload["middle_name"] = middle_name
             res = self._post("/customer", payload)
             customer_id = res["data"]["id"]

        # Assign Dedicated Account
        payload = {
            "customer": customer_id,
            "preferred_bank": "wema-bank"
        }
        return self._post("/dedicated_account", payload)

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        res = self._get(f"/transaction/verify/{reference}")
        data = res["data"]
        status_map = {"success": "SUCCESS", "failed": "FAILED", "reversed": "FAILED", "abandoned": "PENDING"}
        return {
            "status": status_map.get(data["status"], "PENDING"),
            "amount": float(data["amount"]) / 100,
            "currency": data["currency"],
            "raw_response": res
        }

    def list_banks(self) -> List[Dict[str, str]]:
        res = self._get("/bank?country=nigeria")
        return [{"name": b["name"], "code": b["code"]} for b in res["data"]]

    def resolve_account(self, account_number: str, bank_code: str) -> Dict[str, Any]:
        res = self._get(f"/bank/resolve?account_number={account_number}&bank_code={bank_code}")
        print(res)
        return {
            "account_name": res["data"]["account_name"],
            "account_number": res["data"]["account_number"],
            "bank_code": bank_code
        }

    def initiate_transfer(self, amount: float, bank_code: str, account_number: str, account_name: str, reference: str, reason: Optional[str] = None) -> Dict[str, Any]:
        # 1. Create Recipient
        recip_payload = {
            "type": "nuban",
            "name": account_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN"
        }
        recip_res = self._post("/transferrecipient", recip_payload)
        recipient_code = recip_res["data"]["recipient_code"]

        # 2. Initiate Transfer
        transfer_payload = {
            "source": "balance",
            "amount": int(amount * 100),
            "recipient": recipient_code,
            "reason": reason,
            "reference": reference
        }
        res = self._post("/transfer", transfer_payload)
        status_map = {"success": "SUCCESS", "failed": "FAILED", "pending": "PENDING", "processing": "PENDING"}
        return {
            "status": status_map.get(res["data"]["status"], "PENDING"),
            "transfer_code": res["data"]["transfer_code"],
            "raw_response": res
        }

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not self.secret_key:
            return False
        computed = hmac.new(self.secret_key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed, signature)


# class FlutterwaveGatewayImpl(BasePaymentGateway):
#     """
#     Flutterwave implementation of BasePaymentGateway.
#     """

#     def __init__(self, secret_key: str):
#         self.secret_key = secret_key
#         self.base_url = "https://api.flutterwave.com/v3"
#         self.headers = {
#             "Authorization": f"Bearer {self.secret_key}",
#             "Content-Type": "application/json",
#         }

#     def _post(self, endpoint: str, payload: dict) -> Dict[str, Any]:
#         url = f"{self.base_url}{endpoint}"
#         response = requests.post(url, headers=self.headers, json=payload)
#         data = response.json()
#         if not response.ok:
#             raise Exception(data.get("message", "Flutterwave request failed"))
#         return data

#     def _get(self, endpoint: str) -> Dict[str, Any]:
#         url = f"{self.base_url}{endpoint}"
#         response = requests.get(url, headers=self.headers)
#         data = response.json()
#         if not response.ok:
#             raise Exception(data.get("message", "Flutterwave request failed"))
#         return data

#     def initialize_deposit(self, email: str, amount: float, reference: str, callback_url: Optional[str] = None, metadata: Optional[dict] = None) -> Dict[str, Any]:
#         payload = {
#             "tx_ref": reference,
#             "amount": float(amount),
#             "currency": "NGN",
#             "redirect_url": callback_url,
#             "customer": {"email": email},
#             "meta": metadata
#         }
#         res = self._post("/payments", payload)
#         return {
#             "status": True,
#             "checkout_url": res["data"]["link"],
#             "reference": reference,
#             "raw_response": res
#         }

#     def verify_transaction(self, reference: str) -> Dict[str, Any]:
#         # Usually verify by ID, but can verify by tx_ref
#         res = self._get(f"/transactions/verify_by_reference?tx_ref={reference}")
#         data = res["data"]
#         status_map = {"successful": "SUCCESS", "failed": "FAILED"}
#         return {
#             "status": status_map.get(data["status"], "PENDING"),
#             "amount": float(data["amount"]),
#             "currency": data["currency"],
#             "raw_response": res
#         }

#     def list_banks(self) -> List[Dict[str, str]]:
#         res = self._get("/banks/NG")
#         return [{"name": b["name"], "code": b["code"]} for b in res["data"]]

#     def resolve_account(self, account_number: str, bank_code: str) -> Dict[str, Any]:
#         res = self._post("/accounts/resolve", {"account_number": account_number, "account_bank": bank_code})
#         return {
#             "account_name": res["data"]["account_name"],
#             "account_number": account_number,
#             "bank_code": bank_code
#         }

#     def initiate_transfer(self, amount: float, bank_code: str, account_number: str, account_name: str, reference: str, reason: Optional[str] = None) -> Dict[str, Any]:
#         payload = {
#             "account_bank": bank_code,
#             "account_number": account_number,
#             "amount": float(amount),
#             "narration": reason,
#             "currency": "NGN",
#             "reference": reference,
#             "callback_url": None,
#             "debit_currency": "NGN"
#         }
#         res = self._post("/transfers", payload)
#         status_map = {"NEW": "PENDING", "SUCCESSFUL": "SUCCESS", "FAILED": "FAILED"}
#         return {
#             "status": status_map.get(res["data"]["status"], "PENDING"),
#             "transfer_code": str(res["data"]["id"]),
#             "raw_response": res
#         }

#     def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
#         secret_hash = getattr(settings, "FLUTTERWAVE_SECRET_HASH", "test_hash")
#         return signature == secret_hash


# class MonnifyGatewayImpl(BasePaymentGateway):
#     """
#     Monnify implementation of BasePaymentGateway.
#     """

#     def __init__(self, api_key: str, api_secret: str, base_url: str, contract_code: str):
#         self.api_key = api_key
#         self.api_secret = api_secret
#         self.base_url = base_url
#         self.contract_code = contract_code
#         self._access_token = None
#         self._token_expires_at = None

#     def _get_auth_header(self):
#         creds = f"{self.api_key}:{self.api_secret}"
#         b64 = base64.b64encode(creds.encode()).decode()
#         return {"Authorization": f"Basic {b64}"}

#     def _authenticate(self):
#         if self._access_token and datetime.now() < self._token_expires_at:
#             return self._access_token

#         url = f"{self.base_url}/api/v1/auth/login"
#         resp = requests.post(url, headers=self._get_auth_header())
#         resp.raise_for_status()
#         body = resp.json()["responseBody"]
#         self._access_token = body["accessToken"]
#         self._token_expires_at = datetime.now() + timedelta(seconds=body["expiresIn"] - 60)
#         return self._access_token

#     def _headers(self):
#         return {
#             "Authorization": f"Bearer {self._authenticate()}",
#             "Content-Type": "application/json",
#         }

#     def initialize_deposit(self, email: str, amount: float, reference: str, callback_url: Optional[str] = None, metadata: Optional[dict] = None) -> Dict[str, Any]:
#         payload = {
#             "amount": float(amount),
#             "customerName": f"User {email}",
#             "customerEmail": email,
#             "paymentReference": reference,
#             "paymentDescription": f"Deposit: {reference}",
#             "currencyCode": "NGN",
#             "contractCode": self.contract_code,
#             "redirectUrl": callback_url,
#             "metadata": metadata
#         }
#         url = f"{self.base_url}/api/v1/merchant/transactions/init-transaction"
#         resp = requests.post(url, json=payload, headers=self._headers())
#         res = resp.json()
#         if not res["requestSuccessful"]:
#             raise Exception(res.get("responseMessage", "Monnify request failed"))
#         return {
#             "status": True,
#             "checkout_url": res["responseBody"]["checkoutUrl"],
#             "reference": reference,
#             "raw_response": res
#         }

#     def verify_transaction(self, reference: str) -> Dict[str, Any]:
#         url = f"{self.base_url}/api/v2/transactions/{reference}"
#         resp = requests.get(url, headers=self._headers())
#         res = resp.json()
#         data = res["responseBody"]
#         status_map = {"PAID": "SUCCESS", "OVERPAID": "SUCCESS", "PARTIALLY_PAID": "PENDING", "PENDING": "PENDING", "FAILED": "FAILED", "EXPIRED": "FAILED"}
#         return {
#             "status": status_map.get(data["paymentStatus"], "PENDING"),
#             "amount": float(data["amountPaid"]),
#             "currency": data["currencyCode"],
#             "raw_response": res
#         }

#     def list_banks(self) -> List[Dict[str, str]]:
#         url = f"{self.base_url}/api/v1/banks"
#         resp = requests.get(url, headers=self._headers())
#         res = resp.json()
#         return [{"name": b["name"], "code": b["code"]} for b in res["responseBody"]]

#     def resolve_account(self, account_number: str, bank_code: str) -> Dict[str, Any]:
#         url = f"{self.base_url}/api/v1/disbursement/account/validate?accountNumber={account_number}&bankCode={bank_code}"
#         resp = requests.get(url, headers=self._headers())
#         res = resp.json()
#         if not res["requestSuccessful"]:
#             raise Exception(res.get("responseMessage", "Account resolution failed"))
#         return {
#             "account_name": res["responseBody"]["accountName"],
#             "account_number": account_number,
#             "bank_code": bank_code
#         }

#     def initiate_transfer(self, amount: float, bank_code: str, account_number: str, account_name: str, reference: str, reason: Optional[str] = None) -> Dict[str, Any]:
#         payload = {
#             "amount": float(amount),
#             "reference": reference,
#             "narration": reason,
#             "bankCode": bank_code,
#             "accountNumber": account_number,
#             "currency": "NGN",
#             "walletId": self.contract_code  # Or defined wallet ID
#         }
#         url = f"{self.base_url}/api/v1/disbursement/single"
#         resp = requests.post(url, json=payload, headers=self._headers())
#         res = resp.json()
#         status_map = {"SUCCESS": "SUCCESS", "QUEUED": "PENDING", "PROCESSING": "PENDING", "FAILED": "FAILED"}
#         return {
#             "status": status_map.get(res["responseBody"]["status"], "PENDING"),
#             "transfer_code": res["responseBody"]["reference"],
#             "raw_response": res
#         }

#     def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
#         computed = hmac.new(self.api_secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
#         return hmac.compare_digest(computed, signature)

# # Backward Compatibility Aliases
# PaystackGateway = PaystackGatewayImpl
# MonnifyClient = MonnifyGatewayImpl