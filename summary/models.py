from django.db import models
from django.contrib.auth import get_user_model
from summary.utils import get_api_wallet_balance, get_paystack_balance
from wallet.models import Wallet, WalletTransaction
from payments.models import Deposit, Withdrawal
from django.db.models import Q, Sum, F, Count, Avg, Case, When, Value, DecimalField
from django.utils import timezone
from datetime import timedelta
from orders.models import (
    DataService, DataVariation, AirtimeNetwork, Purchase, VTUProviderConfig,
    TVVariation, ElectricityVariation, InternetVariation, EducationVariation,
)
from support.models import SupportTicket

User = get_user_model()


class SummaryDashboard(Wallet):
    """
    A proxy model that doesn't store data — it aggregates statistics
    from other models across the system.
    """
    class Meta:
        proxy = True
        managed = False
        verbose_name = "Summary Dashboard"
        verbose_name_plural = "Summary Dashboard"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _calculate_profit(qs):
        """
        Calculate profit across all purchase types.
        Uses the stored profit field for new records, while maintaining 
        a fallback for legacy records if needed (though we recommend mapping them).
        """
        # Sum pre-calculated profit
        stored_profit = float(qs.aggregate(total=Sum('profit'))['total'] or 0)
        
        # If there are old records with 0 profit, we could calculate them here,
        # but for simplicity and performance we transition to the new field.
        # Check if we have records with profit=0 that might have on-the-fly profit
        if stored_profit == 0 and qs.exists():
             # Fallback logic for legacy data if specifically needed
             # (Keeping the old logic as a safety net for now)
             profit = 0.0
             profit += float(qs.filter(purchase_type='data', data_variation__isnull=False).annotate(p=F('amount') - F('data_variation__cost_price')).aggregate(total=Sum('p'))['total'] or 0)
             profit += float(qs.filter(purchase_type='tv', tv_variation__isnull=False).annotate(p=F('amount') - F('tv_variation__cost_price')).aggregate(total=Sum('p'))['total'] or 0)
             profit += float(qs.filter(purchase_type='electricity', electricity_variation__isnull=False).annotate(p=F('amount') - F('electricity_variation__cost_price')).aggregate(total=Sum('p'))['total'] or 0)
             profit += float(qs.filter(purchase_type='internet', internet_variation__isnull=False).annotate(p=F('amount') - F('internet_variation__cost_price')).aggregate(total=Sum('p'))['total'] or 0)
             profit += float(qs.filter(purchase_type='education', education_variation__isnull=False).annotate(p=F('amount') - F('education_variation__cost_price')).aggregate(total=Sum('p'))['total'] or 0)
             
             airtime_qs = qs.filter(purchase_type='airtime', airtime_service__isnull=False)
             for p in airtime_qs.select_related('airtime_service'):
                 try:
                     discount = float(p.airtime_service.discount or 0) / 100
                     profit += float(p.amount) * discount
                 except Exception: pass
             return profit

        return stored_profit

    @staticmethod
    def _calculate_commissions(qs):
        """
        Calculate agent commissions from successful purchases.
        Commission = selling_price − agent_price for agent purchases.
        """
        agent_purchases = qs.filter(user__role='agent')
        commission = 0.0

        commission += float(
            agent_purchases.filter(purchase_type='data', data_variation__isnull=False)
            .annotate(c=F('amount') - F('data_variation__agent_price'))
            .aggregate(total=Sum('c'))['total'] or 0
        )
        commission += float(
            agent_purchases.filter(purchase_type='tv', tv_variation__isnull=False)
            .annotate(c=F('amount') - F('tv_variation__agent_price'))
            .aggregate(total=Sum('c'))['total'] or 0
        )
        commission += float(
            agent_purchases.filter(purchase_type='internet', internet_variation__isnull=False)
            .annotate(c=F('amount') - F('internet_variation__agent_price'))
            .aggregate(total=Sum('c'))['total'] or 0
        )
        commission += float(
            agent_purchases.filter(purchase_type='education', education_variation__isnull=False)
            .annotate(c=F('amount') - F('education_variation__agent_price'))
            .aggregate(total=Sum('c'))['total'] or 0
        )
        airtime_agent = agent_purchases.filter(purchase_type='airtime', airtime_service__isnull=False)
        for p in airtime_agent.select_related('airtime_service'):
            try:
                agent_disc = float(p.airtime_service.agent_discount or 0) / 100
                commission += float(p.amount) * agent_disc
            except Exception:
                pass

        return commission

    # ------------------------------------------------------------------
    # main summary
    # ------------------------------------------------------------------
    @classmethod
    def summary(cls, start=None, end=None):
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # ── DATE-FILTERED BASE QUERYSETS ──────────────────────────────
        all_purchases = Purchase.objects.all()
        filtered_purchases_all = Purchase.objects.all()
        filtered_wallet_tx = WalletTransaction.objects.all()
        deposits_qs = Deposit.objects.all()
        withdrawals_qs = Withdrawal.objects.all()

        if start:
            filtered_purchases_all = filtered_purchases_all.filter(time__gte=start)
            filtered_wallet_tx = filtered_wallet_tx.filter(timestamp__gte=start)
            deposits_qs = deposits_qs.filter(timestamp__gte=start)
            withdrawals_qs = withdrawals_qs.filter(created_at__gte=start)
        if end:
            filtered_purchases_all = filtered_purchases_all.filter(time__lte=end)
            filtered_wallet_tx = filtered_wallet_tx.filter(timestamp__lte=end)
            deposits_qs = deposits_qs.filter(timestamp__lte=end)
            withdrawals_qs = withdrawals_qs.filter(created_at__lte=end)

        filtered_success = filtered_purchases_all.filter(status="success")

        # ==============================================================
        # 1. FINANCIAL
        # ==============================================================
        total_deposits = float(
            deposits_qs.filter(status="SUCCESS").aggregate(s=Sum("amount"))["s"] or 0
        )
        total_withdrawals = float(
            withdrawals_qs.filter(status="APPROVED").aggregate(s=Sum("amount"))["s"] or 0
        )

        # Wallet-to-wallet transfers (descriptions that contain "Transfer to" or "Transfer from")
        transfer_debits = filtered_wallet_tx.filter(
            transaction_type='debit',
            description__istartswith='Transfer to'
        )
        total_transfers = float(
            transfer_debits.aggregate(s=Sum("amount"))["s"] or 0
        )

        # Paystack available balance
        try:
            paystack_balance = get_paystack_balance() or 0.0
        except Exception:
            paystack_balance = 0.0

        # Total payouts (SystemTransaction cashouts)
        total_payouts = 0.0
        try:
            from summary.models import SystemTransaction
            payouts_qs = SystemTransaction.objects.filter(
                transaction_type="CASHOUT", status="SUCCESS"
            )
            if start:
                payouts_qs = payouts_qs.filter(created_at__gte=start)
            if end:
                payouts_qs = payouts_qs.filter(created_at__lte=end)
            total_payouts = float(payouts_qs.aggregate(s=Sum("amount"))["s"] or 0)
        except Exception:
            pass

        financial = {
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_transfers": total_transfers,
            "paystack_balance": paystack_balance,
            "total_payouts": total_payouts,
        }

        # ==============================================================
        # 2. WALLETS
        # ==============================================================
        total_wallet_balance = float(
            Wallet.objects.aggregate(s=Sum("balance"))["s"] or 0
        )
        total_credits = float(
            filtered_wallet_tx.filter(transaction_type='credit')
            .aggregate(s=Sum("amount"))["s"] or 0
        )
        total_debits = float(
            filtered_wallet_tx.filter(transaction_type='debit')
            .aggregate(s=Sum("amount"))["s"] or 0
        )

        wallets = {
            "total_balance": total_wallet_balance,
            "total_credits": total_credits,
            "total_debits": total_debits,
        }

        # ==============================================================
        # 3. PURCHASES
        # ==============================================================
        purchase_success_count = filtered_purchases_all.filter(status="success").count()
        purchase_failed_count = filtered_purchases_all.filter(status="failed").count()
        purchase_pending_count = filtered_purchases_all.filter(status="pending").count()

        total_transaction_volume = float(
            filtered_success.aggregate(s=Sum("amount"))["s"] or 0
        )

        # Totals by service type
        service_types = ['airtime', 'data', 'electricity', 'tv', 'internet', 'education']
        totals_by_service = {}
        for stype in service_types:
            stype_qs = filtered_purchases_all.filter(purchase_type=stype)
            totals_by_service[stype] = {
                "total_amount": float(
                    stype_qs.filter(status="success").aggregate(s=Sum("amount"))["s"] or 0
                ),
                "count": stype_qs.count(),
                "success": stype_qs.filter(status="success").count(),
                "failed": stype_qs.filter(status="failed").count(),
                "pending": stype_qs.filter(status="pending").count(),
            }

        # Total commissions (agent markup)
        total_commissions = cls._calculate_commissions(filtered_success)

        # Total profit
        total_profit = cls._calculate_profit(filtered_success)

        # Profit by period (always uses full dataset, ignoring start/end)
        daily_profit = cls._calculate_profit(
            Purchase.objects.filter(status="success", time__date=today)
        )
        weekly_profit = cls._calculate_profit(
            Purchase.objects.filter(status="success", time__gte=week_ago)
        )
        monthly_profit = cls._calculate_profit(
            Purchase.objects.filter(status="success", time__gte=month_ago)
        )

        purchases = {
            "success_count": purchase_success_count,
            "failed_count": purchase_failed_count,
            "pending_count": purchase_pending_count,
            "total_volume": total_transaction_volume,
            "totals_by_service": totals_by_service,
            "total_commissions": total_commissions,
            "total_profit": total_profit,
            "profit_periods": {
                "today": daily_profit,
                "weekly": weekly_profit,
                "monthly": monthly_profit,
            },
        }

        # ==============================================================
        # 4. USERS
        # ==============================================================
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        agent_users = User.objects.filter(role='agent').count()
        customer_users = User.objects.filter(role='customer').count()
        admin_users = User.objects.filter(
            Q(is_superuser=True) | Q(is_staff=True)
        ).count()
        
        # Enhanced active today logic: Users who logged in OR performed any major action today
        active_users_today = User.objects.filter(
            Q(last_login__date=today) |
            Q(purchases__time__date=today) |
            Q(wallet_transactions__timestamp__date=today) |
            Q(deposits__timestamp__date=today) |
            Q(withdrawals__created_at__date=today) |
            Q(tickets__created_at__date=today)
        ).distinct().count()

        users = {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
            "agents": agent_users,
            "customers": customer_users,
            "admins": admin_users,
            "active_today": active_users_today,
        }

        # ==============================================================
        # 5. VTU API PROVIDERS (per configured provider)
        # ==============================================================
        from orders.router import ProviderRouter
        from orders.models import (
            DataService as DS, AirtimeNetwork as AN,
            TVService, ElectricityService, InternetService, EducationService,
        )

        vtu_providers = []
        for provider in VTUProviderConfig.objects.all():
            # Balance
            balance = 0.0
            if provider.is_active:
                try:
                    impl = ProviderRouter.get_provider_implementation(provider.name)
                    if impl:
                        balance = impl.get_wallet_balance()
                except Exception:
                    pass

            # Active services count (services linked to this provider)
            active_services = 0
            active_services += DS.objects.filter(provider=provider, is_active=True).count()
            active_services += AN.objects.filter(provider=provider, is_active=True).count()
            active_services += TVService.objects.filter(provider=provider, is_active=True).count()
            active_services += ElectricityService.objects.filter(provider=provider, is_active=True).count()
            active_services += InternetService.objects.filter(provider=provider, is_active=True).count()
            active_services += EducationService.objects.filter(provider=provider, is_active=True).count()

            # Total transactions (filtered by date if applicable)
            provider_tx_qs = filtered_purchases_all.filter(provider=provider)
            total_tx = provider_tx_qs.count()
            success_tx = provider_tx_qs.filter(status='success').count()

            vtu_providers.append({
                "id": provider.id,
                "name": provider.get_name_display(),
                "provider_key": provider.name,
                "is_active": provider.is_active,
                "balance": balance,
                "active_services": active_services,
                "total_transactions": total_tx,
                "success_transactions": success_tx,
                "success_rate": round(
                    (success_tx / total_tx * 100) if total_tx > 0 else 100, 2
                ),
            })

        # ==============================================================
        # SERVICE HEALTH INDICATORS (kept from original)
        # ==============================================================
        networks = ['mtn', 'glo', 'airtel', '9mobile']
        health_indicators = {}
        for nw in networks:
            # Convert to list to avoid "Cannot filter a query once a slice has been taken" error
            nw_purchases_statuses = list(Purchase.objects.filter(
                Q(airtime_service__service_name__icontains=nw) | 
                Q(data_variation__service__service_name__icontains=nw)
            ).order_by('-time')[:20].values_list('status', flat=True))
            
            if not nw_purchases_statuses:
                health_indicators[nw] = "EXCELLENT"
            else:
                success_count = nw_purchases_statuses.count("success")
                rate = success_count / len(nw_purchases_statuses)
                if rate >= 0.9: health_indicators[nw] = "EXCELLENT"
                elif rate >= 0.5: health_indicators[nw] = "DEGRADED"
                else: health_indicators[nw] = "POOR"

        # Bill payment system health
        bill_services_list = ['electricity', 'tv', 'education', 'internet']
        bill_tx = Purchase.objects.filter(purchase_type__in=bill_services_list)
        bill_success_rate = 0
        if bill_tx.exists():
            bill_success_rate = (bill_tx.filter(status='success').count() / bill_tx.count()) * 100

        # ==============================================================
        # VTU BALANCE (legacy – kept for backward compat)
        # ==============================================================
        try:
            vtu_balance = get_api_wallet_balance() or 0.0
        except Exception:
            vtu_balance = 0.0

        # SMS balance removed

        # ==============================================================
        # SMART ALERTS
        # ==============================================================
        failed_transactions = Purchase.objects.filter(status="failed").order_by('-time')[:10]
        failed_data = [{
            "id": f.id,
            "ref": f.reference,
            "type": f.purchase_type,
            "amount": float(f.amount),
            "beneficiary": f.beneficiary,
            "time": f.time.isoformat(),
            "error": f.remarks
        } for f in failed_transactions]

        low_balance_alerts = []
        if vtu_balance < 5000: low_balance_alerts.append("Low VTU Provider Balance")

        # ==============================================================
        # DEPOSITS & WITHDRAWALS SUMMARY (legacy – kept for compat)
        # ==============================================================
        deposits_summary = {
            "total_amount": total_deposits,
            "success_count": deposits_qs.filter(status="SUCCESS").count(),
            "pending_count": deposits_qs.filter(status="PENDING").count(),
            "failed_count": deposits_qs.filter(status="FAILED").count(),
        }

        withdrawals_summary = {
            "total_amount": total_withdrawals,
            "approved_count": withdrawals_qs.filter(status="APPROVED").count(),
            "pending_count": withdrawals_qs.filter(status="PENDING").count(),
            "rejected_count": withdrawals_qs.filter(status="REJECTED").count(),
        }

        # ==============================================================
        # SITE CONFIG
        # ==============================================================
        config = SiteConfig.objects.first()
        config_data = {
            "withdrawal_charge": float(config.withdrawal_charge) if config else 0,
            "crediting_charge": float(config.crediting_charge) if config else 0,
            "deposit_charge_fixed": float(config.deposit_charge_fixed) if config else 0,
            "deposit_charge_percentage": float(config.deposit_charge_percentage) if config else 0,
            "withdrawal_charge_fixed": float(config.withdrawal_charge_fixed) if config else 0,
            "withdrawal_charge_percentage": float(config.withdrawal_charge_percentage) if config else 0,
            "automatic_withdrawal": config.automatic_withdrawal if config else False,
            "withdrawals_enabled": config.withdrawals_enabled if config else True,
            "maintenance_mode": config.maintenance_mode if config else False,
            "services_status": {
                "airtime": config.airtime_active if config else True,
                "data": config.data_active if config else True,
                "tv": config.tv_active if config else True,
                "electricity": config.electricity_active if config else True,
                "education": config.education_active if config else True,
            }
        }

        # ==============================================================
        # RESPONSE
        # ==============================================================
        return {
            # ── NEW SECTIONS ──
            "financial": financial,
            "wallets": wallets,
            "purchases": purchases,
            "users": users,
            "vtu_providers": vtu_providers,

            # ── EXISTING SECTIONS (kept for backward compatibility) ──
            "business_metrics": {
                "total_users": total_users,
                "active_users_today": active_users_today,
                "total_wallet_balance": total_wallet_balance,
                "total_transaction_volume": total_transaction_volume,
                "profit": {
                    "today": daily_profit,
                    "weekly": weekly_profit,
                    "monthly": monthly_profit,
                }
            },
            "service_health": {
                "network_status": health_indicators,
                "provider_performances": [{
                    "name": vp["name"],
                    "is_active": vp["is_active"],
                    "success_rate": vp["success_rate"],
                    "total_transactions": vp["total_transactions"],
                } for vp in vtu_providers],
                "bill_system_success_rate": round(bill_success_rate, 2),
            },
            "provider_balances": {
                "vtu": vtu_balance,
                "payment_gateway": paystack_balance,
            },
            "alerts": {
                "failed_transactions": failed_data,
                "low_balance_warnings": low_balance_alerts,
            },
            "quick_actions": {
                "maintenance_mode": config_data["maintenance_mode"],
                "services": config_data["services_status"],
            },
            "finances": {
                "deposits": deposits_summary,
                "withdrawals": withdrawals_summary,
            }
        }

