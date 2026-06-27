from django.db import transaction as db_transaction
from django.db import models as dj_models
from datetime import date, datetime
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import logging

from wallet.utils import debit_wallet, fund_wallet
from wallet.models import Wallet
from orders.models import (
    Purchase, PromoCode, PurchasePromoUsed, VTUProviderConfig,
    DataService, AirtimeNetwork, ElectricityService, TVService, InternetService, EducationService, ServiceRouting, ServiceFallback
)
from orders.router import ProviderRouter
from notifications.utils import NotificationService
import uuid
import requests
import json
import hmac
import hashlib
from threading import Thread

logger = logging.getLogger(__name__)


def _log_provider_response(purchase_type: str, reference: str, user_id, res: dict):
    """Log the full raw provider response whenever a purchase fails."""
    if res.get('status') not in ('SUCCESS', 'ORDER_RECEIVED'):
        logger.error(
            "Provider FAILED response | type=%s ref=%s user=%s provider=%s status=%s "
            "message=%r raw=%s",
            purchase_type,
            reference,
            user_id,
            res.get('provider_used', 'unknown'),
            res.get('status'),
            res.get('message') or res.get('error'),
            res,
        )


def dispatch_developer_webhook(purchase_obj):
    """
    Sends a webhook notification to the developer's registered URL.
    Runs in a background thread to avoid blocking the purchase flow.
    """
    try:
        profile = getattr(purchase_obj.user, 'developer_profile', None)
        if not profile or not profile.webhook_url:
            return

        payload = {
            "event": "transaction.updated",
            "data": {
                "reference": purchase_obj.reference,
                "status": purchase_obj.status,
                "amount": float(purchase_obj.amount),
                "beneficiary": purchase_obj.beneficiary,
                "type": purchase_obj.purchase_type,
                "timestamp": str(purchase_obj.time),
                "remarks": purchase_obj.remarks
            }
        }

        # Calculate signature
        secret = profile.webhook_secret.encode('utf-8')
        signature = hmac.new(
            secret,
            json.dumps(payload, separators=(',', ':')).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        def send_request():
            try:
                requests.post(
                    profile.webhook_url,
                    json=payload,
                    headers={'X-Starboy-Signature': signature},
                    timeout=10
                )
            except Exception as e:
                logger.error(f"Webhook dispatch failed for {purchase_obj.reference}: {e}")

        # Dispatch async
        Thread(target=send_request).start()

    except Exception as e:
        logger.error(f"Error preparing webhook for {purchase_obj.reference}: {e}")

def _service_enabled(purchase_type: str) -> bool:
    try:
        from summary.models import SiteConfig
        config = SiteConfig.objects.first()
        if not config:
            return True
        field_map = {
            "airtime": "airtime_active",
            "data": "data_active",
            "tv": "tv_active",
            "electricity": "electricity_active",
            "education": "education_active",
            # internet has no explicit flag; default to enabled
        }
        field = field_map.get(purchase_type)
        return getattr(config, field, True) if field else True
    except Exception:
        return True

def _validate_service_and_plan(purchase_type: str, kwargs: dict):
    if purchase_type == "airtime":
        network = kwargs.get("airtime_service")
        if not network:
            return "Airtime service not found."
        if not getattr(network, "is_active", True):
            return "Airtime service is inactive."
        return None

    if purchase_type == "data":
        plan = kwargs.get("data_variation")
        if not plan:
            return "Data plan not found."
        if not getattr(plan, "is_active", True):
            return "Data plan is inactive."
        service = getattr(plan, "service", None)
        if service and not getattr(service, "is_active", True):
            return "Data service is inactive."
        return None

    if purchase_type == "tv":
        variation = kwargs.get("tv_variation")
        if not variation:
            return "TV package not found."
        if not getattr(variation, "is_active", True):
            return "TV package is inactive."
        service = getattr(variation, "service", None)
        if service and not getattr(service, "is_active", True):
            return "TV service is inactive."
        return None

    if purchase_type == "electricity":
        variation = kwargs.get("electricity_variation")
        service = kwargs.get("electricity_service")
        if not variation:
            return "Electricity plan not found."
        if not getattr(variation, "is_active", True):
            return "Electricity plan is inactive."
        if service and not getattr(service, "is_active", True):
            return "Electricity service is inactive."
        return None

    if purchase_type == "internet":
        variation = kwargs.get("internet_variation")
        if not variation:
            return "Internet plan not found."
        if not getattr(variation, "is_active", True):
            return "Internet plan is inactive."
        service = getattr(variation, "service", None)
        if service and not getattr(service, "is_active", True):
            return "Internet service is inactive."
        return None

    if purchase_type == "education":
        variation = kwargs.get("education_variation")
        if not variation:
            return "Education plan not found."
        if not getattr(variation, "is_active", True):
            return "Education plan is inactive."
        service = getattr(variation, "service", None)
        if service and not getattr(service, "is_active", True):
            return "Education service is inactive."
        return None

    return None

def _resolve_role_amount(user, purchase_type, amount, kwargs):
    role = getattr(user, "role", "customer")
    if purchase_type == "data" and kwargs.get("data_variation"):
        plan = kwargs["data_variation"]
        return plan.agent_price if role == "agent" else plan.selling_price
    if purchase_type == "tv" and kwargs.get("tv_variation"):
        plan = kwargs["tv_variation"]
        return plan.agent_price if role == "agent" else plan.selling_price
    if purchase_type == "internet" and kwargs.get("internet_variation"):
        plan = kwargs["internet_variation"]
        return plan.agent_price if role == "agent" else plan.selling_price
    if purchase_type == "education" and kwargs.get("education_variation"):
        plan = kwargs["education_variation"]
        return plan.agent_price if role == "agent" else plan.selling_price
    return amount

def _build_provider_call_kwargs(purchase_type: str, amount, beneficiary: str, reference: str, kwargs: dict, user):
    phone = kwargs.get("phone") or beneficiary or getattr(user, "phone_number", None)

    if purchase_type == "airtime":
        network = kwargs.get("network")
        if not network and kwargs.get("airtime_service"):
            network = kwargs["airtime_service"].service_id
        return {
            "phone": phone,
            "network": network,
            "amount": amount,
            "reference": reference,
        }

    if purchase_type == "data":
        network = kwargs.get("network")
        plan_id = kwargs.get("plan_id")
        if kwargs.get("data_variation"):
            plan = kwargs["data_variation"]
            if not network:
                network = plan.service.service_id
            if not plan_id:
                plan_id = plan.variation_id
        return {
            "phone": phone,
            "network": network,
            "plan_id": plan_id,
            "amount": amount,
            "reference": reference,
        }

    if purchase_type == "tv":
        tv_id = kwargs.get("tv_id")
        package_id = kwargs.get("package_id")
        smart_card_number = kwargs.get("smart_card_number") or beneficiary
        if kwargs.get("tv_variation"):
            plan = kwargs["tv_variation"]
            if not tv_id:
                tv_id = plan.service.service_id
            if not package_id:
                package_id = plan.variation_id
        return {
            "tv_id": tv_id,
            "package_id": package_id,
            "smart_card_number": smart_card_number,
            "phone": phone,
            "amount": amount,
            "reference": reference,
        }

    if purchase_type == "electricity":
        disco_id = kwargs.get("disco_id")
        plan_id = kwargs.get("plan_id")
        meter_number = kwargs.get("meter_number") or beneficiary
        if kwargs.get("electricity_variation"):
            plan = kwargs["electricity_variation"]
            if not disco_id:
                disco_id = plan.service.service_id
            if not plan_id:
                plan_id = plan.variation_id
        return {
            "disco_id": disco_id,
            "plan_id": plan_id,
            "meter_number": meter_number,
            "phone": phone,
            "amount": amount,
            "reference": reference,
        }

    if purchase_type == "internet":
        plan_id = kwargs.get("plan_id")
        if kwargs.get("internet_variation"):
            plan = kwargs["internet_variation"]
            if not plan_id:
                plan_id = plan.variation_id
        return {
            "plan_id": plan_id,
            "phone": phone,
            "amount": amount,
            "reference": reference,
        }

    if purchase_type == "education":
        exam_type = kwargs.get("exam_type")
        variation_id = kwargs.get("variation_id")
        quantity = kwargs.get("quantity") or 1
        if kwargs.get("education_variation"):
            plan = kwargs["education_variation"]
            if not exam_type:
                exam_type = plan.service.service_id
            if not variation_id:
                variation_id = plan.variation_id
        return {
            "exam_type": exam_type,
            "variation_id": variation_id,
            "quantity": quantity,
            "amount": amount,
            "reference": reference,
        }

    return {
        "amount": amount,
        "reference": reference,
    }

def _json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dj_models.Model):
        return getattr(value, "id", str(value))
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value

