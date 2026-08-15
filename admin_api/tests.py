from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from decimal import Decimal
from wallet.models import TransactionCharge

User = get_user_model()

class AdminTransactionChargeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            phone_number="08099998888",
            email="admin@example.com",
            password="adminpassword123",
            first_name="Super",
            last_name="Admin"
        )
        self.client.force_authenticate(user=self.admin)

    def test_create_and_list_transaction_charge(self):
        payload = {
            "name": "Standard Deposit Charge",
            "transaction_type": "deposit",
            "charge_type": "flat",
            "amount": "100.00",
            "min_transaction_amount": "500.00",
            "max_transaction_amount": "50000.00",
            "block_if_insufficient": False,
            "is_active": True
        }
        res = self.client.post("/api/admin/settings/transaction-charges/", payload)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["name"], "Standard Deposit Charge")

        list_res = self.client.get("/api/admin/settings/transaction-charges/")
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(len(list_res.data["results"] if "results" in list_res.data else list_res.data), 1)

    def test_calculate_charges_preview_endpoint(self):
        TransactionCharge.objects.create(
            name="Bank Transfer Base Fee",
            transaction_type="transfer_others",
            charge_type="percentage",
            amount=Decimal("2.00"), # 2%
            cap=Decimal("200.00"),
            min_transaction_amount=Decimal("100.00"),
        )
        TransactionCharge.objects.create(
            name="Bank Transfer Stamp Duty",
            transaction_type="transfer_others",
            charge_type="flat",
            amount=Decimal("50.00"),
            min_transaction_amount=Decimal("1000.00"),
        )

        # For 5,000 transfer:
        # Fee 1: 2% of 5,000 = 100.00 (under cap 200)
        # Fee 2: 50.00 flat (since 5000 >= 1000)
        # Total charges = 150.00, Net = 5150.00
        calc_payload = {
            "transaction_type": "transfer_others",
            "amount": "5000.00"
        }
        res = self.client.post("/api/admin/settings/transaction-charges/calculate/", calc_payload)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Decimal(str(res.data["total_charge"])), Decimal("150.00"))
        self.assertEqual(Decimal(str(res.data["net_amount"])), Decimal("5150.00"))
        self.assertEqual(len(res.data["charges"]), 2)
