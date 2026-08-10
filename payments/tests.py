from django.test import TestCase
from django.contrib.auth import get_user_model
from summary.models import SiteConfig
from payments.models import Withdrawal
from payments.utils import calculate_net_withdrawal_amount

User = get_user_model()

class WithdrawalCalculationTests(TestCase):
    def test_calculate_net_withdrawal_amount_no_config(self):
        net_amount, charge = calculate_net_withdrawal_amount(1000)
        self.assertEqual(net_amount, 1000.0)
        self.assertEqual(charge, 0.0)

    def test_calculate_net_withdrawal_amount_with_charges(self):
        SiteConfig.objects.create(
            pk=1,
            withdrawal_charge_fixed=50.00,
            withdrawal_charge_percentage=1.00
        )
        net_amount, charge = calculate_net_withdrawal_amount(10000)
        # Fixed 50 + 1% of 10000 (100) = 150 total charge
        self.assertEqual(charge, 150.0)
        self.assertEqual(net_amount, 9850.0)

class WithdrawalApprovalPinTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(phone_number="08011111111", password="pass")
        self.superuser = User.objects.create_superuser(phone_number="08022222222", password="superpassword123")
        self.staff_user = User.objects.create_user(phone_number="08033333333", password="staffpassword123", is_staff=True)
        self.staff_user.transaction_pin = "1234"
        self.staff_user.save()

        self.withdrawal = Withdrawal.objects.create(
            user=self.customer,
            amount=5000.00,
            bank_name="Access Bank",
            bank_code="044",
            account_number="0123456789",
            account_name="Customer User",
            reference="WTH-TEST-PIN-1"
        )

    def test_superuser_approval_requires_login_password(self):
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
        # Passes authentication/PIN step
        self.assertNotEqual(res.status_code, 403)

    def test_staff_user_approval_requires_admin_pin(self):
        self.client.force_login(self.staff_user)

        # Invalid PIN
        res = self.client.post(f"/portal/payments/withdrawals/{self.withdrawal.pk}/approve/", {
            "action_type": "APPROVED",
            "admin_pin": "9999"
        })
        self.assertEqual(res.status_code, 403)
