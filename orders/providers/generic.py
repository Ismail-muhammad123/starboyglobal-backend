import requests
import json
import logging
from typing import Dict, Any, List, Optional
from ..interfaces import BaseVTUProvider

logger = logging.getLogger(__name__)

class GenericLocalProvider(BaseVTUProvider):
    """
    Standard implementation for many Nigerian VTU APIs (Alrahuz, MobileNIG, etc.) 
    that share similar request/response structures.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')

    @property
    def provider_name(self) -> str:
        return self.config.get('name', 'generic')

    @classmethod
    def get_supported_services(cls) -> List[str]:
        return ["airtime", "data", "tv", "electricity", "education"]

    @classmethod
    def get_config_requirements(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "api_key", "label": "API Key/Token", "type": "text", "required": True},
            {"name": "base_url", "label": "Base URL", "type": "text", "required": True},
        ]

    def _get_headers(self):
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def buy_airtime(self, phone: str, network: str, amount: float, reference: str) -> Dict[str, Any]:
        payload = {
            "network": network, # Expected to be the numeric ID or string required by specific generic API
            "amount": int(amount),
            "mobile_number": phone,
            "Ported_number": True,
            "airtime_type": "VTU"
        }
        url = f"{self.base_url}/topup/"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            data = response.json()
            if data.get('Status') == 'successful':
                return {"status": "SUCCESS", "provider_reference": data.get('id'), "raw_response": data}
            return {"status": "FAILED", "message": data.get('error', 'Transaction failed'), "raw_response": data}
        except Exception as e:
            return {"status": "FAILED", "message": str(e)}

    def buy_data(self, phone: str, network: str, plan_id: str, amount: float, reference: str) -> Dict[str, Any]:
        payload = {
            "network": network,
            "mobile_number": phone,
            "plan": plan_id,
            "Ported_number": True
        }
        url = f"{self.base_url}/data/"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            data = response.json()
            if data.get('Status') == 'successful':
                return {"status": "SUCCESS", "provider_reference": data.get('id'), "raw_response": data}
            return {"status": "FAILED", "message": data.get('error', 'Transaction failed'), "raw_response": data}
        except Exception as e:
            return {"status": "FAILED", "message": str(e)}

    def buy_tv(self, tv_id: str, package_id: str, smart_card_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        payload = {
            "cablename": tv_id,
            "smart_card_number": smart_card_number,
            "cableplan": package_id,
        }
        url = f"{self.base_url}/cablesub/"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            data = response.json()
            if data.get('Status') == 'successful':
                return {"status": "SUCCESS", "token": data.get('main_token'), "raw_response": data}
            return {"status": "FAILED", "message": data.get('error', 'Transaction failed'), "raw_response": data}
        except Exception as e:
            return {"status": "FAILED", "message": str(e)}

    def buy_electricity(self, disco_id: str, plan_id: str, meter_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        payload = {
            "disco_name": disco_id,
            "meter_number": meter_number,
            "Meter_Type": "Prepaid",
            "amount": int(amount),
        }
        url = f"{self.base_url}/billpayment/"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            data = response.json()
            if data.get('Status') == 'successful':
                return {"status": "SUCCESS", "token": data.get('main_token'), "raw_response": data}
            return {"status": "FAILED", "message": data.get('error', 'Transaction failed'), "raw_response": data}
        except Exception as e:
            return {"status": "FAILED", "message": str(e)}

    def buy_internet(self, plan_id: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        payload = {
            "network": kwargs.get('internet_variation', plan_id), # Try to map network or use generalized payload
            "mobile_number": phone,
            "plan": plan_id,
            "Ported_number": True
        }
        url = f"{self.base_url}/internet/"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            data = response.json()
            if data.get('Status') == 'successful':
                return {"status": "SUCCESS", "provider_reference": data.get('id'), "raw_response": data}
            return {"status": "FAILED", "message": data.get('error', 'Transaction failed'), "raw_response": data}
        except Exception as e:
            return {"status": "FAILED", "message": str(e)}

    def buy_education(self, exam_type: str, variation_id: str, quantity: int, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        payload = {
            "exam_name": exam_type,
            "quantity": quantity,
            "amount": amount
        }
        url = f"{self.base_url}/education/"
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload, timeout=20)
            data = response.json()
            if data.get('Status') == 'successful':
                return {"status": "SUCCESS", "token": data.get('pin'), "raw_response": data}
            return {"status": "FAILED", "message": data.get('error', 'Transaction failed'), "raw_response": data}
        except Exception as e:
            return {"status": "FAILED", "message": str(e)}

    def query_transaction(self, reference: str) -> Dict[str, Any]:
        url = f"{self.base_url}/query-status/{reference}/"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            data = response.json()
            status = "SUCCESS" if data.get('Status') == 'successful' else "FAILED"
            return {"status": status, "raw_response": data}
        except:
            return {"status": "PENDING", "error": "Query failed"}

    def cancel_transaction(self, reference: str) -> Dict[str, Any]:
        """Simulation: Cancellation not supported by generic mock."""
        return {"status": "FAILED", "message": "Cancellation not supported"}

    def validate_meter(self, meter_number: str, service: str) -> Dict[str, Any]:
        url = f"{self.base_url}/validate_meter/?meternumber={meter_number}&disconame={service}&mtype=Prepaid"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            data = response.json()
            account_name = data.get('name')
            return {"status": "SUCCESS" if account_name else "FAILED", "account_name": account_name, "raw_response": data}
        except:
            return {"status": "FAILED", "error": "Verification failed"}

    def validate_cable_id(self, card_number: str, service: str) -> Dict[str, Any]:
        url = f"{self.base_url}/validate_iuc/?smart_card_number={card_number}&cablename={service}"
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            data = response.json()
            account_name = data.get('name')
            return {"status": "SUCCESS" if account_name else "FAILED", "account_name": account_name, "raw_response": data}
        except:
            return {"status": "FAILED", "error": "Verification failed"}

    def get_wallet_balance(self) -> float:
        try:
            url = f"{self.base_url}/user/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            return float(response.json().get('user', {}).get('balance', 0))
        except:
            return 0.0

    def get_available_services(self) -> List[Dict[str, Any]]:
        return [
            {"type": "airtime", "id": "1", "name": "MTN"},
            {"type": "data", "id": "1", "name": "MTN Data"},
        ]

    def sync_airtime(self) -> int:
        try:
            url = f"{self.base_url}/networks/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            return len(self._deserialize_airtime(data))
        except: return 0

    def _deserialize_airtime(self, data: List[Dict]) -> List[Any]:
        from orders.models import AirtimeNetwork
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.airtime_margin if config else Decimal('0.00')
        base_100 = Decimal('100.00')

        created = []
        for item in data:
            net, _ = AirtimeNetwork.objects.update_or_create(
                service_id=item.get("id"),
                defaults={
                    "service_name": item.get("name"),
                    "cost_price": base_100,
                    "selling_price": base_100 + margin,
                    "agent_price": base_100,
                    "provider": getattr(self, "provider_config", None),
                }
            )
            created.append(net)
        return created

    def sync_data(self) -> int:
        try:
            url = f"{self.base_url}/dataplans/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            return len(self._deserialize_data(data))
        except: return 0

    def _deserialize_data(self, data: List[Dict]) -> List[Any]:
        from orders.models import DataService, DataVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.data_margin if config else Decimal('0.00')

        created = []
        for item in data:
            network_name = item.get("network_name") or item.get("network")
            service, _ = DataService.objects.get_or_create(
                service_id=item.get("network_id") or network_name,
                defaults={"service_name": network_name, "provider": getattr(self, "provider_config", None)}
            )
            p_amount = Decimal(str(item.get("amount") or 0))
            variation, _ = DataVariation.objects.update_or_create(
                variation_id=item.get("id"),
                service=service,
                defaults={
                    "name": item.get("plan_name") or item.get("name"),
                    "cost_price": p_amount,
                    "selling_price": p_amount + margin,
                    "agent_price": p_amount,
                    "is_active": True
                }
            )
            created.append(variation)
        return created

    def sync_cable(self) -> int:
        try:
            url = f"{self.base_url}/cableplans/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            return len(self._deserialize_tv(data))
        except: return 0

    def _deserialize_tv(self, data: List[Dict]) -> List[Any]:
        from orders.models import TVService, TVVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.tv_margin if config else Decimal('0.00')

        created = []
        for item in data:
            service_name = item.get("cablename") or item.get("name")
            service, _ = TVService.objects.get_or_create(
                service_id=item.get("cable_id") or service_name,
                defaults={"service_name": service_name, "provider": getattr(self, "provider_config", None)}
            )
            p_amount = Decimal(str(item.get("amount") or 0))
            variation, _ = TVVariation.objects.update_or_create(
                variation_id=item.get("id"),
                service=service,
                defaults={
                    "name": item.get("plan_name") or item.get("name"),
                    "cost_price": p_amount,
                    "selling_price": p_amount + margin,
                    "agent_price": p_amount,
                    "is_active": True
                }
            )
            created.append(variation)
        return created

    def sync_electricity(self) -> int:
        try:
            url = f"{self.base_url}/discos/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            return len(self._deserialize_electricity(data))
        except: return 0

    def _deserialize_electricity(self, data: List[Dict]) -> List[Any]:
        from orders.models import ElectricityService, ElectricityVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.electricity_margin if config else Decimal('0.00')

        created = []
        for item in data:
            service, _ = ElectricityService.objects.get_or_create(
                service_id=item.get("id") or item.get("name"),
                defaults={"service_name": item.get("name"), "provider": getattr(self, "provider_config", None)}
            )
            variation, _ = ElectricityVariation.objects.update_or_create(
                variation_id=f"{item.get('id')}-general",
                service=service,
                defaults={
                    "name": "General",
                    "cost_price": Decimal('0.00'),
                    "selling_price": margin,
                    "agent_price": Decimal('0.00'),
                    "is_active": True
                }
            )
            created.append(variation)
        return created

    def sync_internet(self) -> int:
        return 0

    def sync_education(self) -> int:
        try:
            url = f"{self.base_url}/education/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            return len(self._deserialize_education(data))
        except: return 0

    def _deserialize_education(self, data: List[Dict]) -> List[Any]:
        from orders.models import EducationService, EducationVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.education_margin if config else Decimal('0.00')

        created = []
        for item in data:
            name = item.get("name") or item.get("exam_name")
            service, _ = EducationService.objects.get_or_create(
                service_id=item.get("id") or name,
                defaults={"service_name": name, "provider": getattr(self, "provider_config", None)}
            )
            p_amount = Decimal(str(item.get("amount") or 0))
            variation, _ = EducationVariation.objects.update_or_create(
                variation_id=item.get("id"),
                service=service,
                defaults={
                    "name": item.get("plan_name") or name,
                    "cost_price": p_amount,
                    "selling_price": p_amount + margin,
                    "agent_price": p_amount,
                    "is_active": True
                }
            )
            created.append(variation)
        return created

    def fetch_airtime_live(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/networks/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            items = []
            for item in data:
                items.append({
                    "id": item.get("id"),
                    "service_id": str(item.get("id")),
                    "service_name": item.get("name"),
                    "name": item.get("name"),
                    "cost_price": 100.00,
                    "min_amount": item.get("min_amount", "50"),
                    "max_amount": item.get("max_amount", "200000"),
                    "is_active": True
                })
            return items
        except Exception:
            return []

    def fetch_data_live(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/dataplans/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            items = []
            for item in data:
                network_name = item.get("network_name") or item.get("network") or ""
                items.append({
                    "id": item.get("id"),
                    "variation_id": str(item.get("id")),
                    "name": item.get("plan_name") or item.get("name"),
                    "service_id": str(item.get("network_id") or network_name),
                    "network_name": network_name,
                    "cost_price": float(item.get("amount") or 0),
                    "plan_type": item.get("plan_type", "general"),
                    "is_active": True
                })
            return items
        except Exception:
            return []

    def fetch_tv_live(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/cableplans/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            items = []
            for item in data:
                service_name = item.get("cablename") or item.get("name") or ""
                items.append({
                    "id": item.get("id"),
                    "variation_id": str(item.get("id")),
                    "name": item.get("plan_name") or item.get("name"),
                    "service_id": str(item.get("cable_id") or service_name),
                    "service_name": service_name,
                    "cost_price": float(item.get("amount") or 0),
                    "is_active": True
                })
            return items
        except Exception:
            return []

    def fetch_electricity_live(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/discos/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            items = []
            for item in data:
                items.append({
                    "id": item.get("id"),
                    "variation_id": f"{item.get('id')}-general",
                    "name": item.get("name") or "General",
                    "service_id": str(item.get("id") or item.get("name")),
                    "service_name": item.get("name"),
                    "cost_price": 0.00,
                    "is_active": True
                })
            return items
        except Exception:
            return []

    def fetch_internet_live(self) -> List[Dict[str, Any]]:
        return []

    def fetch_education_live(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/education/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            data = response.json()
            items = []
            for item in data:
                name = item.get("name") or item.get("exam_name") or ""
                items.append({
                    "id": item.get("id"),
                    "variation_id": str(item.get("id")),
                    "name": item.get("plan_name") or name,
                    "service_id": str(item.get("id") or name),
                    "service_name": name,
                    "cost_price": float(item.get("amount") or 0),
                    "is_active": True
                })
            return items
        except Exception:
            return []

