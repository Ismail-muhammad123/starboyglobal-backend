import requests
import logging
from typing import Dict, Any, List, Optional
from ..interfaces import BaseVTUProvider

logger = logging.getLogger(__name__)

# =============================================================================
# Hardcoded plan catalogs — FlowPay plan IDs and prices from documentation.
# =============================================================================

AIRTIME_NETWORKS_DATA = [
    {"service_id": "1", "service_name": "MTN", "min_amount": "50", "max_amount": "50000"},
    {"service_id": "2", "service_name": "Airtel", "min_amount": "50", "max_amount": "50000"},
    {"service_id": "3", "service_name": "Glo", "min_amount": "50", "max_amount": "50000"},
    {"service_id": "4", "service_name": "9mobile", "min_amount": "50", "max_amount": "50000"},
]

DATA_PLANS_BY_NETWORK = {
    # ── MTN (network id "1") ────────────────────────────────────────────
    "1": {
        "name": "MTN",
        "plans": [
            # SME
            {"plan_id": "82", "name": "MTN SME 500 MB", "selling_price": 300, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "83", "name": "MTN SME 1 GB", "selling_price": 400, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "84", "name": "MTN SME 2 GB", "selling_price": 800, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "86", "name": "MTN SME 3 GB", "selling_price": 1200, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "87", "name": "MTN SME 5 GB", "selling_price": 1700, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "88", "name": "MTN SME 10 GB", "selling_price": 4500, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "89", "name": "MTN SME 20 GB", "selling_price": 9000, "plan_type": "sme", "validity": "30 DAYS"},
            {"plan_id": "215", "name": "MTN SME 25 GB", "selling_price": 12000, "plan_type": "sme", "validity": "30 DAYS"},
            # GIFTING
            {"plan_id": "91", "name": "MTN GIFTING 500 MB", "selling_price": 280, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "92", "name": "MTN GIFTING 1 GB", "selling_price": 400, "plan_type": "gifting", "validity": "7 DAYS"},
            {"plan_id": "93", "name": "MTN GIFTING 2 GB", "selling_price": 750, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "94", "name": "MTN GIFTING 2.5 GB", "selling_price": 900, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "95", "name": "MTN GIFTING 3.2 GB", "selling_price": 1000, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "96", "name": "MTN GIFTING 5 GB", "selling_price": 1750, "plan_type": "gifting", "validity": "7 DAYS"},
            {"plan_id": "97", "name": "MTN GIFTING 6 GB", "selling_price": 2500, "plan_type": "gifting", "validity": "7 DAYS"},
            {"plan_id": "98", "name": "MTN GIFTING 11 GB", "selling_price": 3500, "plan_type": "gifting", "validity": "7 DAYS"},
            {"plan_id": "99", "name": "MTN GIFTING 20 GB", "selling_price": 5000, "plan_type": "gifting", "validity": "7 DAYS"},
            {"plan_id": "100", "name": "MTN GIFTING 25 GB", "selling_price": 9000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "101", "name": "MTN GIFTING 30 GB", "selling_price": 9500, "plan_type": "gifting", "validity": "BROADBAND 30 DAYS"},
            {"plan_id": "102", "name": "MTN GIFTING 35 GB", "selling_price": 7500, "plan_type": "gifting", "validity": "POSTPAID 30 DAYS"},
            {"plan_id": "103", "name": "MTN GIFTING 40 GB", "selling_price": 10000, "plan_type": "gifting", "validity": "POSTPAID 60 DAYS"},
            {"plan_id": "104", "name": "MTN GIFTING 60 GB", "selling_price": 14500, "plan_type": "gifting", "validity": "BROADBAND 30 DAYS"},
            {"plan_id": "105", "name": "MTN GIFTING 65 GB", "selling_price": 16000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "106", "name": "MTN GIFTING 75 GB", "selling_price": 18000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "107", "name": "MTN GIFTING 90 GB", "selling_price": 25000, "plan_type": "gifting", "validity": "60 DAYS"},
            {"plan_id": "108", "name": "MTN GIFTING 150 GB", "selling_price": 40000, "plan_type": "gifting", "validity": "60 DAYS"},
            {"plan_id": "109", "name": "MTN GIFTING 165 GB", "selling_price": 45000, "plan_type": "gifting", "validity": "60 DAYS"},
            {"plan_id": "110", "name": "MTN GIFTING 200 GB", "selling_price": 50000, "plan_type": "gifting", "validity": "60 DAYS"},
            {"plan_id": "111", "name": "MTN GIFTING 250 GB", "selling_price": 60000, "plan_type": "gifting", "validity": "60 DAYS"},
            {"plan_id": "112", "name": "MTN GIFTING 450 GB", "selling_price": 75000, "plan_type": "gifting", "validity": "BROADBAND 90 DAYS"},
            {"plan_id": "113", "name": "MTN GIFTING 800 GB", "selling_price": 130000, "plan_type": "gifting", "validity": "60 DAYS"},
            # DATA SHARE
            {"plan_id": "234", "name": "MTN DATA SHARE 1 GB", "selling_price": 375, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "231", "name": "MTN DATA SHARE 2 GB", "selling_price": 760, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "232", "name": "MTN DATA SHARE 3 GB", "selling_price": 1100, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "233", "name": "MTN DATA SHARE 5 GB", "selling_price": 1400, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "235", "name": "MTN DATA SHARE 10 GB", "selling_price": 4490, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "236", "name": "MTN DATA SHARE 20 GB", "selling_price": 5500, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "246", "name": "MTN DATA SHARE 500 MB", "selling_price": 300, "plan_type": "gifting", "validity": "30 DAYS"},
            # OFFERS
            {"plan_id": "122", "name": "MTN OFFERS 3.2 GB", "selling_price": 980, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "123", "name": "MTN OFFERS 3.5 GB", "selling_price": 1000, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "125", "name": "MTN OFFERS 4 GB", "selling_price": 1200, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "126", "name": "MTN OFFERS 5.5 GB", "selling_price": 1500, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "230", "name": "MTN OFFERS 7 GB", "selling_price": 1800, "plan_type": "gifting", "validity": "2 DAYS"},
        ]
    },
    # ── Airtel (network id "2") ─────────────────────────────────────────
    "2": {
        "name": "Airtel",
        "plans": [
            # CORPORATE
            {"plan_id": "162", "name": "Airtel CORPORATE 500 MB", "selling_price": 485, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "164", "name": "Airtel CORPORATE 1 GB", "selling_price": 780, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "165", "name": "Airtel CORPORATE 2 GB", "selling_price": 1480, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "166", "name": "Airtel CORPORATE 3 GB", "selling_price": 1950, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "167", "name": "Airtel CORPORATE 4 GB", "selling_price": 2500, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "168", "name": "Airtel CORPORATE 5 GB", "selling_price": 3500, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "169", "name": "Airtel CORPORATE 6 GB", "selling_price": 4000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "170", "name": "Airtel CORPORATE 8 GB", "selling_price": 4500, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "171", "name": "Airtel CORPORATE 10 GB", "selling_price": 5000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "175", "name": "Airtel CORPORATE 12 GB", "selling_price": 5500, "plan_type": "corporate", "validity": "(Coll 100 mins + 5 SMS) 30 DAYS"},
            {"plan_id": "176", "name": "Airtel CORPORATE 13 GB", "selling_price": 6000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "177", "name": "Airtel CORPORATE 18 GB", "selling_price": 7500, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "178", "name": "Airtel CORPORATE 25 GB", "selling_price": 9500, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "179", "name": "Airtel CORPORATE 35 GB", "selling_price": 11000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "180", "name": "Airtel CORPORATE 60 GB", "selling_price": 15000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "181", "name": "Airtel CORPORATE 100 GB", "selling_price": 20000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "182", "name": "Airtel CORPORATE 160 GB", "selling_price": 30000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "183", "name": "Airtel CORPORATE 210 GB", "selling_price": 40000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "184", "name": "Airtel CORPORATE 300 GB", "selling_price": 50000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "185", "name": "Airtel CORPORATE 350 GB", "selling_price": 60000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "188", "name": "Airtel CORPORATE 650 GB", "selling_price": 100000, "plan_type": "corporate", "validity": "90 DAYS"},
            # CORPORATE 1
            {"plan_id": "237", "name": "Airtel CORPORATE 1 500 MB", "selling_price": 485, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "238", "name": "Airtel CORPORATE 1 1 GB", "selling_price": 780, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "239", "name": "Airtel CORPORATE 1 1.5 GB", "selling_price": 1000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "240", "name": "Airtel CORPORATE 1 2 GB", "selling_price": 1479, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "241", "name": "Airtel CORPORATE 1 3 GB", "selling_price": 2000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "242", "name": "Airtel CORPORATE 1 5 GB", "selling_price": 2500, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "243", "name": "Airtel CORPORATE 1 6 GB", "selling_price": 3000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "244", "name": "Airtel CORPORATE 1 7 GB", "selling_price": 3400, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "245", "name": "Airtel CORPORATE 1 10 GB", "selling_price": 4000, "plan_type": "corporate", "validity": "30 DAYS"},
            # GIFTING
            {"plan_id": "190", "name": "Airtel GIFTING 300 MB", "selling_price": 100, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "191", "name": "Airtel GIFTING 600 MB", "selling_price": 230, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "194", "name": "Airtel GIFTING 1.5 GB", "selling_price": 500, "plan_type": "gifting", "validity": "1 DAY"},
            {"plan_id": "195", "name": "Airtel GIFTING 2 GB", "selling_price": 600, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "196", "name": "Airtel GIFTING 3 GB", "selling_price": 750, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "197", "name": "Airtel GIFTING 3.2 GB", "selling_price": 850, "plan_type": "gifting", "validity": "3 DAYS"},
            {"plan_id": "198", "name": "Airtel GIFTING 4 GB", "selling_price": 2450, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "199", "name": "Airtel GIFTING 5 GB", "selling_price": 3400, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "200", "name": "Airtel GIFTING 6 GB", "selling_price": 3950, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "201", "name": "Airtel GIFTING 8 GB", "selling_price": 4400, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "202", "name": "Airtel GIFTING 10 GB", "selling_price": 4900, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "203", "name": "Airtel GIFTING 12 GB", "selling_price": 5300, "plan_type": "gifting", "validity": "| Coll 100 mins | 30 DAYS"},
            {"plan_id": "204", "name": "Airtel GIFTING 13 GB", "selling_price": 5500, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "205", "name": "Airtel GIFTING 18 GB", "selling_price": 7500, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "206", "name": "Airtel GIFTING 25 GB", "selling_price": 9500, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "207", "name": "Airtel GIFTING 35 GB", "selling_price": 11000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "208", "name": "Airtel GIFTING 60 GB", "selling_price": 15000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "209", "name": "Airtel GIFTING 100 GB", "selling_price": 20000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "210", "name": "Airtel GIFTING 160 GB", "selling_price": 30000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "211", "name": "Airtel GIFTING 210 GB", "selling_price": 40000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "212", "name": "Airtel GIFTING 300 GB", "selling_price": 50000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "213", "name": "Airtel GIFTING 350 GB", "selling_price": 60000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "214", "name": "Airtel GIFTING 650 GB", "selling_price": 100000, "plan_type": "gifting", "validity": "90 DAYS"},
        ]
    },
    # ── GLO (network id "3") ────────────────────────────────────────────
    "3": {
        "name": "Glo",
        "plans": [
            # CORPORATE
            {"plan_id": "127", "name": "Glo CORPORATE 200 MB", "selling_price": 100, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "128", "name": "Glo CORPORATE 500 MB", "selling_price": 200, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "129", "name": "Glo CORPORATE 1 GB", "selling_price": 400, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "130", "name": "Glo CORPORATE 2 GB", "selling_price": 850, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "131", "name": "Glo CORPORATE 3 GB", "selling_price": 1200, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "132", "name": "Glo CORPORATE 5 GB", "selling_price": 2000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "133", "name": "Glo CORPORATE 10 GB", "selling_price": 4000, "plan_type": "corporate", "validity": "30 DAYS"},
            # GIFTING
            {"plan_id": "134", "name": "Glo GIFTING 200 MB", "selling_price": 95, "plan_type": "gifting", "validity": "1 DAY"},
            {"plan_id": "135", "name": "Glo GIFTING 750 MB", "selling_price": 200, "plan_type": "gifting", "validity": "1 DAY"},
            {"plan_id": "136", "name": "Glo GIFTING 1 GB", "selling_price": 350, "plan_type": "gifting", "validity": "1 DAY"},
            {"plan_id": "137", "name": "Glo GIFTING 1.5 GB", "selling_price": 380, "plan_type": "gifting", "validity": "1 DAY"},
            {"plan_id": "138", "name": "Glo GIFTING 2 GB", "selling_price": 500, "plan_type": "gifting", "validity": "1 DAY"},
            {"plan_id": "139", "name": "Glo GIFTING 2.5 GB", "selling_price": 550, "plan_type": "gifting", "validity": "2 DAYS"},
            {"plan_id": "140", "name": "Glo GIFTING 5.1 GB", "selling_price": 1000, "plan_type": "gifting", "validity": "SOCIAL 2 DAYS"},
            {"plan_id": "141", "name": "Glo GIFTING 7.7 GB", "selling_price": 2500, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "142", "name": "Glo GIFTING 10 GB", "selling_price": 1950, "plan_type": "gifting", "validity": "7 DAYS"},
            {"plan_id": "143", "name": "Glo GIFTING 14 GB", "selling_price": 3900, "plan_type": "gifting", "validity": "30 DAYS"},
        ]
    },
    # ── 9mobile (network id "4") ────────────────────────────────────────
    "4": {
        "name": "9mobile",
        "plans": [
            # CORPORATE
            {"plan_id": "144", "name": "9mobile CORPORATE 300 MB", "selling_price": 100, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "145", "name": "9mobile CORPORATE 500 MB", "selling_price": 200, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "146", "name": "9mobile CORPORATE 1 GB", "selling_price": 400, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "147", "name": "9mobile CORPORATE 2 GB", "selling_price": 800, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "148", "name": "9mobile CORPORATE 3 GB", "selling_price": 1200, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "149", "name": "9mobile CORPORATE 5 GB", "selling_price": 2000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "150", "name": "9mobile CORPORATE 10 GB", "selling_price": 4000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "151", "name": "9mobile CORPORATE 15 GB", "selling_price": 6000, "plan_type": "corporate", "validity": "30 DAYS"},
            {"plan_id": "152", "name": "9mobile CORPORATE 20 GB", "selling_price": 8000, "plan_type": "corporate", "validity": "30 DAYS"},
            # GIFTING
            {"plan_id": "153", "name": "9mobile GIFTING 300 MB", "selling_price": 100, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "154", "name": "9mobile GIFTING 500 MB", "selling_price": 200, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "155", "name": "9mobile GIFTING 1 GB", "selling_price": 400, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "156", "name": "9mobile GIFTING 2 GB", "selling_price": 800, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "157", "name": "9mobile GIFTING 3 GB", "selling_price": 1200, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "158", "name": "9mobile GIFTING 5 GB", "selling_price": 2000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "159", "name": "9mobile GIFTING 10 GB", "selling_price": 4000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "160", "name": "9mobile GIFTING 15 GB", "selling_price": 6000, "plan_type": "gifting", "validity": "30 DAYS"},
            {"plan_id": "161", "name": "9mobile GIFTING 20 GB", "selling_price": 8000, "plan_type": "gifting", "validity": "30 DAYS"},
        ]
    },
}

