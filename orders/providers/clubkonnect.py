import requests
import json
import logging
from typing import Dict, Any, Optional, List
from ..interfaces import BaseVTUProvider
from django.conf import settings

logger = logging.getLogger(__name__)

class ClubKonnectProvider(BaseVTUProvider):
    """
    ClubKonnect implementation of BaseVTUProvider.
    """

    def __init__(self, config: Dict[str, Any]):
        self.user_id = config.get('user_id')
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')
        if self.base_url is None or self.base_url == '':
            self.base_url = 'https://www.nellobytesystems.com'
            
        self.headers = {
            "Content-Type": "application/json",
        }

    @property
    def provider_name(self) -> str:
        return "clubkonnect"

    @classmethod
    def get_supported_services(cls) -> List[str]:
        return ["airtime", "data", "tv", "electricity", "education", "internet"]

    @classmethod
    def get_config_requirements(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "user_id", "label": "User ID", "type": "text", "required": True},
            {"name": "api_key", "label": "API Key", "type": "text", "required": True},
            {"name": "base_url", "label": "Base URL", "type": "text", "required": False, "default": "https://www.nellobytesystems.com"},
        ]

    def _get(self, endpoint: str, params: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        params.update({"UserID": self.user_id, "APIKey": self.api_key})
        try:
            timeout = getattr(settings, "CLUBKONNECT_TIMEOUT", 30)
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"ClubKonnect request error: {str(e)}")
            raise Exception(f"ClubKonnect API error: {str(e)}")

    def buy_airtime(self, phone: str, network: str, amount: float, reference: str) -> Dict[str, Any]:
        # network map for ClubKonnect
        network_map = {'mtn': '01', 'glo': '02', 'airtel': '03', '9mobile': '04'}
        service_id = network_map.get(network.lower(), '01')
        
        params = {
            "MobileNetwork": service_id,
            "Amount": int(amount),
            "MobileNumber": phone,
            # "RequestID": reference
        }
        endpoint = "/APIAirtimeV1.asp" 
        res = self._get(endpoint, params)

        print(res)
        
        status = "PENDING"
        if res.get('status') in ['ORDER_COMPLETED', 'ORDER_RECEIVED'] or res.get('statuscode') == '100':
            status = "SUCCESS"
        elif res.get('status') in ['ORDER_FAILED', 'ORDER_CANCELLED']:
            status = "FAILED"
            
        return {
            "status": status,
            "provider_reference": res.get('orderid'),
            "message": res.get('remark'),
            "raw_response": res
        }

    def buy_data(self, phone: str, network: str, plan_id: str, amount: float, reference: str) -> Dict[str, Any]:
        network_map = {'mtn': '01', 'glo': '02', 'airtel': '03', '9mobile': '04'}
        service_id = network_map.get(network.lower(), '01')
        # data

        params = {
            "MobileNetwork": service_id,
            "DataPlan": plan_id,
            "MobileNumber": phone,
            "RequestID": reference
        }

        endpoint = settings.CLUBKONNECT_ENDPOINTS.get("buy_data", "/APIDatabundleV1.asp")
        res = self._get(endpoint, params)
        
        status = "PENDING"
        if res.get('status') in [
            'ORDER_COMPLETED',  
            'ORDER_RECEIVED',
            'ORDER_PROCESSED',
            ] or res.get('statuscode') == '100':
            status = "SUCCESS"
        else:
            status = "FAILED"
            
        return {
            "status": status,
            "provider_reference": res.get('orderid'),
            "message": res.get('remark'),
            "raw_response": res
        }

    def buy_tv(self, tv_id: str, package_id: str, smart_card_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        params = {
            "MobileNumber": phone,
            "Amount": int(amount),
            "RequestID": reference,
            "CableTV": tv_id,
            "Package": package_id,
            "SmartCardNo": smart_card_number
        }
        endpoint = settings.CLUBKONNECT_ENDPOINTS.get("buy_cable", "/CableTV.asp")
        res = self._get(endpoint, params)
        
        status = "PENDING"
        if res.get('status') in ['ORDER_COMPLETED', 'ORDER_RECEIVED'] or res.get('statuscode') == '100':
            status = "SUCCESS"
        elif res.get('status') in ['ORDER_FAILED', 'ORDER_CANCELLED']:
            status = "FAILED"
            
        return {
            "status": status,
            "provider_reference": res.get('orderid'),
            "message": res.get('remark'),
            "raw_response": res
        }

    def buy_electricity(self, disco_id: str, plan_id: str, meter_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        params = {
            "MobileNumber": phone,
            "Amount": int(amount),
            "RequestID": reference,
            "ElectricCompany": disco_id,
            "MeterNo": meter_number,
            "MeterType": "01" # PREPAID
        }
        endpoint = settings.CLUBKONNECT_ENDPOINTS.get("buy_electricity", "/Electricity.asp")
        res = self._get(endpoint, params)
        
        status = "PENDING"
        if res.get('status') in ['ORDER_COMPLETED', 'ORDER_RECEIVED'] or res.get('statuscode') == '100':
            status = "SUCCESS"
        elif res.get('status') in ['ORDER_FAILED', 'ORDER_CANCELLED']:
            status = "FAILED"
            
        return {
            "status": status,
            "provider_reference": res.get('orderid'),
            "message": res.get('remark'),
            "raw_response": res
        }

    def buy_internet(self, plan_id: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        variation = kwargs.get('internet_variation')
        network_id = variation.service.service_id if variation else "smile-direct"
        
        params = {
            "MobileNetwork": network_id,
            "DataPlan": plan_id,
            "MobileNumber": phone,
            "RequestID": reference
        }
        
        # Determine endpoint based on network
        if "smile" in network_id.lower():
            endpoint = "/APISmileV1.asp"
        elif "spectranet" in network_id.lower():
            endpoint = "/APISpectranetV1.asp"
        else:
            endpoint = "/APISmileV1.asp" # default

        res = self._get(endpoint, params)
        
        status = "PENDING"
        if res.get('status') in ['ORDER_COMPLETED', 'ORDER_RECEIVED'] or res.get('statuscode') in ['200', '100']:
            status = "SUCCESS"
        elif res.get('status') in ['ORDER_FAILED', 'ORDER_CANCELLED'] or res.get('statuscode') == '400':
            status = "FAILED"
            
        return {
            "status": status,
            "provider_reference": res.get('orderid'),
            "message": res.get('remark') or res.get('status'),
            "raw_response": res
        }

    def buy_education(self, exam_type: str, variation_id: str, quantity: int, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        phone = kwargs.get('beneficiary') or kwargs.get('phone') or kwargs.get('PhoneNo')
        if not phone or phone == "N/A":
             # Fallback to user phone if not provided for education
             phone = getattr(self, 'user_phone', '08000000000') 

        params = {
            "ExamType": variation_id,
            "PhoneNo": phone,
            "RequestID": reference
        }
        
        # Determine endpoint based on exam_type (service_id)
        if exam_type.lower() == 'waec':
            endpoint = "/APIWAECV1.asp"
        elif exam_type.lower() == 'jamb':
            endpoint = "/APIJAMBV1.asp"
        else:
            # Fallback to generic if any other exists, though docs only showed WAEC/JAMB
            endpoint = "/APIWAECV1.asp" if 'waec' in exam_type.lower() else "/APIJAMBV1.asp"

        res = self._get(endpoint, params)
        
        status = "PENDING"
        if res.get('status') in ['ORDER_COMPLETED', 'ORDER_RECEIVED'] or res.get('statuscode') in ['200', '100']:
            status = "SUCCESS"
        elif res.get('status') in ['ORDER_FAILED', 'ORDER_CANCELLED'] or res.get('statuscode') == '400':
            status = "FAILED"
            
        return {
            "status": status,
            "provider_reference": res.get('orderid'),
            "message": res.get('remark') or res.get('status'),
            "token": res.get('carddetails') or res.get('pin'),
            "raw_response": res
        }

    def query_transaction(self, reference: str) -> Dict[str, Any]:
        endpoint = settings.CLUBKONNECT_ENDPOINTS.get("query", "/Query.asp")
        res = self._get(endpoint, {"RequestID": reference})
        
        status = "PENDING"
        if res.get('status') in ['ORDER_COMPLETED', 'ORDER_RECEIVED'] or res.get('statuscode') in ['200', '100']:
            status = "SUCCESS"
        elif res.get('status') in ['ORDER_FAILED', 'ORDER_CANCELLED'] or res.get('statuscode') == '400':
            status = "FAILED"
            
        return {
            "status": status,
            "raw_response": res
        }

    def cancel_transaction(self, reference: str) -> Dict[str, Any]:
        endpoint = settings.CLUBKONNECT_ENDPOINTS.get("cancel", "/Cancel.asp")
        res = self._get(endpoint, {"RequestID": reference})
        return {
            "status": "CANCELLED" if res.get('statuscode') == '200' else "FAILED",
            "raw_response": res
        }

    def handle_webhook(self, data: Dict[str, Any]) -> bool:
        """Processes ClubKonnect webhook notifications."""
        return self._process_async_feedback(data)

    def handle_callback(self, data: Dict[str, Any]) -> bool:
        """Processes ClubKonnect callback notifications."""
        return self._process_async_feedback(data)

    def _process_async_feedback(self, data: Dict[str, Any]) -> bool:
        """Unified processing for ClubKonnect async feedback."""
        from orders.models import Purchase
        
        order_id = data.get("orderid") or data.get("OrderID")
        request_id = data.get("requestid") or data.get("RequestID")
        status_code = data.get("statuscode") or data.get("StatusCode") or data.get("Status")
        
        logger.info(f"ClubKonnect Async Feedback: order_id={order_id}, request_id={request_id}, status={status_code}")

        try:
            purchase = Purchase.objects.filter(reference__in=[order_id, request_id]).first()
            if not purchase:
                logger.warning(f"ClubKonnect Feedback: Purchase not found for reference {order_id or request_id}")
                return False

            purchase.provider_response = data
            
            if status_code in ["200", "delivered", "Success", "100", "ORDER_RECEIVED"]:
                purchase.status = "success"
                purchase.save()
            elif status_code in ["101", "102", "pending", "Pending"]:
                # Keep as pending
                pass
            else:
                self._handle_async_failure(purchase, f"ClubKonnect reported failure: {status_code}")

            return True
        except Exception as e:
            logger.error(f"ClubKonnect Feedback Error: {e}")
            return False

    def _handle_async_failure(self, purchase, error_msg):
        """Internal failure handling delegating to common logic."""
        purchase.last_error = error_msg
        purchase.save()
        
        # 1. Attempt Cancellation
        try:
            cancel_res = self.cancel_transaction(purchase.reference)
            if purchase.provider_response is None:
                purchase.provider_response = {}
            purchase.provider_response["cancel_request_response"] = cancel_res
            purchase.save()
        except Exception as e:
            logger.error(f"ClubKonnect Cancellation Failed: {e}")
            
        # 2. Trigger Refund/Fallback
        from orders.utils.purchase_logic import handle_vtu_async_failure
        handle_vtu_async_failure(purchase)

    def validate_meter(self, meter_number: str, service: str) -> Dict[str, Any]:
        params = {"ElectricCompany": service, "MeterNo": meter_number}
        res = self._get("/ElectricityVerify.asp", params)
        account_name = res.get('customername')
        return {
            "status": "SUCCESS" if account_name else "FAILED",
            "account_name": account_name,
            "raw_response": res
        }

    def validate_cable_id(self, card_number: str, service: str) -> Dict[str, Any]:
        params = {"CableTV": service, "SmartCardNo": card_number}
        res = self._get("/CableTVVerify.asp", params)
        account_name = res.get('customername')
        return {
            "status": "SUCCESS" if account_name else "FAILED",
            "account_name": account_name,
            "raw_response": res
        }

    def get_wallet_balance(self) -> float:
        res = self._get("/APIWalletBalanceV1.asp", {})
        return res.get('balance', 0)

    def get_available_services(self) -> List[Dict[str, Any]]:
        """
        Returns a list of available services, networks, and variations from ClubKonnect.
        """
        return [
            {"type": "airtime", "endpoint": "/AirtimeNetworks.asp"},
            {"type": "data", "endpoint": "/DataPlans.asp"},
            {"type": "cable", "endpoint": "/CableTVPackages.asp"},
            {"type": "electricity", "endpoint": "/ElectricityCompanies.asp"},
            {"type": "internet", "endpoint": "/SmilePackages.asp"},
            {"type": "education", "endpoint": "/EducationPackages.asp"},
        ]
    
    def sync_airtime(self) -> int:
        res = self._get("/APIAirtimeDiscountV2.asp", {})
        networks = res.get("MOBILE_NETWORK") or {}
        created_networks = []
        for network_name, product_list in networks.items():
            if not product_list: continue
            created_networks.extend(self._deserialize_airtime(network_name, product_list))
        if created_networks:
            from orders.utils.sync_runner import deactivate_unreturned_items
            deactivate_unreturned_items(getattr(self, "provider_config", None) or "clubkonnect", 'airtime', synced_pks=[n.pk for n in created_networks])
        return len(created_networks)

    def _deserialize_airtime(self, network_name: str, product_list: List[Dict]) -> List[Any]:
        from orders.models import AirtimeNetwork
        created = []
        provider_config = getattr(self, "provider_config", None)
        created = []
        for product in product_list:
            discount = product.get("PRODUCT_DISCOUNT", "0")
            if isinstance(discount, str):
                discount = discount.replace("%", "").strip()
            
            from summary.models import SiteConfig
            from decimal import Decimal
            config = SiteConfig.objects.first()
            margin = config.airtime_margin if config else Decimal('0.00')
            
            # For airtime, we'll store prices relative to 100 Naira face value for consistency
            base_100 = Decimal('100.00')
            p_discount = Decimal(str(discount))
            
            net, _ = AirtimeNetwork.objects.update_or_create(
                service_id=product.get("ID"),
                provider=provider_config,
                defaults={
                    "service_name": product.get("PRODUCT_NAME", network_name).capitalize(),
                    "min_amount": product.get("MINAMOUNT", "50"),
                    "max_amount": product.get("MAXAMOUNT", "200000"),
                    "discount": str(p_discount),
                    "cost_price": base_100 - (base_100 * p_discount / 100),
                    "selling_price": base_100 + margin,
                    "agent_price": base_100, # Agents get it at face value
                }
            )
            created.append(net)
        return created

    def sync_data(self) -> int:
        params = {}
        res = self._get("/APIDatabundlePlansV2.asp", params)
        networks = res.get("MOBILE_NETWORK") or {}
        created_variations = []
        for network_name, network_list in networks.items():
            if not network_list: continue
            created_variations.extend(self._deserialize_data(network_name, network_list))
        if created_variations:
            from orders.utils.sync_runner import deactivate_unreturned_items
            deactivate_unreturned_items(getattr(self, "provider_config", None) or "clubkonnect", 'data', synced_pks=[v.pk for v in created_variations])
        return len(created_variations)

    def _deserialize_data(self, network_name: str, network_list: List[Dict]) -> List[Any]:
        from orders.models import DataService, DataVariation
        provider_config = getattr(self, "provider_config", None)
        created = []
        net_info = network_list[0]
        service_id = net_info.get("ID")
        products = net_info.get("PRODUCT", [])
        service, _ = DataService.objects.get_or_create(
            service_id=service_id,
            provider=provider_config,
            defaults={"service_name": network_name}
        )
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.data_margin if config else Decimal('0.00')
        
        for product in products:
            p_amount = Decimal(str(product.get("PRODUCT_AMOUNT") or 0)) or Decimal(str(product.get("selling_price") or 0))
            p_discount = Decimal(str(product.get("DISCOUNT") or product.get("PRODUCT_DISCOUNT") or 0))
            
            variation, _ = DataVariation.objects.update_or_create(
                variation_id=product.get("PRODUCT_ID"),
                service=service,
                defaults={
                    "name": product.get("PRODUCT_NAME", "Data Plan"),
                    "cost_price": p_amount - p_discount,
                    "selling_price": p_amount + margin,
                    "agent_price": p_amount,
                    "is_active": True
                }
            )
            created.append(variation)
        return created

    def sync_cable(self) -> int:
        params = {}
        res = self._get("/APICableTVPackagesV2.asp", params)
        networks = res.get("MOBILE_NETWORK") or res.get("TV_ID") or res.get("CABLETV") or {}
        created_variations = []
        for network_name, network_list in networks.items():
            if not network_list: continue
            created_variations.extend(self._deserialize_tv(network_name, network_list))
        if created_variations:
            from orders.utils.sync_runner import deactivate_unreturned_items
            deactivate_unreturned_items(getattr(self, "provider_config", None) or "clubkonnect", 'tv', synced_pks=[v.pk for v in created_variations])
        return len(created_variations)

    def _deserialize_tv(self, network_name: str, network_list: List[Dict]) -> List[Any]:
        from orders.models import TVService, TVVariation
        provider_config = getattr(self, "provider_config", None)
        created = []
        net_info = network_list[0]
        s_id = net_info.get("ID") or network_name.lower().replace(" ", "-")
        products = net_info.get("PRODUCT") or net_info.get("PACKAGE") or []
        service, _ = TVService.objects.get_or_create(
            service_id=s_id,
            provider=provider_config,
            defaults={"service_name": network_name}
        )
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.tv_margin if config else Decimal('0.00')
        
        for product in products:
            p_amount = Decimal(str(product.get("PACKAGE_AMOUNT") or product.get("PRODUCT_AMOUNT") or 0))
            p_discount = Decimal(str(product.get("DISCOUNT") or product.get("PACKAGE_DISCOUNT") or 0))
            
            variation, _ = TVVariation.objects.update_or_create(
                variation_id=product.get("PACKAGE_ID") or product.get("PRODUCT_ID"),
                service=service,
                defaults={
                    "name": product.get("PACKAGE_NAME") or product.get("PRODUCT_NAME") or "TV Package",
                    "cost_price": p_amount - p_discount,
                    "selling_price": p_amount + margin,
                    "agent_price": p_amount,
                    "package_bouquet": product.get("PACKAGE_NAME") or product.get("PRODUCT_NAME"),
                    "is_active": True
                }
            )
            created.append(variation)
        return created

    def sync_electricity(self) -> int:
        res = self._get("/APIElectricityDiscosV2.asp", {})
        companies = res.get("ELECTRIC_COMPANY") or res.get("ELECTRICCOMPANIES") or {}
        created_variations = []
        for name, company_infos in companies.items():
            if not company_infos: continue
            created_variations.extend(self._deserialize_electricity(name, company_infos))
        return len(created_variations)

    def _deserialize_electricity(self, name: str, company_infos: List[Dict]) -> List[Any]:
        from orders.models import ElectricityService, ElectricityVariation
        provider_config = getattr(self, "provider_config", None)
        created = []
        for company_info in company_infos:
            service, _ = ElectricityService.objects.get_or_create(
                service_id=company_info.get('ID') or name.lower().replace("_", "-").replace(" ", "-"),
                provider=provider_config,
                defaults={"service_name": company_info.get("NAME") or name.replace("_", " ").title()}
            )
            for product in company_info.get("PRODUCT", []):
                from summary.models import SiteConfig
                from decimal import Decimal
                config = SiteConfig.objects.first()
                margin = config.electricity_margin if config else Decimal('0.00')

                # electricity usually doesn't have a fixed amount in response here, but if it does:
                p_amount = Decimal(str(product.get("PRODUCT_AMOUNT") or 0))
                p_discount = Decimal(str(product.get("PRODUCT_DISCOUNT_AMOUNT") or 0)) if product.get("PRODUCT_DISCOUNT_AMOUNT") else Decimal('0')
                
                variation, _ = ElectricityVariation.objects.update_or_create(
                    variation_id=product.get("PRODUCT_ID"),
                    service=service,
                    defaults={
                        "name": product.get("PRODUCT_TYPE", "General").capitalize(),
                        "min_amount": product.get("MINAMOUNT", "1000"),
                        "max_amount": product.get("MAXAMOUNT", "200000"),
                        "discount": str(p_discount),
                        "cost_price": p_amount - p_discount if p_amount > 0 else 0,
                        "selling_price": p_amount + margin if p_amount > 0 else 0,
                        "agent_price": p_amount if p_amount > 0 else 0,
                        "is_active": True
                    }
                )
                created.append(variation)
        return created

    def sync_internet(self) -> int:
        count = 0
        # 1. Sync Smile
        try:
            res_smile = self._get("/APISmilePackagesV2.asp", {})
            count += self._process_internet_res(res_smile, "Smile", "smile-direct")
        except Exception as e:
            logger.error(f"ClubKonnect Smile Sync error: {e}")

        # 2. Sync Spectranet
        try:
            res_spectranet = self._get("/APISpectranetPackagesV2.asp", {})
            count += self._process_internet_res(res_spectranet, "Spectranet", "spectranet")
        except Exception as e:
            logger.error(f"ClubKonnect Spectranet Sync error: {e}")
            
        return count

    def _process_internet_res(self, res: dict, service_name: str, service_id: str) -> int:
        from orders.models import InternetService, InternetVariation
        
        variations_list = []
        if isinstance(res, list):
            variations_list = res
        elif isinstance(res, dict):
            # Try common top-level keys
            raw_data = res.get("MOBILE_NETWORK") or res.get("INTERNET") or res.get("PACKAGE") or res
            if isinstance(raw_data, list):
                variations_list = raw_data
            elif isinstance(raw_data, dict):
                for val in raw_data.values():
                    if isinstance(val, list):
                        variations_list = val
                        break
                        
        provider_config = getattr(self, "provider_config", None)
        service, _ = InternetService.objects.get_or_create(
            service_id=service_id,
            provider=provider_config,
            defaults={"service_name": service_name}
        )
        
        synced_count = 0
        for item in variations_list:
            if isinstance(item, dict) and "PRODUCT" in item:
                for product in item["PRODUCT"]:
                    synced_count += self._create_internet_variation(service, product)
            else:
                synced_count += self._create_internet_variation(service, item)
                
        return synced_count

    def _create_internet_variation(self, service: Any, item: Dict) -> int:
        from orders.models import InternetVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        if not isinstance(item, dict): return 0
        
        config = SiteConfig.objects.first()
        margin = config.internet_margin if config else Decimal('0.00')
        
        v_id = item.get("ID") or item.get("PRODUCT_ID") or item.get("PACKAGE_ID")
        v_name = item.get("NAME") or item.get("PRODUCT_NAME") or item.get("PACKAGE_NAME")
        v_amount = Decimal(str(item.get("AMOUNT") or item.get("PRODUCT_AMOUNT") or item.get("PACKAGE_AMOUNT") or 0))
        v_discount = Decimal(str(item.get("DISCOUNT") or item.get("PRODUCT_DISCOUNT") or 0))
        
        if not v_id: return 0
        
        InternetVariation.objects.update_or_create(
            variation_id=v_id,
            service=service,
            defaults={
                "name": v_name,
                "cost_price": v_amount - v_discount,
                "selling_price": v_amount + margin,
                "agent_price": v_amount,
                "is_active": True
            }
        )
        return 1

    def sync_education(self) -> int:
        count = 0
        # 1. Sync WAEC
        try:
            res_waec = self._get("/APIWAECPackagesV2.asp", {})
            count += self._process_edu_res(res_waec, "WAEC", "waec")
        except Exception as e:
            logger.error(f"ClubKonnect WAEC Sync error: {e}")

        # 2. Sync JAMB
        try:
            res_jamb = self._get("/APIJAMBPackagesV2.asp", {})
            count += self._process_edu_res(res_jamb, "JAMB", "jamb")
        except Exception as e:
            logger.error(f"ClubKonnect JAMB Sync error: {e}")
            
        return count

    def _process_edu_res(self, res: dict, service_name: str, service_id: str) -> int:
        from orders.models import EducationService, EducationVariation
        
        # ClubKonnect responses can have nested structures.
        # We try to extract the list of products/variations.
        variations_list = []
        if isinstance(res, list):
            variations_list = res
        elif isinstance(res, dict):
            # Try common top-level keys
            raw_data = res.get("EXAM_TYPE") or res.get("MOBILE_NETWORK") or res.get("EDUCATION") or res.get("VAR") or res.get("PACKAGE") or res
            if isinstance(raw_data, list):
                variations_list = raw_data
            elif isinstance(raw_data, dict):
                # If it's a dict, it might be { "WAEC": [...] }
                for val in raw_data.values():
                    if isinstance(val, list):
                        variations_list = val
                        break
                        
        if not variations_list and isinstance(res, dict):
             # Search deeply for lists if not found
             for k, v in res.items():
                 if isinstance(v, list):
                     variations_list = v
                     break

        provider_config = getattr(self, "provider_config", None)
        service, _ = EducationService.objects.get_or_create(
            service_id=service_id,
            provider=provider_config,
            defaults={"service_name": service_name}
        )
        
        synced_count = 0
        for item in variations_list:
            # Check for nested PRODUCT list (common in ClubKonnect V2)
            if isinstance(item, dict) and "PRODUCT" in item:
                for product in item["PRODUCT"]:
                    synced_count += self._create_edu_variation(service, product)
            else:
                synced_count += self._create_edu_variation(service, item)
                
        return synced_count

    def _create_edu_variation(self, service: Any, item: Dict) -> int:
        from orders.models import EducationVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        if not isinstance(item, dict): return 0
        
        config = SiteConfig.objects.first()
        margin = config.education_margin if config else Decimal('0.00')
        
        v_id = item.get("PRODUCT_CODE") or item.get("ID") or item.get("PRODUCT_ID") or item.get("PACKAGE_ID") or item.get("exam_code")
        v_name = item.get("PRODUCT_DESCRIPTION") or item.get("NAME") or item.get("PRODUCT_NAME") or item.get("PACKAGE_NAME")
        v_amount = Decimal(str(item.get("PRODUCT_AMOUNT") or item.get("AMOUNT") or item.get("PACKAGE_AMOUNT") or 0))
        v_discount = Decimal(str(item.get("DISCOUNT") or item.get("PRODUCT_DISCOUNT") or 0))
        
        if not v_id: return 0
        
        EducationVariation.objects.update_or_create(
            variation_id=v_id,
            service=service,
            defaults={
                "name": v_name or f"{service.service_name} PIN",
                "cost_price": v_amount - v_discount,
                "selling_price": v_amount + margin,
                "agent_price": v_amount,
                "is_active": True
            }
        )
        return 1