class SiteConfig(models.Model):
    withdrawal_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    crediting_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Newly added charges
    deposit_charge_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deposit_charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    withdrawal_charge_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    withdrawal_charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Auto-creation toggles
    auto_create_wallet = models.BooleanField(default=True)
    auto_create_virtual_account = models.BooleanField(default=True)

    # Signup bonus
    signup_bonus_enabled = models.BooleanField(default=False)
    signup_bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Cashback settings
    cashback_enabled = models.BooleanField(default=False)

    # Referral settings
    COMMISSION_TYPE_CHOICES = [('percentage', 'Percentage'), ('flat', 'Flat')]
    TRIGGER_CHOICES = [('signup', 'On Signup'), ('credit', 'On Credit'), ('transaction', 'On Transaction')]
    CYCLE_CHOICES = [('always', 'Always'), ('once', 'Once'), ('never', 'Never')]

    # Agent Referral Settings
    agent_referral_commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES, default='flat')
    agent_referral_commission_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    agent_referral_trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='signup')
    agent_referral_cycle = models.CharField(max_length=20, choices=CYCLE_CHOICES, default='once')

    # User Referral Settings
    user_referral_commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES, default='flat')
    user_referral_commission_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    user_referral_trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='signup')
    user_referral_cycle = models.CharField(max_length=20, choices=CYCLE_CHOICES, default='once')

    automatic_withdrawal = models.BooleanField(default=False, help_text="If enabled, withdrawals will be processed automatically via Paystack.")
    withdrawals_enabled = models.BooleanField(default=True, help_text="Global toggle to enable or disable user withdrawals.")
    
    # VTU API Funding Details (The bank account to move money to for VTU funding)
    vtu_funding_bank_name = models.CharField(max_length=100, blank=True, null=True)
    vtu_funding_account_number = models.CharField(max_length=20, blank=True, null=True)
    vtu_funding_account_name = models.CharField(max_length=100, blank=True, null=True)

    # Global Automation settings
    auto_retry_enabled = models.BooleanField(default=True)
    auto_refund_enabled = models.BooleanField(default=True)
    notify_admin_on_failure = models.BooleanField(default=True)
    delayed_tx_detection_enabled = models.BooleanField(default=True)
    delayed_tx_timeout_minutes = models.PositiveIntegerField(default=15)

    # Maintenance and health
    maintenance_mode = models.BooleanField(default=False)
    airtime_active = models.BooleanField(default=True)
    data_active = models.BooleanField(default=True)
    tv_active = models.BooleanField(default=True)
    electricity_active = models.BooleanField(default=True)
    education_active = models.BooleanField(default=True)
    enforce_2fa_for_staff = models.BooleanField(default=False, help_text="If enabled, all staff users must pass 2FA to access admin features.")
    
    # Global Notification Channel Toggles
    fcm_enabled = models.BooleanField(default=True, verbose_name="Enable Push (FCM) Notifications")
    email_enabled = models.BooleanField(default=True, verbose_name="Enable Email Notifications")
    sms_enabled = models.BooleanField(default=False, verbose_name="Enable SMS Notifications")
    whatsapp_enabled = models.BooleanField(default=False, verbose_name="Enable WhatsApp Notifications")
    
    # Developer API Settings
    developer_upgrade_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Amount charged to upgrade to developer status.")
    developer_upgrade_kyc_required = models.BooleanField(default=False, help_text="If enabled, user must be KYC verified to upgrade to developer.")

    # Agent Upgrade Settings
    agent_upgrade_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Amount charged to upgrade to agent status.")
    agent_upgrade_kyc_required = models.BooleanField(default=False, help_text="If enabled, user must be KYC verified to upgrade to agent.")
    
    # Product margins
    data_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    airtime_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tv_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    electricity_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    internet_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    education_margin = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        # Synchronize old and new charge fields for backward compatibility
        # Case 1: If new fields are set, they should update the old fields
        if self.deposit_charge_fixed and self.deposit_charge_fixed != 0:
            self.crediting_charge = self.deposit_charge_fixed
        if self.withdrawal_charge_fixed and self.withdrawal_charge_fixed != 0:
            self.withdrawal_charge = self.withdrawal_charge_fixed
            
        # Case 2: If old fields are set but new ones are zero, populate new ones
        if self.crediting_charge and self.crediting_charge != 0 and (self.deposit_charge_fixed == 0 and self.deposit_charge_percentage == 0):
            self.deposit_charge_fixed = self.crediting_charge
        if self.withdrawal_charge and self.withdrawal_charge != 0 and (self.withdrawal_charge_fixed == 0 and self.withdrawal_charge_percentage == 0):
            self.withdrawal_charge_fixed = self.withdrawal_charge

        if not self.pk and SiteConfig.objects.exists():
            # Return either existing instance or None, don't allow double creation.
            return 
        return super(SiteConfig, self).save(*args, **kwargs)

class ServiceCashback(models.Model):
    SERVICE_CHOICES = [
        ('airtime', 'Airtime'),
        ('data', 'Data'),
        ('tv', 'TV'),
        ('electricity', 'Electricity'),
        ('education', 'Education'),
        ('internet', 'Internet'),
    ]
    CASHBACK_TYPE_CHOICES = [
        ('flat', 'Flat Amount'),
        ('percentage', 'Percentage (%)'),
    ]
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES, unique=True)
    cashback_type = models.CharField(max_length=20, choices=CASHBACK_TYPE_CHOICES, default='flat')
    cashback_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    min_purchase_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_service_type_display()} Cashback: {self.cashback_value} ({self.cashback_type})"


class SystemTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("CASHOUT", "Cashout (Paystack to Bank)"),
        ("VTU_FUNDING", "VTU Wallet Funding"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    reference = models.CharField(max_length=100, unique=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} ({self.status})"

    class Meta:
        ordering = ["-created_at"]