def to_decimal(value, default='0.00'):
    """Safely convert a value to Decimal."""
    try:
        if value is None or value == "":
            return Decimal(str(default))
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(str(default))

def _build_finalize_purchase(purchase_type, status, res, user, final_amount, beneficiary, reference, initiator, initiated_by, provider_obj, discount, promo_obj, service_name, kwargs, cost_price=Decimal('0.00'), profit=Decimal('0.00')):
    """Internal helper to shared the record creation and notification logic."""
    final_amount = to_decimal(final_amount)
    cost_price = to_decimal(cost_price)
    profit = to_decimal(profit)
    discount = to_decimal(discount)
    with db_transaction.atomic():
        purchase = Purchase.objects.create(
            user=user,
            purchase_type=purchase_type,
            amount=final_amount,
            beneficiary=beneficiary,
            reference=reference,
            status=status,
            provider_response=_json_safe(res),
            provider=provider_obj,
            initiator=initiator,
            initiated_by=initiated_by,
            cost_price=cost_price,
            profit=profit
        )
        
        # Link extras
        if 'airtime_service' in kwargs: purchase.airtime_service = kwargs['airtime_service']
        if 'data_variation' in kwargs: purchase.data_variation = kwargs['data_variation']
        if 'electricity_service' in kwargs: purchase.electricity_service = kwargs['electricity_service']
        if 'tv_variation' in kwargs: purchase.tv_variation = kwargs['tv_variation']
        if 'internet_variation' in kwargs: purchase.internet_variation = kwargs['internet_variation']
        if 'education_variation' in kwargs: purchase.education_variation = kwargs['education_variation']
        # Extract token and other metadata
        token_val = None
        metadata = {}

        if isinstance(res, dict):
            # Check direct keys
            token_val = res.get('token') or res.get('purchased_code') or res.get('pin')
            
            # Populate metadata dictionary
            for key in ['token', 'tokens', 'pin', 'pins', 'serial', 'serial_number', 'units', 'receipt_no', 'meter_name', 'customer_name', 'purchased_code']:
                if key in res and res[key] is not None:
                    metadata[key] = res[key]
            
            # Inspect raw_response for further details
            raw = res.get('raw_response')
            if isinstance(raw, dict):
                if not token_val:
                    token_val = raw.get('token') or raw.get('purchased_code') or raw.get('pin') or raw.get('pin_code')
                for k, v in raw.items():
                    kl = k.lower()
                    if any(x in kl for x in ['token', 'pin', 'serial', 'units', 'receipt', 'code', 'meter', 'customer']):
                        if v is not None:
                            metadata[k] = v
                # Check nested content/details
                for nested_key in ['content', 'details', 'data']:
                    nested = raw.get(nested_key)
                    if isinstance(nested, dict):
                        if not token_val:
                            token_val = nested.get('token') or nested.get('purchased_code') or nested.get('pin') or nested.get('pin_code')
                        for k, v in nested.items():
                            kl = k.lower()
                            if any(x in kl for x in ['token', 'pin', 'serial', 'units', 'receipt', 'code', 'meter', 'customer']):
                                if v is not None:
                                    metadata[k] = v

        if token_val:
            purchase.token = token_val
            metadata['token'] = token_val
        
        purchase.metadata = metadata
        purchase.save()

        # Handle Promo Usage
        if promo_obj:
            PurchasePromoUsed.objects.create(
                purchase=purchase,
                promo_code=promo_obj,
                discount_applied=discount
            )
            promo_obj.used_count += 1
            promo_obj.save()

        # Terminal Failure - Auto Refund
        auto_refund = False
        if status == "failed":
            auto_refund = True
            try:
                from summary.models import SiteConfig
                config = SiteConfig.objects.first()
                if config and not config.auto_refund_enabled:
                    auto_refund = False
            except Exception:
                pass

            routing = ServiceRouting.objects.filter(service=purchase_type).first()
            if routing and not routing.auto_refund_enabled:
                auto_refund = False

        if status == "failed" and auto_refund:
            fund_wallet(
                user.id, 
                final_amount, 
                f"Refund: {service_name} purchase failed ({reference})",
                initiator="system"
            )
            purchase.status = "refunded"
            purchase.save(update_fields=["status"])
            NotificationService.send_from_template(
                user, 
                "purchase-failed", 
                {"service": service_name, "beneficiary": beneficiary, "reference": reference, "amount": final_amount}
            )
        elif status == "success":
            NotificationService.send_from_template(
                user, 
                "purchase-success", 
                {"service": service_name, "beneficiary": beneficiary, "reference": reference, "amount": final_amount}
            )
            from wallet.utils import process_cashback, process_referral_reward
            process_cashback(user, purchase_type, final_amount)
            process_referral_reward(user, trigger_event='transaction', transaction_amount=final_amount)
 
        if hasattr(user, 'developer_profile'):
            dispatch_developer_webhook(purchase)

    return {"status": status, "purchase_id": purchase.id, "res": res, "amount": final_amount}

