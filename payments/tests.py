from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from summary.models import SiteConfig
from payments.models import Withdrawal
from payments.utils import calculate_net_withdrawal_amount
from users.models import StaffPermission

User = get_user_model()

from wallet.models import TransactionCharge
from decimal import Decimal

class WithdrawalCalculationTests(TestCase):
    def test_calculate_net_withdrawal_amount(self):
        net_amount, charge = calculate_net_withdrawal_amount(1000)
        self.assertEqual(net_amount, 1000.0)
        self.assertEqual(charge, 0.0)


class WithdrawalApprovalPinTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone_number="08011111111", password="pass", is_active=True)
        self.superuser = User.objects.create_superuser(phone_number="08022222222", password="superpassword123")
        self.staff_user = User.objects.create_user(phone_number="08033333333", password="staffpassword123", is_staff=True, is_active=True)
        self.staff_user.set_transaction_pin("1234")

        # Grant payment management permission to staff user
        StaffPermission.objects.create(user=self.staff_user, can_manage_payments=True)

        self.withdrawal = Withdrawal.objects.create(
            user=self.customer,
            amount=5000.00,
            bank_name="Access Bank",
            bank_code="044",
            account_number="0123456789",
            account_name="Customer User",
            reference="WTH-TEST-PIN-1"
        )

    @patch("payments.utils.PaystackGateway.initiate_transfer")
    def test_superuser_approval_requires_login_password(self, mock_transfer):
        mock_transfer.return_value = {"status": "SUCCESS", "transfer_code": "TRF_123"}
        self.client.force_login(self.superuser)

        # Invalid password
        res = self.client.post(f"/portal/payments/withdrawals/{self.withdrawal.pk}/approve/", {
            "action_type": "APPROVED",
            "admin_pin": "wrongpass"
        })
        self.assertEqual(res.status_code, 403)

        # Correct password passes PIN check
        res = self.client.post(f"/portal/payments/withdrawals/{self.withdrawal.pk}/approve/", {
            "action_type": "APPROVED",
            "admin_pin": "superpassword123"
        })
        self.assertEqual(res.status_code, 200)

    @patch("payments.utils.PaystackGateway.initiate_transfer")
    def test_staff_user_approval_requires_admin_pin(self, mock_transfer):
        mock_transfer.return_value = {"status": "SUCCESS", "transfer_code": "TRF_123"}
        self.client.force_login(self.staff_user)

        # Invalid PIN
        res = self.client.post(f"/portal/payments/withdrawals/{self.withdrawal.pk}/approve/", {
            "action_type": "APPROVED",
            "admin_pin": "9999"
        })
        self.assertEqual(res.status_code, 403)

        # Valid PIN
        res = self.client.post(f"/portal/payments/withdrawals/{self.withdrawal.pk}/approve/", {
            "action_type": "APPROVED",
            "admin_pin": "1234"
        })
        self.assertEqual(res.status_code, 200)
