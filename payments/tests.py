from django.test import TestCase
from summary.models import SiteConfig
from payments.utils import calculate_net_withdrawal_amount

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
