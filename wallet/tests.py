from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from wallet.models import Wallet, WalletTransaction, TransactionCharge
from wallet.utils import (
    fund_wallet,
    debit_wallet,
    get_applicable_charges,
    calculate_charge_amount,
    calculate_total_charges,
    validate_balance_for_transaction,
    apply_charges,
    refund_charges
)

User = get_user_model()

class TransactionChargeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="08012345678",
            email="testuser@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User"
        )
        self.wallet, _ = Wallet.objects.get_or_create(user=self.user, defaults={'balance': 0.0})

    def test_flat_charge_calculation(self):
        charge = TransactionCharge.objects.create(
            name="Flat Deposit Fee",
            transaction_type="deposit",
            charge_type="flat",
            amount=Decimal("50.00"),
            min_transaction_amount=Decimal("100.00"),
        )
        self.assertIsNone(charge.cap)
        fee = calculate_charge_amount(charge, Decimal("500.00"))
        self.assertEqual(fee, Decimal("50.00"))

    def test_percentage_charge_with_cap(self):
        charge = TransactionCharge.objects.create(
            name="Percentage Transfer Fee",
            transaction_type="transfer_others",
            charge_type="percentage",
            amount=Decimal("1.50"), # 1.5%
            cap=Decimal("100.00"),
            min_transaction_amount=Decimal("100.00"),
        )
        # 1.5% of 5,000 = 75.00 (under cap 100)
        fee1 = calculate_charge_amount(charge, Decimal("5000.00"))
        self.assertEqual(fee1, Decimal("75.00"))

        # 1.5% of 10,000 = 150.00 (capped at 100.00)
        fee2 = calculate_charge_amount(charge, Decimal("10000.00"))
        self.assertEqual(fee2, Decimal("100.00"))

    def test_min_and_max_transaction_amount_applicability(self):
        TransactionCharge.objects.create(
            name="Tier 1 Charge",
            transaction_type="transfer_p2p",
            charge_type="flat",
            amount=Decimal("20.00"),
            min_transaction_amount=Decimal("100.00"),
            max_transaction_amount=Decimal("1000.00"),
        )
        TransactionCharge.objects.create(
            name="Tier 2 Charge",
            transaction_type="transfer_p2p",
            charge_type="flat",
            amount=Decimal("50.00"),
            min_transaction_amount=Decimal("1000.01"),
            max_transaction_amount=None, # no max
        )

        # Below min
        charges_below = get_applicable_charges("transfer_p2p", Decimal("50.00"))
        self.assertEqual(len(charges_below), 0)

        # Tier 1
        charges_t1 = get_applicable_charges("transfer_p2p", Decimal("500.00"))
        self.assertEqual(len(charges_t1), 1)
        self.assertEqual(charges_t1[0].name, "Tier 1 Charge")

        # Tier 2
        charges_t2 = get_applicable_charges("transfer_p2p", Decimal("2000.00"))
        self.assertEqual(len(charges_t2), 1)
        self.assertEqual(charges_t2[0].name, "Tier 2 Charge")

    def test_apply_charges_creates_separate_debit(self):
        fund_wallet(self.user.id, Decimal("1000.00"))
        charge = TransactionCharge.objects.create(
            name="P2P Fee",
            transaction_type="transfer_p2p",
            charge_type="flat",
            amount=Decimal("30.00"),
            min_transaction_amount=Decimal("100.00"),
            block_if_insufficient=True
        )
        _, parent_tx = debit_wallet(self.user.id, Decimal("500.00"), description="P2P Transfer", return_tx=True)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("500.00"))

        charge_txs = apply_charges(self.user.id, "transfer_p2p", Decimal("500.00"), parent_wallet_tx=parent_tx)
        self.assertEqual(len(charge_txs), 1)
        self.assertEqual(charge_txs[0].charge_for, parent_tx)
        self.assertTrue(charge_txs[0].is_charge)
        self.assertFalse(charge_txs[0].is_refunded)

        self.wallet.refresh_from_db()
        # 500 - 30 = 470
        self.assertEqual(self.wallet.balance, Decimal("470.00"))

    def test_block_if_insufficient_true_raises_error(self):
        fund_wallet(self.user.id, Decimal("100.00"))
        TransactionCharge.objects.create(
            name="Strict Charge",
            transaction_type="transfer_others",
            charge_type="flat",
            amount=Decimal("50.00"),
            block_if_insufficient=True
        )

        is_valid, total_req, err = validate_balance_for_transaction(self.user.id, "transfer_others", Decimal("80.00"))
        self.assertFalse(is_valid)
        self.assertEqual(total_req, Decimal("130.00"))

    def test_block_if_insufficient_false_skips_charge(self):
        fund_wallet(self.user.id, Decimal("100.00"))
        charge = TransactionCharge.objects.create(
            name="Optional Charge",
            transaction_type="transfer_others",
            charge_type="flat",
            amount=Decimal("50.00"),
            block_if_insufficient=False
        )

        # Debit the entire 100 balance
        _, parent_tx = debit_wallet(self.user.id, Decimal("100.00"), return_tx=True)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

        # apply_charges should gracefully skip the charge without raising error
        charge_txs = apply_charges(self.user.id, "transfer_others", Decimal("100.00"), parent_wallet_tx=parent_tx)
        self.assertEqual(len(charge_txs), 0)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))

    def test_refund_charges_is_idempotent(self):
        fund_wallet(self.user.id, Decimal("1000.00"))
        TransactionCharge.objects.create(
            name="Transfer Fee",
            transaction_type="transfer_others",
            charge_type="flat",
            amount=Decimal("50.00"),
        )
        _, parent_tx = debit_wallet(self.user.id, Decimal("400.00"), return_tx=True)
        charge_txs = apply_charges(self.user.id, "transfer_others", Decimal("400.00"), parent_wallet_tx=parent_tx)
        self.assertEqual(len(charge_txs), 1)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("550.00"))

        # Refund 1: Should refund 50.00
        refunded = refund_charges(parent_tx)
        self.assertEqual(len(refunded), 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("600.00"))

        # Refund 2: Should do nothing (idempotent)
        refunded_again = refund_charges(parent_tx)
        self.assertEqual(len(refunded_again), 0)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("600.00"))


