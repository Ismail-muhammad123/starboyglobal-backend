from django.urls import path
from .views import (
    InitFundWallet, WalletDetailView, WalletTransactionDetailView, 
    WalletTransactionListView, VirtualAccountDetailView, BankListView, 
    ResolveAccountView, WalletTransferView, VerifyRecipientView,
    InitiateBankTransferView, TransferBeneficiaryListCreateView, 
    TransferBeneficiaryDeleteView, TransactionChargesView
)

urlpatterns = [
    # Wallet Core
    path('', WalletDetailView.as_view(), name='wallet-detail'),
    path('transactions/', WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('transactions/<int:pk>/', WalletTransactionDetailView.as_view(), name='wallet-transaction-detail'),
    path('deposit/', InitFundWallet.as_view(), name='initiate-deposit'),
    path('charges/', TransactionChargesView.as_view(), name='wallet-charges'),
    
    path('p2p-verify/', VerifyRecipientView.as_view(), name='p2p-verify'),
    
    # Financial Infrastructure
    path('virtual-account/', VirtualAccountDetailView.as_view(), name='virtual-account'),
    path('banks/', BankListView.as_view(), name='bank-list'),
    path('resolve-account/', ResolveAccountView.as_view(), name='resolve-account'),
    
    # Withdrawal & Bank Transfers
    path('withdraw-to-bank/', InitiateBankTransferView.as_view(), name='initiate-bank-transfer'),
    
    # Beneficiaries & P2P
    path('transfer-p2p/', WalletTransferView.as_view(), name='wallet-transfer-p2p'),
    path('beneficiaries/', TransferBeneficiaryListCreateView.as_view(), name='transfer-beneficiary-list-create'),
    path('beneficiaries/<int:pk>/', TransferBeneficiaryDeleteView.as_view(), name='transfer-beneficiary-delete'),
]