def purchase_airtime(user, network, phone, amount, reference, promo_code_str=None, initiator="self", initiated_by=None):
    if not _service_enabled("airtime"):
        return {"status": "failed", "error": "Airtime purchases are currently disabled."}
    
    if not network.is_active:
        return {"status": "failed", "error": "Airtime service is inactive."}

    discount_val = network.discount
    
    from summary.models import SiteConfig
    config = SiteConfig.objects.first()
    margin = config.airtime_margin if config else Decimal('0.00')

    base_amount = to_decimal(amount)
    actual_amount = base_amount + margin
    cost_price = base_amount - (base_amount * to_decimal(discount_val) / 100)
    
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (actual_amount * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = actual_amount - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    wallet = Wallet.objects.filter(user_id=user.id).first()
    if not wallet or wallet.balance < final_amount:
        return {"status": "failed", "error": "Insufficient balance"}

    try:
        debit_wallet(user.id, final_amount, f"Airtime purchase: {reference}", initiator=initiator, initiated_by=initiated_by)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    call_kwargs = {
        "phone": phone,
        "network": network.service_id,
        "amount": base_amount,
        "reference": reference,
    }
    # Use the provider assigned to this specific network record directly.
    provider_config = getattr(network, 'provider', None)
    if provider_config:
        res = ProviderRouter.execute_with_provider(provider_config, "buy_airtime", **call_kwargs)
    else:
        # Fallback: use the routing table if no provider is attached.
        res = ProviderRouter.execute_with_fallback("airtime", "buy_airtime", **call_kwargs)

    _log_provider_response("airtime", reference, user.id, res)
    status = "success" if res['status'] == 'SUCCESS' else "failed"
    provider_obj = VTUProviderConfig.objects.filter(name=res.get('provider_used')).first() if res.get('provider_used') else None
    
    return _build_finalize_purchase("airtime", status, res, user, final_amount, phone, reference, initiator, initiated_by, provider_obj, discount, promo_obj, f"{network.service_name} Airtime", {"airtime_service": network}, cost_price=cost_price, profit=profit)


def purchase_data(user, plan, phone, reference, promo_code_str=None, initiator="self", initiated_by=None):
    if not _service_enabled("data"):
        return {"status": "failed", "error": "Data purchases are currently disabled."}
    if not plan.is_active or not plan.service.is_active:
        return {"status": "failed", "error": "Data plan is inactive."}

    amount = plan.agent_price if user.role == 'agent' else plan.selling_price
    cost_price = plan.cost_price
    
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (to_decimal(amount) * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = to_decimal(amount) - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    wallet = Wallet.objects.filter(user_id=user.id).first()
    if not wallet or wallet.balance < final_amount:
        return {"status": "failed", "error": "Insufficient balance"}

    try:
        debit_wallet(user.id, final_amount, f"Data purchase: {reference}", initiator=initiator, initiated_by=initiated_by)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    call_kwargs = {
        "phone": phone,
        "network": plan.service.service_id,
        "plan_id": plan.variation_id,
        "amount": amount,
        "reference": reference,
    }
    # Use the provider assigned to this specific data service record directly.
    provider_config = getattr(plan.service, 'provider', None)
    if provider_config:
        res = ProviderRouter.execute_with_provider(provider_config, "buy_data", **call_kwargs)
    else:
        # Fallback: use the routing table if no provider is attached.
        res = ProviderRouter.execute_with_fallback("data", "buy_data", **call_kwargs)

    _log_provider_response("data", reference, user.id, res)
    status = "success" if res['status'] == 'SUCCESS' else "failed"
    provider_obj = VTUProviderConfig.objects.filter(name=res.get('provider_used')).first() if res.get('provider_used') else None
    
    return _build_finalize_purchase("data", status, res, user, final_amount, phone, reference, initiator, initiated_by, provider_obj, discount, promo_obj, f"{plan.service.service_name} Data Bundle", {"data_variation": plan}, cost_price=cost_price, profit=profit)


def purchase_tv(user, tv_variation, customer_id, reference, promo_code_str=None, initiator="self", initiated_by=None):
    if not _service_enabled("tv"):
        return {"status": "failed", "error": "TV purchases are currently disabled."}
    if not tv_variation.is_active or not tv_variation.service.is_active:
        return {"status": "failed", "error": "TV package is inactive."}

    amount = tv_variation.agent_price if user.role == 'agent' else tv_variation.selling_price
    cost_price = tv_variation.cost_price
    
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (to_decimal(amount) * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = to_decimal(amount) - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    wallet = Wallet.objects.filter(user_id=user.id).first()
    if not wallet or wallet.balance < final_amount:
        return {"status": "failed", "error": "Insufficient balance"}

    try:
        debit_wallet(user.id, final_amount, f"TV purchase: {reference}", initiator=initiator, initiated_by=initiated_by)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    call_kwargs = {
        "tv_id": tv_variation.service.service_id,
        "package_id": tv_variation.variation_id,
        "smart_card_number": customer_id,
        "phone": user.phone_number,
        "amount": amount,
        "reference": reference,
    }
    res = ProviderRouter.execute_with_fallback("tv", "buy_tv", **call_kwargs)

    _log_provider_response("tv", reference, user.id, res)
    status = "success" if res['status'] == 'SUCCESS' else "failed"
    provider_obj = VTUProviderConfig.objects.filter(name=res.get('provider_used')).first() if res.get('provider_used') else None
    
    return _build_finalize_purchase("tv", status, res, user, final_amount, customer_id, reference, initiator, initiated_by, provider_obj, discount, promo_obj, f"{tv_variation.service.service_name} TV Sub", {"tv_variation": tv_variation}, cost_price=cost_price, profit=profit)

def purchase_electricity(user, electricity_variation, meter_number, amount, reference, promo_code_str=None, initiator="self", initiated_by=None):
    if not _service_enabled("electricity"):
        return {"status": "failed", "error": "Electricity purchases are currently disabled."}
    if not electricity_variation.is_active or not electricity_variation.service.is_active:
        return {"status": "failed", "error": "Electricity service is inactive."}

    discount_val = electricity_variation.agent_discount if user.role == 'agent' else electricity_variation.discount
    
    from summary.models import SiteConfig
    config = SiteConfig.objects.first()
    margin = config.electricity_margin if config else Decimal('0.00')

    base_amount = to_decimal(amount)
    actual_amount = base_amount + margin
    
    # If the variation has a cost_price, use it, otherwise calculate from discount using base_amount
    if hasattr(electricity_variation, 'cost_price') and to_decimal(electricity_variation.cost_price) > 0:
        cost_price = to_decimal(electricity_variation.cost_price)
    else:
        cost_price = base_amount - (base_amount * to_decimal(discount_val) / 100)
    
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (actual_amount * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = actual_amount - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    wallet = Wallet.objects.filter(user_id=user.id).first()
    if not wallet or wallet.balance < final_amount:
        return {"status": "failed", "error": "Insufficient balance"}

    try:
        debit_wallet(user.id, final_amount, f"Electricity purchase: {reference}", initiator=initiator, initiated_by=initiated_by)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    call_kwargs = {
        "disco_id": electricity_variation.service.service_id,
        "plan_id": electricity_variation.variation_id,
        "meter_number": meter_number,
        "phone": user.phone_number,
        "amount": base_amount,
        "reference": reference,
    }
    res = ProviderRouter.execute_with_fallback("electricity", "buy_electricity", **call_kwargs)

    _log_provider_response("electricity", reference, user.id, res)
    status = "success" if res['status'] == 'SUCCESS' else "failed"
    provider_obj = VTUProviderConfig.objects.filter(name=res.get('provider_used')).first() if res.get('provider_used') else None
    
    return _build_finalize_purchase("electricity", status, res, user, final_amount, meter_number, reference, initiator, initiated_by, provider_obj, discount, promo_obj, f"{electricity_variation.service.service_name} Electricity", {"electricity_service": electricity_variation.service, "electricity_variation": electricity_variation}, cost_price=cost_price, profit=profit)

def purchase_internet(user, internet_variation, phone, reference, promo_code_str=None, initiator="self", initiated_by=None):
    if not _service_enabled("internet"):
        return {"status": "failed", "error": "Internet purchases are currently disabled."}
    if not internet_variation.is_active or not internet_variation.service.is_active:
        return {"status": "failed", "error": "Internet service is inactive."}

    amount = internet_variation.agent_price if user.role == 'agent' else internet_variation.selling_price
    cost_price = internet_variation.cost_price
    
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (to_decimal(amount) * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = to_decimal(amount) - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    wallet = Wallet.objects.filter(user_id=user.id).first()
    if not wallet or wallet.balance < final_amount:
        return {"status": "failed", "error": "Insufficient balance"}

    try:
        debit_wallet(user.id, final_amount, f"Internet purchase: {reference}", initiator=initiator, initiated_by=initiated_by)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    call_kwargs = {
        "plan_id": internet_variation.variation_id,
        "phone": phone,
        "amount": amount,
        "reference": reference,
        "internet_variation": internet_variation
    }
    res = ProviderRouter.execute_with_fallback("internet", "buy_internet", **call_kwargs)

    _log_provider_response("internet", reference, user.id, res)
    status = "success" if res['status'] == 'SUCCESS' else "failed"
    provider_obj = VTUProviderConfig.objects.filter(name=res.get('provider_used')).first() if res.get('provider_used') else None
    
    return _build_finalize_purchase("internet", status, res, user, final_amount, phone, reference, initiator, initiated_by, provider_obj, discount, promo_obj, "Internet Subscription", {"internet_variation": internet_variation}, cost_price=cost_price, profit=profit)

def purchase_education(user, education_variation, phone, quantity=1, reference=None, promo_code_str=None, initiator="self", initiated_by=None):
    if not _service_enabled("education"):
        return {"status": "failed", "error": "Education purchases are currently disabled."}
    if not education_variation.is_active or not education_variation.service.is_active:
        return {"status": "failed", "error": "Education service is inactive."}

    amount = (education_variation.agent_price if user.role == 'agent' else education_variation.selling_price) * quantity
    cost_price = education_variation.cost_price * quantity
    
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (to_decimal(amount) * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = to_decimal(amount) - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    wallet = Wallet.objects.filter(user_id=user.id).first()
    if not wallet or wallet.balance < final_amount:
        return {"status": "failed", "error": "Insufficient balance"}

    try:
        debit_wallet(user.id, final_amount, f"Education purchase: {reference}", initiator=initiator, initiated_by=initiated_by)
    except Exception as e:
        return {"status": "failed", "error": str(e)}

    call_kwargs = {
        "exam_type": education_variation.service.service_id,
        "variation_id": education_variation.variation_id,
        "quantity": quantity,
        "amount": amount,
        "reference": reference,
        "education_variation": education_variation
    }
    res = ProviderRouter.execute_with_fallback("education", "buy_education", **call_kwargs)

    _log_provider_response("education", reference, user.id, res)
    status = "success" if res['status'] == 'SUCCESS' else "failed"
    provider_obj = VTUProviderConfig.objects.filter(name=res.get('provider_used')).first() if res.get('provider_used') else None
    
    return _build_finalize_purchase("education", status, res, user, final_amount, phone, reference, initiator, initiated_by, provider_obj, discount, promo_obj, f"{education_variation.name} PIN", {"education_variation": education_variation}, cost_price=cost_price, profit=profit)

def process_vtu_purchase(user, purchase_type, amount, beneficiary, action, promo_code_str=None, initiator="self", initiated_by=None, **kwargs):
    """
    Unified logic for processing VTU purchases.
    """
    service_name = kwargs.get('service_name', purchase_type.title())
    
    # 0. Service enabled check
    if not _service_enabled(purchase_type):
        return {"status": "failed", "error": f"{purchase_type} purchases are currently disabled."}

    # 1. Validate plan/service
    validation_error = _validate_service_and_plan(purchase_type, kwargs)
    if validation_error:
        return {"status": "failed", "error": validation_error}

    # 3. Resolve cost_price
    cost_price = Decimal('0.00')
    if purchase_type == 'airtime' and 'airtime_service' in kwargs:
        asv = kwargs['airtime_service']
        disc = asv.agent_discount if user.role == 'agent' else asv.discount
        # Standard cost calculation if not explicitly set
        cost_price = to_decimal(amount) - (to_decimal(amount) * to_decimal(disc) / 100)
    elif purchase_type == 'data' and 'data_variation' in kwargs:
        cost_price = kwargs['data_variation'].cost_price
    elif purchase_type == 'tv' and 'tv_variation' in kwargs:
        cost_price = kwargs['tv_variation'].cost_price
    elif purchase_type == 'electricity' and 'electricity_variation' in kwargs:
        ev = kwargs['electricity_variation']
        if ev.cost_price > 0: cost_price = ev.cost_price
        else:
            disc = ev.agent_discount if user.role == 'agent' else ev.discount
            cost_price = to_decimal(amount) - (to_decimal(amount) * to_decimal(disc) / 100)
    elif purchase_type == 'internet' and 'internet_variation' in kwargs:
        cost_price = kwargs['internet_variation'].cost_price
    elif purchase_type == 'education' and 'education_variation' in kwargs:
        cost_price = kwargs['education_variation'].cost_price * kwargs.get('quantity', 1)

    # 4. Handle Promo Code
    discount = Decimal('0.00')
    promo_obj = None
    if promo_code_str:
        promo_obj = PromoCode.objects.filter(code=promo_code_str).first()
        if promo_obj and promo_obj.is_valid():
            if promo_obj.discount_amount > 0:
                discount = promo_obj.discount_amount
            elif promo_obj.discount_percentage > 0:
                discount = (to_decimal(amount) * promo_obj.discount_percentage) / 100
        else:
            return {"status": "failed", "error": "Invalid or expired promo code."}

    final_amount = to_decimal(amount) - discount
    if final_amount < 0: final_amount = Decimal('0.00')
    
    profit = final_amount - cost_price

    # 4. Reference & record initialization
    reference = kwargs.get('reference')
    
    # 5. Affordability check
    wallet = Wallet.objects.filter(user_id=user.id).first()
    balance = wallet.balance if wallet else Decimal('0.00')
    if to_decimal(balance) < to_decimal(final_amount):
        return {"status": "failed", "error": "Insufficient balance"}

    # 6. Debit Wallet
    try:
        debit_wallet(
            user.id, 
            final_amount, 
            f"{service_name} purchase: {reference}",
            initiator=initiator,
            initiated_by=initiated_by
        )
    except ValueError as e:
        return {"status": "failed", "error": f"Wallet debit failed: {e}"}

    # 7. Execute via Router (with fallback/retries)
    call_kwargs = _build_provider_call_kwargs(
        purchase_type=purchase_type,
        amount=amount,
        beneficiary=beneficiary,
        reference=reference,
        kwargs=kwargs,
        user=user,
    )
    # Provide extra context for providers that accept **kwargs
    if "internet_variation" in kwargs:
        call_kwargs["internet_variation"] = kwargs.get("internet_variation")
    if "education_variation" in kwargs:
        call_kwargs["education_variation"] = kwargs.get("education_variation")
    if "beneficiary" not in call_kwargs:
        call_kwargs["beneficiary"] = beneficiary

    res = ProviderRouter.execute_with_fallback(purchase_type, action, **call_kwargs)
    if isinstance(res, dict):
        res.setdefault("request_data", _json_safe(call_kwargs))

    # 8. Handle Outcome
    status = "pending"
    if res['status'] == 'SUCCESS':
        status = "success"
    elif res['status'] == 'FAILED':
        status = "failed"

    return _build_finalize_purchase(purchase_type, status, res, user, final_amount, beneficiary, reference, initiator, initiated_by, None, discount, promo_obj, service_name, kwargs, cost_price=cost_price, profit=profit)

def handle_vtu_async_failure(purchase):
    """
    Handles terminal failures reported via webhooks/callbacks.
    Decides whether to retry, fallback, or refund based on config.
    """
    logger.info(f"Handling async failure for purchase {purchase.reference}")
    
    # 1. Check if we should retry or fallback
    routing = ServiceRouting.objects.filter(service=purchase.purchase_type).first()
    provider_config = purchase.provider
    
    # Track the failure
    purchase.status = "failed"
    # We don't automatically increment retry_count here, 
    # we use it as a limit check.
    
    if routing:
        max_retries = routing.retry_count or 1
        
        # Determine current chain and where we are
        chain = ProviderRouter.get_routing_chain(purchase.purchase_type)
        provider_names = [p.provider_name for p in chain]
        
        current_index = -1
        if provider_config and provider_config.name in provider_names:
            current_index = provider_names.index(provider_config.name)

        # 2. Case: Retry with SAME provider
        if purchase.retry_count < max_retries:
            logger.info(f"Retrying purchase {purchase.reference} with same provider (Attempt {purchase.retry_count + 1})")
            purchase.retry_count += 1
            purchase.save()
            
            # Execute retry (can be async task)
            # For now, let's trigger it directly
            res = ProviderRouter.execute_with_fallback(purchase.purchase_type, "re-buy-action", reference=purchase.reference)
            # Re-buy action is pseudocode, would need specific methods like buy_airtime
            # Actually ProviderRouter handles the whole logic.

        # 3. Case: Fallback to NEXT provider
        elif current_index != -1 and current_index < len(provider_names) - 1:
            next_provider = provider_names[current_index + 1]
            logger.info(f"Falling back to provider {next_provider} for purchase {purchase.reference}")
            # ... Logic to trigger purchase with next provider ...
            # Actually, simply calling execution again with the remaining chain might be better,
            # but that's what execute_with_fallback does initially.
            # In an async fail state, we might just want to trigger a manual retry from the admin dashboard.

    # 4. Final Fallback: Refund
    if provider_config and provider_config.auto_refund_on_failure:
        fund_wallet(
            purchase.user.id, 
            purchase.amount, 
            f"Auto-Refund: Failed {purchase.purchase_type} purchase ({purchase.reference})",
            initiator="system"
        )
        purchase.status = "refunded"
        NotificationService.send_from_template(
            purchase.user, 
            "transaction-reversed", 
            {"service": purchase.purchase_type, "beneficiary": purchase.beneficiary, "reference": purchase.reference, "amount": purchase.amount}
        )
    
    purchase.save()
    return True

