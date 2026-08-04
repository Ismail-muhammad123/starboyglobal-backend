from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseVTUProvider(ABC):
    """
    Abstract interface for all VTU providers.
    """

    

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_supported_services(cls) -> List[str]:
        """
        Return a list of service types supported by this provider.
        e.g., ['airtime', 'data', 'tv', 'electricity']
        """
        pass

    @classmethod
    @abstractmethod
    def get_config_requirements(cls) -> List[Dict[str, Any]]:
        """
        Return a list of configuration fields required for this provider.
        Format: [{'name': 'api_key', 'label': 'API Key', 'type': 'text', 'required': True}]
        """
        pass

    @abstractmethod
    def buy_airtime(self, phone: str, network: str, amount: float, reference: str) -> Dict[str, Any]:
        """
        Buy airtime.
        Returns: {'status': SUCCESS/FAILED/PENDING, 'provider_reference': '...', 'raw_response': {...}}
        """
        pass

    @abstractmethod
    def buy_data(self, phone: str, network: str, plan_id: str, amount: float, reference: str) -> Dict[str, Any]:
        """
        Buy data plans.
        """
        pass

    @abstractmethod
    def buy_tv(self, tv_id: str, package_id: str, smart_card_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """Buy Cable TV Subscription"""
        pass

    @abstractmethod
    def buy_electricity(self, disco_id: str, plan_id: str, meter_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """Buy Electricity Token"""
        pass

    @abstractmethod
    def buy_internet(self, plan_id: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """Buy Internet Data"""
        pass

    @abstractmethod
    def buy_education(self, exam_type: str, variation_id: str, quantity: int, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """Buy Education Pin (WAEC/NECO/JAMB)"""
        pass

    @abstractmethod
    def query_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Check the status of a VTU transaction.
        """
        pass

    @abstractmethod
    def cancel_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Cancel a pending/failed transaction.
        """
        pass

    @abstractmethod
    def handle_webhook(self, data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def handle_callback(self, data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def validate_meter(self, meter_number: str, service: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate_cable_id(self, card_number: str, service: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_wallet_balance(self) -> float:
        pass

    @abstractmethod
    def get_available_services(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def sync_airtime(self) -> int:
        """Fetch and sync airtime networks"""
        pass

    @abstractmethod
    def sync_data(self) -> int:
        """Fetch and sync data variations"""
        pass

    @abstractmethod
    def sync_cable(self) -> int:
        """Fetch and sync cable tv packages"""
        pass

    @abstractmethod
    def sync_electricity(self) -> int:
        """Fetch and sync electricity variations"""
        pass

    @abstractmethod
    def sync_internet(self) -> int:
        """Fetch and sync internet variations"""
        pass

    @abstractmethod
    def sync_education(self) -> int:
        """Fetch and sync education variations"""
        pass

    def fetch_airtime_live(self) -> List[Dict[str, Any]]:
        """Fetch live airtime networks from provider API without saving to DB"""
        return []

    def fetch_data_live(self) -> List[Dict[str, Any]]:
        """Fetch live data variations from provider API without saving to DB"""
        return []

    def fetch_tv_live(self) -> List[Dict[str, Any]]:
        """Fetch live cable TV variations from provider API without saving to DB"""
        return []

    def fetch_electricity_live(self) -> List[Dict[str, Any]]:
        """Fetch live electricity variations from provider API without saving to DB"""
        return []

    def fetch_internet_live(self) -> List[Dict[str, Any]]:
        """Fetch live internet variations from provider API without saving to DB"""
        return []

    def fetch_education_live(self) -> List[Dict[str, Any]]:
        """Fetch live education variations from provider API without saving to DB"""
        return []

