from django.utils import timezone
from django.db import transaction
from payments.models import Deposit
from wallet.models import Wallet, WalletTransaction, TransactionCharge
from notifications.utils import NotificationService
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)

def to_decimal(value):
    """Convert a value to Decimal type."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

def fund_wallet(user_id, amount, description="Wallet funded", reference=None, initiator='self', initiated_by=None,
                sender_account_name=None, sender_account_number=None, sender_bank_name=None,
                receiver_account_name=None, receiver_account_number=None, receiver_bank_name=None,
                return_tx=False):
    if float(amount) <= 0:
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
        tx_ref = reference or uuid.uuid4().hex[:10].upper()
        # If tx_ref already exists, make unique
        if WalletTransaction.objects.filter(reference=tx_ref).exists():
            tx_ref = f"{tx_ref}-{uuid.uuid4().hex[:4].upper()}"
            
        tx = WalletTransaction.objects.create(
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
            reference=tx_ref,
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
    if return_tx:
        return wallet.balance, tx
    return wallet.balance

def debit_wallet(user_id, amount, description="Wallet debited", reference=None, initiator='self', initiated_by=None,
                 sender_account_name=None, sender_account_number=None, sender_bank_name=None,
                 receiver_account_name=None, receiver_account_number=None, receiver_bank_name=None,
                 return_tx=False):
    if float(amount) <= 0:
        raise ValueError("Amount must be positive")
    with transaction.atomic():
        wallet, created = Wallet.objects.get_or_create(user_id=user_id, defaults={'balance': 0.0})
        if float(wallet.balance) < float(amount):
            raise ValueError("Insufficient balance")
        wallet.balance = float(wallet.balance) - float(amount)
        wallet.save()
        tx_ref = reference or uuid.uuid4().hex[:10].upper()
        if WalletTransaction.objects.filter(reference=tx_ref).exists():
            tx_ref = f"{tx_ref}-{uuid.uuid4().hex[:4].upper()}"

        tx = WalletTransaction.objects.create(
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
            reference=tx_ref,
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
    if return_tx:
        return wallet.balance, tx
    return wallet.balance


# ----------------------------------------------------
# Transaction Charges Utilities
# ----------------------------------------------------

def get_applicable_charges(transaction_type: str, amount) -> list[TransactionCharge]:
    """
    Return all active TransactionCharge rules that match transaction_type and amount range.
    """
    amt = to_decimal(amount)
    charges = TransactionCharge.objects.filter(
        transaction_type=transaction_type,
        is_active=True,
        min_transaction_amount__lte=amt
    )
    applicable = []
    for c in charges:
        if c.max_transaction_amount is not None:
            if amt > to_decimal(c.max_transaction_amount):
                continue
        applicable.append(c)
    return applicable

def calculate_charge_amount(charge: TransactionCharge, amount) -> Decimal:
    """
    Compute the fee amount for a given TransactionCharge and transaction amount.
    """
    amt = to_decimal(amount)
    charge_amt = to_decimal(charge.amount)
    if charge.charge_type == 'flat':
        fee = charge_amt
    elif charge.charge_type == 'percentage':
        fee = (amt * charge_amt) / Decimal('100')
        if charge.cap is not None:
            cap_val = to_decimal(charge.cap)
            if fee > cap_val:
                fee = cap_val
    else:
        fee = Decimal('0.00')
    return round(fee, 2)

def calculate_total_charges(transaction_type: str, amount) -> tuple[Decimal, list[dict]]:
    """
    Returns (total_charge_amount, breakdown_list).
    """
    charges = get_applicable_charges(transaction_type, amount)
    total = Decimal('0.00')
    breakdown = []
    for c in charges:
        fee = calculate_charge_amount(c, amount)
        total += fee
        breakdown.append({
            'id': c.id,
            'name': c.name,
            'charge_type': c.charge_type,
            'rate_or_amount': str(c.amount),
            'cap': str(c.cap) if c.cap is not None else None,
            'computed_amount': str(fee),
            'block_if_insufficient': c.block_if_insufficient,
        })
    return round(total, 2), breakdown

def validate_balance_for_transaction(user_id: int, transaction_type: str, transaction_amount) -> tuple[bool, Decimal, str]:
    """
    Validates if user has sufficient balance for transaction_amount plus any charges
    configured with block_if_insufficient=True.
    Returns (is_valid, total_required, error_message).
    """
    amt = to_decimal(transaction_amount)
    wallet = Wallet.objects.filter(user_id=user_id).first()
    curr_balance = to_decimal(wallet.balance) if wallet else Decimal('0.00')

    charges = get_applicable_charges(transaction_type, amt)
    blocking_charges_total = Decimal('0.00')
    for c in charges:
        if c.block_if_insufficient:
            blocking_charges_total += calculate_charge_amount(c, amt)

    total_required = amt + blocking_charges_total
    if curr_balance < total_required:
        err = f"Insufficient wallet balance. Total required: ₦{total_required:,.2f} (Amount: ₦{amt:,.2f}, Required Charges: ₦{blocking_charges_total:,.2f}), Available: ₦{curr_balance:,.2f}"
        return False, total_required, err
    return True, total_required, ""

def apply_charges(user_id: int, transaction_type: str, transaction_amount, parent_wallet_tx=None, initiator: str = 'system', initiated_by=None) -> list[WalletTransaction]:
    """
    Applies (debits separately) all active charges for the given transaction.
    If block_if_insufficient is True and balance is short, raises ValueError.
    If block_if_insufficient is False and balance is short, the charge is skipped (waived).
    Returns list of created charge WalletTransaction records.
    """
    amt = to_decimal(transaction_amount)
    charges = get_applicable_charges(transaction_type, amt)
    created_charge_txs = []

    for charge in charges:
        fee = calculate_charge_amount(charge, amt)
        if fee <= 0:
            continue

        with transaction.atomic():
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user_id=user_id, defaults={'balance': 0.0})
            if to_decimal(wallet.balance) < fee:
                if charge.block_if_insufficient:
                    raise ValueError(f"Insufficient wallet balance (₦{wallet.balance}) for required charge '{charge.name}' (₦{fee}).")
                else:
                    logger.info(f"Skipping charge '{charge.name}' of ₦{fee} for user {user_id} due to insufficient balance.")
                    continue

            wallet.balance = float(wallet.balance) - float(fee)
            wallet.save()

            charge_ref = f"CHG-{uuid.uuid4().hex[:10].upper()}"
            charge_tx = WalletTransaction.objects.create(
                wallet=wallet,
                user=wallet.user,
                transaction_type='debit',
                amount=fee,
                timestamp=timezone.now(),
                description=f"Charge: {charge.name}",
                balance_before=float(wallet.balance) + float(fee),
                balance_after=wallet.balance,
                initiator=initiator,
                initiated_by=initiated_by,
                reference=charge_ref,
                charge_for=parent_wallet_tx,
                is_charge=True,
                is_refunded=False,
            )
            created_charge_txs.append(charge_tx)

    return created_charge_txs

def refund_charges(parent_wallet_tx_or_ref, initiated_by=None) -> list[WalletTransaction]:
    """
    Finds all un-refunded charge debits linked to the parent transaction and refunds them.
    Idempotent: skips already refunded charges.
    Returns list of refunded charge records.
    """
    if not parent_wallet_tx_or_ref:
        return []

    parent_tx = None
    if isinstance(parent_wallet_tx_or_ref, str):
        parent_tx = WalletTransaction.objects.filter(reference=parent_wallet_tx_or_ref).first()
        if not parent_tx:
            parent_tx = WalletTransaction.objects.filter(deposit__reference=parent_wallet_tx_or_ref).first()
    else:
        parent_tx = parent_wallet_tx_or_ref

    if not parent_tx:
        return []

    refunded_txs = []
    with transaction.atomic():
        charge_txs = parent_tx.charge_transactions.filter(is_charge=True, is_refunded=False, transaction_type='debit')
        for charge_tx in charge_txs:
            fund_wallet(
                user_id=charge_tx.user.id,
                amount=charge_tx.amount,
                description=f"Refund {charge_tx.description} for {parent_tx.reference}",
                initiator='system',
                initiated_by=initiated_by
            )
            charge_tx.is_refunded = True
            charge_tx.save(update_fields=['is_refunded'])
            refunded_txs.append(charge_tx)

    return refunded_txs



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