class FlowPayProvider(BaseVTUProvider):
    """
    FlowPay implementation of BaseVTUProvider.
    """

    def __init__(self, config: Dict[str, Any]):
        self.api_token = config.get('api_key')
        url = config.get('base_url')
        if url and len(url.strip()) > 0:
            self.base_url = url.strip().rstrip('/')
        else:
            self.base_url = 'https://app.flowpay.ng'
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def provider_name(self) -> str:
        return "flowpay"

    @classmethod
    def get_supported_services(cls) -> List[str]:
        return ['airtime', 'data', 'tv', 'electricity', 'education']

    @classmethod
    def get_config_requirements(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'api_key', 
                'label': 'API Token', 
                'type': 'text', 
                'required': True,
                'help_text': 'Bearer Token from FlowPay'
            },
            {
                'name': 'base_url', 
                'label': 'Base URL', 
                'type': 'text', 
                'required': False, 
                'default': ''
            }
        ]

    def _post(self, endpoint: str, data: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=50)
            print("===========================================")
            print(f"FlowPay POST {url} - Payload: {data} - Status: {response.status_code} - Response: {response.json()}")
            print("===========================================")
            return response.json()
        except Exception as e:
            logger.error(f"FlowPay request error: {str(e)}")
            raise Exception(f"FlowPay API error: {str(e)}")

    def _get(self, endpoint: str, params: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        print(f"FlowPay GET {url} - Params: {params} - Headers: {self.headers}")
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=50)
            print("===========================================")
            print(f"FlowPay GET {url} - Params: {params} - Status: {response.status_code}")
            print("===========================================")
            return response.json()
        except Exception as e:
            logger.error(f"FlowPay GET request error: {str(e)}")
            raise Exception(f"FlowPay API error: {str(e)}")

    def buy_airtime(self, phone: str, network: str, amount: float, reference: str) -> Dict[str, Any]:
        # Database: "1" = MTN, "2" = Airtel, "3" = Glo, "4" = 9mobile
        # FlowPay API: 1 = MTN, 2 = Glo, 3 = 9mobile, 4 = Airtel
        db_to_api_map = {
            "1": 1,   # MTN -> MTN
            "2": 4,   # Airtel -> Airtel
            "3": 2,   # Glo -> Glo
            "4": 3,   # 9mobile -> 9mobile
        }
        api_network = db_to_api_map.get(str(network), 1)

        payload = {
            "mobile_number": phone,
            "amount": int(amount),
            "network": api_network,
        }
        
        res = self._post("/api/topup", payload)
        
        inner_data = res.get('data') or {}
        api_status = inner_data.get('Status') or res.get('status') or ''
        status = "SUCCESS" if str(api_status).lower() in ["success", "successful"] else "FAILED"
        
        return {
            "status": status,
            "provider_reference": inner_data.get('ident') or res.get('reference') or reference,
            "message": res.get('api_response') or res.get('message'),
            "raw_response": res
        }

    def buy_data(self, phone: str, network: str, plan_id: str, amount: float, reference: str) -> Dict[str, Any]:
        db_to_api_map = {
            "1": 1,   # MTN -> MTN
            "2": 4,   # Airtel -> Airtel
            "3": 2,   # Glo -> Glo
            "4": 3,   # 9mobile -> 9mobile
        }
        api_network = db_to_api_map.get(str(network), 1)

        payload = {
            "mobile_number": phone,
            "plan": int(plan_id),
            "network": api_network,
        }
        
        res = self._post("/api/data", payload)
        
        inner_data = res.get('data') or {}
        api_status = inner_data.get('Status') or res.get('status') or ''
        status = "SUCCESS" if str(api_status).lower() in ["success", "successful"] else "FAILED"
        
        return {
            "status": status,
            "provider_reference": inner_data.get('ident') or res.get('reference') or reference,
            "message": res.get('api_response') or res.get('message'),
            "raw_response": res
        }

    def buy_tv(self, tv_id: str, package_id: str, smart_card_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        CABLE_NAME_MAP = {"dstv": "DSTV", "gotv": "GOTV", "startime": "STARTIME", "startimes": "STARTIME"}
        cable_name = CABLE_NAME_MAP.get(str(tv_id).lower(), str(tv_id).upper())

        resolved_plan_id = self._resolve_cable_plan_id(package_id)

        payload = {
            "cable_name": cable_name,
            "cable_subscription_plan_id": resolved_plan_id,
            "smart_card_number": smart_card_number,
        }

        res = self._post("/api/cable_subscription", payload)
        
        inner_data = res.get('data') or {}
        api_status = inner_data.get('Status') or res.get('status') or ''
        status = "SUCCESS" if str(api_status).lower() in ["success", "successful"] else "FAILED"
        
        return {
            "status": status,
            "provider_reference": inner_data.get('ident') or res.get('reference') or reference,
            "message": res.get('api_response') or res.get('message'),
            "raw_response": res
        }

    def buy_electricity(self, disco_id: str, plan_id: str, meter_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        distributor_id = self._resolve_disco_id(disco_id)
        
        meter_type = str(plan_id).lower()
        if meter_type not in ["prepaid", "postpaid"]:
            meter_type = "prepaid"
            
        customer_name = kwargs.get("customer_name") or kwargs.get("name")
        if not customer_name:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_obj = User.objects.filter(phone_number=phone).first()
            if user_obj:
                customer_name = user_obj.full_name or user_obj.phone_number
            else:
                customer_name = "Customer"

        payload = {
            "meter_type": meter_type,
            "phone_number": phone,
            "name": customer_name,
            "meter_number": meter_number,
            "electricity_distributor_id": distributor_id,
            "amount": float(amount),
        }

        res = self._post("/api/electricity_bill_payments", payload)
        
        inner_data = res.get('data') or {}
        api_status = inner_data.get('status') or res.get('status') or ''
        status = "SUCCESS" if str(api_status).lower() in ["success", "successful"] else "FAILED"
        
        result = {
            "status": status,
            "provider_reference": inner_data.get('reference') or res.get('reference') or reference,
            "message": res.get('api_response') or res.get('message'),
            "raw_response": res
        }
        token = inner_data.get('token')
        if token:
            result["token"] = token
            
        return result

    def buy_internet(self, *args, **kwargs) -> Dict[str, Any]:
        return {"status": "FAILED", "message": "Internet not supported"}

    def buy_education(self, exam_type: str, variation_id: str, quantity: int, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        EXAM_NAME_MAP = {"waec": "WAEC", "neco": "NECO", "nabteb": "NABTEB"}
        exam_name = EXAM_NAME_MAP.get(str(exam_type).lower(), str(exam_type).upper())
        
        payload = {
            "exam_name": exam_name,
            "quantity": int(quantity),
        }
        
        res = self._post("/api/epin", payload)
        
        inner_data = res.get('data') or {}
        api_status = inner_data.get('Status') or res.get('status') or ''
        status = "SUCCESS" if str(api_status).lower() in ["success", "successful"] else "FAILED"
        
        return {
            "status": status,
            "provider_reference": inner_data.get('ident') or res.get('reference') or reference,
            "message": res.get('api_response') or res.get('message'),
            "raw_response": res
        }

    def query_transaction(self, reference: str) -> Dict[str, Any]:
        return {"status": "UNKNOWN", "message": "Query not implemented"}

    def cancel_transaction(self, reference: str) -> Dict[str, Any]:
        return {"status": "FAILED", "message": "Cancellation not supported"}

    def handle_webhook(self, data: Dict[str, Any]) -> bool:
        from orders.models import Purchase
        
        logger.info(f"FlowPay webhook payload: {data}")
        
        inner_data = data.get("data") or {}
        reference = inner_data.get("reference")
        
        if not reference:
            logger.warning("FlowPay Webhook: No reference in payload data.")
            return False
            
        status_val = inner_data.get("status")
        
        try:
            purchase = Purchase.objects.filter(reference=reference).first()
            if not purchase:
                logger.warning(f"FlowPay Webhook: Purchase not found for reference {reference}")
                return False
                
            purchase.provider_response = data
            
            if status_val == "successful":
                purchase.status = "success"
                purchase.save()
            elif status_val == "failed":
                purchase.status = "failed"
                purchase.save()
                from orders.utils.purchase_logic import handle_vtu_async_failure
                handle_vtu_async_failure(purchase)
            elif status_val == "refunded":
                purchase.status = "refunded"
                purchase.save()
            
            return True
        except Exception as e:
            logger.error(f"FlowPay Webhook Error: {e}")
            return False

    def handle_callback(self, data: Dict[str, Any]) -> bool:
        return self.handle_webhook(data)

    def validate_meter(self, meter_number: str, service: str) -> Dict[str, Any]:
        params = {
            "meter_number": meter_number,
            "disco_name": service,      # e.g. "ikeja-electric"
            "meter_type": "prepaid",    # default prepaid, can be overridden if needed
        }
        res = self._get("/api/validate_meter", params)
        account_name = res.get('name')
        return {
            "status": "SUCCESS" if res.get("status") == "success" and account_name else "FAILED",
            "account_name": account_name,
            "raw_response": res
        }

    def validate_cable_id(self, card_number: str, service: str) -> Dict[str, Any]:
        CABLE_NAME_MAP = {"dstv": "DSTV", "gotv": "GOTV", "startime": "STARTIME", "startimes": "STARTIME"}
        cable_name = CABLE_NAME_MAP.get(str(service).lower(), str(service).upper())
        params = {
            "smart_card_number": card_number,
            "cable_name": cable_name,
        }
        res = self._get("/api/validate_icu", params)
        account_name = res.get('name')
        return {
            "status": "SUCCESS" if res.get("status") == "success" and account_name else "FAILED",
            "account_name": account_name,
            "raw_response": res
        }

    def get_wallet_balance(self) -> float:
        return 0.0

    def get_available_services(self) -> List[Dict[str, Any]]:
        return [
            {"type": "airtime", "endpoint": "/api/topup"},
            {"type": "data", "endpoint": "/api/data"},
            {"type": "tv", "endpoint": "/api/cable_subscription"},
            {"type": "electricity", "endpoint": "/api/electricity_bill_payments"},
            {"type": "education", "endpoint": "/api/epin"},
        ]

    def sync_airtime(self) -> int:
        from orders.models import AirtimeNetwork
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.airtime_margin if config else Decimal('0.00')
        base_100 = Decimal('100.00')

        created = []
        for net_data in AIRTIME_NETWORKS_DATA:
            net, _ = AirtimeNetwork.objects.update_or_create(
                service_id=net_data["service_id"],
                provider=getattr(self, "provider_config", None),
                defaults={
                    "service_name": net_data["service_name"],
                    "min_amount": net_data["min_amount"],
                    "max_amount": net_data["max_amount"],
                    "cost_price": base_100,
                    "selling_price": base_100 + margin,
                    "agent_price": base_100,
                }
            )
            created.append(net)
        return len(created)

    def sync_data(self) -> int:
        """
        Sync data plans from FlowPay.

        Live API response shape:
            {
                "mobile_networks": [
                    {
                        "id": 1, "name": "MTN", "code": "mtn", ...
                        "plan_types": [
                            {
                                "id": 1, "name": "SME", "code": "sme", "active": 1, ...
                                "data_plans": [
                                    {
                                        "id": 82, "size": 500, "volume": "mb",
                                        "validity": "30 DAYS", "amount": "300.00", ...
                                    },
                                    ...
                                ]
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        from orders.models import DataService, DataVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.data_margin if config else Decimal('0.00')
        provider_config = getattr(self, "provider_config", None)

        # ── Network name → our internal service_id mapping ────────────────
        NETWORK_CODE_MAP = {
            "mtn":    ("1", "MTN"),
            "airtel": ("2", "Airtel"),
            "glo":    ("3", "Glo"),
            "9mobile":("4", "9mobile"),
            "etisalat":("4", "9mobile"),
        }

        try:
            res = self._get("/api/data_plans", {})

            # ── Parse nested structure ─────────────────────────────────────
            mobile_networks = None
            if isinstance(res, dict):
                mobile_networks = res.get("mobile_networks")
            elif isinstance(res, list):
                # Unexpected flat list — old path, skip to fallback
                mobile_networks = None

            if mobile_networks and isinstance(mobile_networks, list):
                created_variations = []
                services_by_db_id: Dict[str, Any] = {}

                for network in mobile_networks:
                    if not isinstance(network, dict):
                        continue

                    # Resolve network → internal service_id
                    net_code = str(network.get("code", "")).lower().strip()
                    net_name_raw = str(network.get("name", "")).lower().strip()
                    mapping = NETWORK_CODE_MAP.get(net_code) or NETWORK_CODE_MAP.get(net_name_raw)
                    if not mapping:
                        # Try partial match on name
                        for key, val in NETWORK_CODE_MAP.items():
                            if key in net_name_raw or key in net_code:
                                mapping = val
                                break
                    if not mapping:
                        logger.debug(f"FlowPay sync_data: unknown network '{network.get('name')}', skipping")
                        continue

                    db_service_id, net_name = mapping

                    # Ensure DataService exists
                    if db_service_id not in services_by_db_id:
                        service, _ = DataService.objects.update_or_create(
                            service_id=db_service_id,
                            provider=provider_config,
                            defaults={"service_name": net_name}
                        )
                        services_by_db_id[db_service_id] = service
                    service = services_by_db_id[db_service_id]

                    # Loop plan_types
                    for plan_type in network.get("plan_types", []):
                        if not isinstance(plan_type, dict):
                            continue
                        if not plan_type.get("active", 1):
                            continue  # skip inactive plan types

                        pt_name = str(plan_type.get("name", "General")).strip()   # e.g. "SME", "GIFTING"
                        pt_code = str(plan_type.get("code", pt_name)).strip().lower()  # e.g. "sme", "gifting"

                        # Loop data_plans inside this plan type
                        for plan in plan_type.get("data_plans", []):
                            if not isinstance(plan, dict):
                                continue
                            if not plan.get("active", 1):
                                continue  # skip inactive plans

                            plan_id   = str(plan.get("id", ""))
                            size      = plan.get("size", "")
                            volume    = str(plan.get("volume", "")).upper()   # "MB" / "GB"
                            validity  = str(plan.get("validity", "")).strip()
                            amount    = plan.get("amount", "0")

                            # Build a human-readable name:
                            # e.g. "MTN SME 500 MB (30 DAYS)"
                            size_str = f"{size} {volume}" if volume else str(size)
                            name = f"{net_name} {pt_name} {size_str}"
                            if validity:
                                name += f" ({validity})"

                            cost_price = Decimal(str(amount))

                            variation, _ = DataVariation.objects.update_or_create(
                                variation_id=plan_id,
                                service=service,
                                defaults={
                                    "name": name,
                                    "cost_price": cost_price,
                                    "selling_price": cost_price + margin,
                                    "agent_price": cost_price,
                                    "plan_type": pt_code,
                                    "is_active": True,
                                }
                            )
                            created_variations.append(variation)

                logger.info(f"FlowPay: synced {len(created_variations)} data variations from live API")
                if created_variations:
                    return len(created_variations)

            # No usable data from live API
            logger.warning("FlowPay sync_data: live API returned no mobile_networks, falling back to catalog")

        except Exception as e:
            logger.warning(f"FlowPay live data sync failed ({e}), falling back to catalog")

        # ── Fallback to hardcoded catalog ─────────────────────────────────
        created_variations = []
        for net_id, net_info in DATA_PLANS_BY_NETWORK.items():
            service, _ = DataService.objects.update_or_create(
                service_id=net_id,
                provider=provider_config,
                defaults={"service_name": net_info["name"]}
            )
            for plan in net_info["plans"]:
                p_amount = Decimal(str(plan["selling_price"]))
                variation, _ = DataVariation.objects.update_or_create(
                    variation_id=plan["plan_id"],
                    service=service,
                    defaults={
                        "name": plan["name"],
                        "cost_price": p_amount,
                        "selling_price": p_amount + margin,
                        "agent_price": p_amount,
                        "plan_type": plan.get("plan_type", "general"),
                        "is_active": True,
                    }
                )
                created_variations.append(variation)

        logger.info(f"FlowPay: synced {len(created_variations)} data variations from catalog")
        return len(created_variations)

    def sync_cable(self) -> int:
        from orders.models import TVService, TVVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.tv_margin if config else Decimal('0.00')
        provider_config = getattr(self, "provider_config", None)

        TV_SERVICES = {
            "dstv": {
                "name": "DSTV",
                "plans": [
                    {"name": "DStv Padi", "selling_price": 2500, "package_id": "Padi"},
                    {"name": "DStv Yanga", "selling_price": 3500, "package_id": "Yanga"},
                    {"name": "DStv Confam", "selling_price": 6200, "package_id": "Confam"},
                    {"name": "DStv Premium", "selling_price": 24500, "package_id": "Premium"},
                ]
            },
            "gotv": {
                "name": "GOTV",
                "plans": [
                    {"name": "GOtv Smallie", "selling_price": 1100, "package_id": "Smallie"},
                    {"name": "GOtv Jinja", "selling_price": 2250, "package_id": "Jinja"},
                    {"name": "GOtv Jolli", "selling_price": 3300, "package_id": "Jolli"},
                    {"name": "GOtv Max", "selling_price": 4850, "package_id": "Max"},
                ]
            },
            "startime": {
                "name": "STARTIME",
                "plans": [
                    {"name": "Startimes Nova", "selling_price": 1500, "package_id": "Nova"},
                    {"name": "Startimes Basic", "selling_price": 3000, "package_id": "Basic"},
                    {"name": "Startimes Smart", "selling_price": 4500, "package_id": "Smart"},
                    {"name": "Startimes Classic", "selling_price": 6000, "package_id": "Classic"},
                    {"name": "Startimes Super", "selling_price": 9000, "package_id": "Super"},
                ]
            }
        }

        created_variations = []
        for service_id, service_info in TV_SERVICES.items():
            service, _ = TVService.objects.get_or_create(
                service_id=service_id,
                provider=provider_config,
                defaults={"service_name": service_info["name"]}
            )
            for plan in service_info["plans"]:
                cost_price = Decimal(str(plan["selling_price"]))
                variation, _ = TVVariation.objects.update_or_create(
                    variation_id=plan["package_id"],
                    service=service,
                    defaults={
                        "name": plan["name"],
                        "cost_price": cost_price,
                        "selling_price": cost_price + margin,
                        "agent_price": cost_price,
                        "package_bouquet": plan["name"],
                        "is_active": True,
                    }
                )
                created_variations.append(variation)

        logger.info(f"FlowPay: synced {len(created_variations)} cable variations")
        return len(created_variations)

    def sync_electricity(self) -> int:
        from orders.models import ElectricityService, ElectricityVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.electricity_margin if config else Decimal('0.00')
        provider_config = getattr(self, "provider_config", None)

        DISCOS = [
            {"id": "ikeja-electric", "name": "Ikeja Electric"},
            {"id": "eko-electric", "name": "Eko Electric"},
            {"id": "abuja-electric", "name": "Abuja Electric"},
            {"id": "kano-electric", "name": "Kano Electric"},
            {"id": "enugu-electric", "name": "Enugu Electric"},
            {"id": "port-harcourt-electric", "name": "Port Harcourt Electric"},
            {"id": "ibadan-electric", "name": "Ibadan Electric"},
            {"id": "kaduna-electric", "name": "Kaduna Electric"},
            {"id": "jos-electric", "name": "Jos Electric"},
            {"id": "benin-electric", "name": "Benin Electric"},
            {"id": "yola-electric", "name": "Yola Electric"},
        ]

        created_variations = []
        for disco in DISCOS:
            service, _ = ElectricityService.objects.get_or_create(
                service_id=disco["id"],
                provider=provider_config,
                defaults={"service_name": disco["name"]}
            )
            for v_type in ["prepaid", "postpaid"]:
                variation, _ = ElectricityVariation.objects.update_or_create(
                    variation_id=v_type,
                    service=service,
                    defaults={
                        "name": f"{disco['name']} {v_type.capitalize()}",
                        "min_amount": "1000",
                        "max_amount": "200000",
                        "discount": "0",
                        "cost_price": Decimal('0.00'),
                        "selling_price": Decimal('0.00'),
                        "agent_price": Decimal('0.00'),
                        "is_active": True,
                    }
                )
                created_variations.append(variation)

        logger.info(f"FlowPay: synced {len(created_variations)} electricity variations")
        return len(created_variations)

    def sync_internet(self) -> int:
        return 0

    def sync_education(self) -> int:
        from orders.models import EducationService, EducationVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.education_margin if config else Decimal('0.00')
        provider_config = getattr(self, "provider_config", None)

        EXAMS = [
            {"id": "waec", "name": "WAEC Pin", "cost_price": 1000, "variation_id": "WAEC"},
            {"id": "neco", "name": "NECO Pin", "cost_price": 500, "variation_id": "NECO"},
            {"id": "nabteb", "name": "NABTEB Pin", "cost_price": 800, "variation_id": "NABTEB"},
        ]

        created_variations = []
        for exam in EXAMS:
            service, _ = EducationService.objects.get_or_create(
                service_id=exam["id"],
                provider=provider_config,
                defaults={"service_name": exam["id"].upper()}
            )
            cost_price = Decimal(str(exam["cost_price"]))
            variation, _ = EducationVariation.objects.update_or_create(
                variation_id=exam["variation_id"],
                service=service,
                defaults={
                    "name": exam["name"],
                    "cost_price": cost_price,
                    "selling_price": cost_price + margin,
                    "agent_price": cost_price,
                    "is_active": True,
                }
            )
            created_variations.append(variation)

        logger.info(f"FlowPay: synced {len(created_variations)} education variations")
        return len(created_variations)

    def _resolve_cable_plan_id(self, package_id: str) -> int:
        try:
            return int(package_id)
        except ValueError:
            name_map = {
                "smallie": 1,
                "jinja": 2,
                "jolli": 3,
                "max": 4,
                "padi": 5,
                "yanga": 6,
                "confam": 5,  # example in docs used 5
                "premium": 8,
                "nova": 21,
                "basic": 22,
                "smart": 23,
                "classic": 24,
                "super": 25,
            }
            val = str(package_id).strip().lower()
            for k, v in name_map.items():
                if k in val:
                    return v
            return 1

    def _resolve_disco_id(self, disco_id: str) -> int:
        DISCO_ID_MAP = {
            "ikeja-electric": 1,
            "eko-electric": 2,
            "abuja-electric": 3,
            "kano-electric": 4,
            "enugu-electric": 5,
            "port-harcourt-electric": 6,
            "ibadan-electric": 7,
            "kaduna-electric": 8,
            "jos-electric": 9,
            "benin-electric": 10,
            "yola-electric": 11,
        }
        normalized = str(disco_id).lower().replace(" ", "-").replace("_", "-")
        if "ikeja" in normalized:
            return 1
        elif "eko" in normalized:
            return 2
        elif "abuja" in normalized or "aedc" in normalized:
            return 3
        elif "kano" in normalized or "kedco" in normalized:
            return 4
        elif "enugu" in normalized or "eedc" in normalized:
            return 5
        elif "port" in normalized or "ph" in normalized:
            return 6
        elif "ibadan" in normalized or "ibedc" in normalized:
            return 7
        elif "kaduna" in normalized:
            return 8
        elif "jos" in normalized or "jed" in normalized:
            return 9
        elif "benin" in normalized or "bedc" in normalized:
            return 10
        elif "yola" in normalized:
            return 11
        return DISCO_ID_MAP.get(normalized, 1)