from rest_framework.test import APIClient
from rest_framework import status


class WalletChargesAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number="08099887766",
            email="charges_test@example.com",
            password="testpassword123",
            first_name="Charges",
            last_name="Tester"
        )
        self.client.force_authenticate(user=self.user)

        # Create charge rules
        TransactionCharge.objects.create(
            name="P2P Flat Charge",
            transaction_type="transfer_p2p",
            charge_type="flat",
            amount=Decimal("25.00"),
            min_transaction_amount=Decimal("100.00"),
            block_if_insufficient=True,
            is_active=True
        )
        TransactionCharge.objects.create(
            name="Deposit Percent Charge",
            transaction_type="deposit",
            charge_type="percentage",
            amount=Decimal("1.50"),
            cap=Decimal("200.00"),
            min_transaction_amount=Decimal("500.00"),
            block_if_insufficient=False,
            is_active=True
        )

    def test_get_charges_p2p(self):
        response = self.client.get("/api/wallet/charges/", {
            "transaction_type": "transfer_p2p",
            "amount": "5000.00"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["transaction_type"], "transfer_p2p")
        self.assertEqual(data["amount"], "5000.00")
        self.assertEqual(data["total_charge"], "25.00")
        self.assertEqual(data["total_required"], "5025.00")
        self.assertEqual(len(data["charges"]), 1)
        self.assertEqual(data["charges"][0]["name"], "P2P Flat Charge")
        self.assertEqual(data["charges"][0]["computed_amount"], "25.00")

    def test_get_charges_deposit_percentage_capped(self):
        # 1.5% of 20,000 = 300, capped at 200
        response = self.client.get("/api/wallet/charges/", {
            "transaction_type": "deposit",
            "amount": "20000.00"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["transaction_type"], "deposit")
        self.assertEqual(data["amount"], "20000.00")
        self.assertEqual(data["total_charge"], "200.00")
        self.assertEqual(data["total_required"], "20200.00")
        self.assertEqual(len(data["charges"]), 1)
        self.assertEqual(data["charges"][0]["name"], "Deposit Percent Charge")
        self.assertEqual(data["charges"][0]["computed_amount"], "200.00")

    def test_post_charges_endpoint(self):
        response = self.client.post("/api/wallet/charges/", {
            "transaction_type": "transfer_p2p",
            "amount": 2500.00
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["transaction_type"], "transfer_p2p")
        self.assertEqual(data["amount"], "2500.00")
        self.assertEqual(data["total_charge"], "25.00")
        self.assertEqual(data["total_required"], "2525.00")

    def test_charges_below_min_amount(self):
        # Amount 50 is below min_transaction_amount 100
        response = self.client.get("/api/wallet/charges/", {
            "transaction_type": "transfer_p2p",
            "amount": "50.00"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_charge"], "0.00")
        self.assertEqual(data["total_required"], "50.00")
        self.assertEqual(len(data["charges"]), 0)

    def test_invalid_transaction_type(self):
        response = self.client.get("/api/wallet/charges/", {
            "transaction_type": "invalid_type",
            "amount": "1000.00"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_request_rejected(self):
        unauth_client = APIClient()
        response = unauth_client.get("/api/wallet/charges/", {
            "transaction_type": "transfer_p2p",
            "amount": "1000.00"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

