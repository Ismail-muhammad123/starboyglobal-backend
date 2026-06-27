from django.utils import timezone
from django.db import transaction
from payments.models import Deposit
from wallet.models import Wallet, WalletTransaction
from notifications.utils import NotificationService
from decimal import Decimal
import uuid

def to_decimal(value):
    """Convert a value to Decimal type."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

def fund_wallet(user_id, amount, description="Wallet funded", reference=None, initiator='self', initiated_by=None,
                sender_account_name=None, sender_account_number=None, sender_bank_name=None,
                receiver_account_name=None, receiver_account_number=None, receiver_bank_name=None):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    with transaction.atomic():
        payment_obj = None
        if reference:
            try:
                payment_obj = Deposit.objects.get(reference=reference)
            except Deposit.DoesNotExist:
                pass
        wallet, created = Wallet.objects.get_or_create(user_id=user_id, defaults={'balance': 0.0})
        wallet.balance = float(wallet.balance) + float(amount)
        wallet.save()
        WalletTransaction.objects.create(
            user=wallet.user,
            wallet=wallet,
            transaction_type='credit',
            amount=amount,
            deposit=payment_obj,
            balance_before=float(wallet.balance) - float(amount),
            balance_after=wallet.balance,
            description=description,
            initiator=initiator,
            initiated_by=initiated_by,
            reference=uuid.uuid4().hex[:10].upper(),
            sender_account_name=sender_account_name,
            sender_account_number=sender_account_number,
            sender_bank_name=sender_bank_name,
            receiver_account_name=receiver_account_name,
            receiver_account_number=receiver_account_number,
            receiver_bank_name=receiver_bank_name,
        )
        NotificationService.send_from_template(
            wallet.user, 
            "wallet-funded", 
            {"amount": amount, "balance": wallet.balance, "reference": reference or "N/A", "description": description}
        )
    return wallet.balance

def debit_wallet(user_id, amount, description="Wallet debited", initiator='self', initiated_by=None,
                 sender_account_name=None, sender_account_number=None, sender_bank_name=None,
                 receiver_account_name=None, receiver_account_number=None, receiver_bank_name=None):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    with transaction.atomic():
        wallet, created = Wallet.objects.get_or_create(user_id=user_id, defaults={'balance': 0.0})
        if wallet.balance < amount:
            raise ValueError("Insufficient balance")
        wallet.balance = float(wallet.balance)- float(amount)
        wallet.save()
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='debit',
            amount=amount,
            timestamp=timezone.now(),
            description=description,
            balance_before=float(wallet.balance) + float(amount),
            balance_after=wallet.balance,
            initiator=initiator,
            initiated_by=initiated_by,
            user=wallet.user,
            reference=uuid.uuid4().hex[:10].upper(),
            sender_account_name=sender_account_name,
            sender_account_number=sender_account_number,
            sender_bank_name=sender_bank_name,
            receiver_account_name=receiver_account_name,
            receiver_account_number=receiver_account_number,
            receiver_bank_name=receiver_bank_name,
        )
        NotificationService.send_from_template(
            wallet.user, 
            "wallet-debit", 
            {"amount": amount, "balance": wallet.balance, "reason": description}
        )
    return wallet.balance


def process_referral_reward(user, trigger_event, transaction_amount=0):
    """
    Process referral rewards based on SiteConfig rules.
    trigger_event: 'signup', 'credit', 'transaction'
    """
    from users.models import Referral
    from summary.models import SiteConfig
    config = SiteConfig.objects.first()
    if not config:
        return

    # User must have been referred
    referral_rel = Referral.objects.filter(referred=user).first()
    if not referral_rel:
        return

    referrer = referral_rel.referrer
    
    # Identify which rules to use (Agent vs User)
    is_agent = getattr(referrer, 'role', 'customer') == 'agent'
    
    if is_agent:
        reward_type = config.agent_referral_commission_type
        reward_value = to_decimal(config.agent_referral_commission_value)
        reward_trigger = config.agent_referral_trigger
        reward_cycle = config.agent_referral_cycle
    else:
        reward_type = config.user_referral_commission_type
        reward_value = to_decimal(config.user_referral_commission_value)
        reward_trigger = config.user_referral_trigger
        reward_cycle = config.user_referral_cycle

    if reward_trigger != trigger_event:
        return

    if reward_cycle == 'never':
        return
    
    if reward_cycle == 'once' and referral_rel.bonus_paid:
        return

    # Calculate reward amount
    amount_to_pay = Decimal('0.00')
    if reward_type == 'flat':
        amount_to_pay = reward_value
    elif reward_type == 'percentage':
        amount_to_pay = (to_decimal(transaction_amount) * reward_value) / Decimal('100')

    if amount_to_pay <= Decimal('0.00'):
        return

    # Pay the referrer
    from wallet.utils import fund_wallet # Ensure local import is safe or use parent
    fund_wallet(
        referrer.id, 
        amount_to_pay, 
        description=f"Referral Bonus ({trigger_event}) from {user.phone_number}",
        initiator='system'
    )
    
    # Update referral record
    referral_rel.bonus_paid = True
    referral_rel.bonus_amount = to_decimal(referral_rel.bonus_amount) + amount_to_pay
    referral_rel.save()

def process_cashback(user, service_type, purchase_amount):
    """
    Process cashback for a purchase based on ServiceCashback rules.
    """
    from summary.models import SiteConfig, ServiceCashback
    config = SiteConfig.objects.first()
    if not config or not config.cashback_enabled:
        return

    cashback_rule = ServiceCashback.objects.filter(service_type=service_type, is_active=True).first()
    if not cashback_rule:
        return

    if to_decimal(purchase_amount) < to_decimal(cashback_rule.min_purchase_amount):
        return

    # Calculate cashback
    reward_amount = Decimal('0.00')
    if cashback_rule.cashback_type == 'flat':
        reward_amount = to_decimal(cashback_rule.cashback_value)
    elif cashback_rule.cashback_type == 'percentage':
        reward_amount = (to_decimal(purchase_amount) * to_decimal(cashback_rule.cashback_value)) / Decimal('100')

    if reward_amount <= Decimal('0.00'):
        return

    # Fund user wallet
    fund_wallet(
        user.id,
        reward_amount,
        description=f"Cashback for {service_type} purchase",
        initiator='system'
    )

