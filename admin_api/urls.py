from admin_api.views import BulkVariationUpdatePriceView
from admin_api.views import VariationUpdatePriceView
from admin_api.views import FetchFromProviderView
from admin_api.views import ProviderBalanceView
from admin_api.views import VTUOverviewView
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminDashboardStatsView,
    AdminMaintenanceModeView,
    AdminRefreshServicesView,
    AdminPauseServiceView,
    AdminUserViewSet, 
    AdminKYCViewSet,
    AdminWalletTransactionViewSet,
    AdminDepositViewSet,
    AdminWithdrawalViewSet,
    AdminPaystackConfigViewSet,
    AdminPurchaseViewSet,
    AdminSupportTicketViewSet,
    AdminVTUProviderConfigViewSet,
    AdminServiceRoutingViewSet,
    AdminDataVariationViewSet, AdminDataServiceViewSet,
    AdminTVVariationViewSet, AdminTVServiceViewSet,
    AdminAirtimeNetworkViewSet,
    AdminInternetVariationViewSet, AdminInternetServiceViewSet,
    AdminEducationVariationViewSet, AdminEducationServiceViewSet,
    AdminElectricityVariationViewSet, AdminElectricityServiceViewSet,
    AdminBeneficiaryViewSet,
    AdminInitiateTransferView,
    AdminTransferLogView,
    AdminNotificationViewSet,
    AdminAnnouncementViewSet,
    AdminNotificationTemplateViewSet,
    # New Views
    AutomationConfigView, AutomationGlobalSettingsView, ServiceRetryConfigView,
    ServiceFallbackToggleView, ServiceAutoRefundView, ServicePricingModeView,
    DetectDelayedTransactionsView, ProviderServiceConfigViewSet, AutoSyncConfigView, AutoSyncRunNowView,
    VariationToggleView, ServiceTypeToggleView, AdminAvailableVTUProvidersView, LiveCataloguePreviewView,
    # New views added today
    AdminWalletViewSet, AdminTransferViewSet, AdminTransferBeneficiaryViewSet,
    AdminPaystackDataViewSet, AdminReferralViewSet, AdminSiteConfigViewSet, AdminServiceCashbackViewSet,
    AdminExportUsersView, AdminExportWalletTransactionsView, AdminExportDepositsView, AdminExportWithdrawalsView, AdminExportPurchasesView,
    # Permissions & Groups
    AdminPermissionViewSet, AdminGroupViewSet, AdminUserPermissionView, AdminUserGroupView,
    AdminActionLogViewSet
)


router = DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'kyc', AdminKYCViewSet, basename='admin-kyc')
router.register(r'wallet/transactions', AdminWalletTransactionViewSet, basename='admin-wallet-transactions')
router.register(r'payments/deposits', AdminDepositViewSet, basename='admin-deposits')
router.register(r'payments/withdrawals', AdminWithdrawalViewSet, basename='admin-withdrawals')
router.register(r'settings/paystack', AdminPaystackConfigViewSet, basename='admin-paystack-config')
router.register(r'purchases', AdminPurchaseViewSet, basename='admin-purchases')
router.register(r'support', AdminSupportTicketViewSet, basename='admin-support')
router.register(r'vtu/providers', AdminVTUProviderConfigViewSet, basename='admin-vtu-providers')
router.register(r'vtu/routings', AdminServiceRoutingViewSet, basename='admin-vtu-routings')

router.register(r'pricing/airtime/networks', AdminAirtimeNetworkViewSet, basename='admin-pricing-airtime')
router.register(r'pricing/data/networks', AdminDataServiceViewSet, basename='admin-pricing-data-networks')
router.register(r'pricing/data/plans', AdminDataVariationViewSet, basename='admin-pricing-data-plans')
router.register(r'pricing/tv/networks', AdminTVServiceViewSet, basename='admin-pricing-tv-networks')
router.register(r'pricing/tv/plans', AdminTVVariationViewSet, basename='admin-pricing-tv-plans')
router.register(r'pricing/internet/networks', AdminInternetServiceViewSet, basename='admin-pricing-internet-networks')
router.register(r'pricing/internet/plans', AdminInternetVariationViewSet, basename='admin-pricing-internet-plans')
router.register(r'pricing/education/networks', AdminEducationServiceViewSet, basename='admin-pricing-education-networks')
router.register(r'pricing/education/plans', AdminEducationVariationViewSet, basename='admin-pricing-education-plans')
router.register(r'pricing/electricity/networks', AdminElectricityServiceViewSet, basename='admin-pricing-electricity-networks')
router.register(r'pricing/electricity/plans', AdminElectricityVariationViewSet, basename='admin-pricing-electricity-plans')

router.register(r'transfer/beneficiaries', AdminBeneficiaryViewSet, basename='admin-transfer-beneficiaries')
router.register(r'notifications/announcements', AdminAnnouncementViewSet, basename='admin-announcements')
router.register(r'notifications/templates', AdminNotificationTemplateViewSet, basename='admin-notification-templates')
router.register(r'notifications/logs', AdminNotificationViewSet, basename='admin-notifications')

router.register(r'vtu/provider-service-configs', ProviderServiceConfigViewSet, basename='admin-provider-service-configs')

# Comprehensive Admin Control Sets

router.register(r'wallets/all', AdminWalletViewSet, basename='admin-global-wallets')
router.register(r'admin-transfers/beneficiaries', AdminTransferBeneficiaryViewSet, basename='admin-transfers-beneficiaries')
router.register(r'admin-transfers/transactions', AdminTransferViewSet, basename='admin-transfers-transactions')
router.register(r'analytics/referrals', AdminReferralViewSet, basename='admin-referral-analytics')
router.register(r'settings/site-config', AdminSiteConfigViewSet, basename='admin-site-config')
router.register(r'settings/service-cashbacks', AdminServiceCashbackViewSet, basename='admin-service-cashbacks')
router.register(r'paystack/data', AdminPaystackDataViewSet, basename='admin-paystack-data')
router.register(r'permissions/all', AdminPermissionViewSet, basename='admin-permissions')
router.register(r'permissions/groups', AdminGroupViewSet, basename='admin-groups')
router.register(r'audit/action-logs', AdminActionLogViewSet, basename='admin-action-logs')

urlpatterns = [
    path('stats/', AdminDashboardStatsView.as_view(), name='admin-stats'),
    path('vtu/available-providers/', AdminAvailableVTUProvidersView.as_view(), name='admin-vtu-available-providers'),
    path('maintenance-mode/', AdminMaintenanceModeView.as_view(), name='admin-maintenance-mode'),
    path('refresh-services/', AdminRefreshServicesView.as_view(), name='admin-refresh-services'),
    path('pause-service/', AdminPauseServiceView.as_view(), name='admin-pause-service'),
    path('transfer/initiate/', AdminInitiateTransferView.as_view(), name='admin-transfer-initiate'),
    path('transfer/logs/', AdminTransferLogView.as_view(), name='admin-transfer-logs'),
    
    # Automation
    path('automation/config/', AutomationConfigView.as_view(), name='admin-automation-config'),
    path('automation/global-settings/', AutomationGlobalSettingsView.as_view(), name='admin-automation-global'),
    path('automation/auto-sync/', AutoSyncConfigView.as_view(), name='admin-auto-sync-config'),
    path('automation/auto-sync/run-now/', AutoSyncRunNowView.as_view(), name='admin-auto-sync-run-now'),
    path('automation/service/<str:service>/retry/', ServiceRetryConfigView.as_view(), name='admin-service-retry'),
    path('automation/service/<str:service>/fallback/', ServiceFallbackToggleView.as_view(), name='admin-service-fallback'),
    path('automation/service/<str:service>/auto-refund/', ServiceAutoRefundView.as_view(), name='admin-service-auto-refund'),
    path('automation/service/<str:service>/pricing-mode/', ServicePricingModeView.as_view(), name='admin-service-pricing-mode'),
    path('automation/detect-delayed/', DetectDelayedTransactionsView.as_view(), name='admin-detect-delayed'),

    # VTU Control Panel
    path('vtu/overview/', VTUOverviewView.as_view(), name='admin-vtu-overview'),
    path('vtu/live-catalogue/', LiveCataloguePreviewView.as_view(), name='admin-vtu-live-catalogue'),

    path('vtu/providers/<int:pk>/balance/', ProviderBalanceView.as_view(), name='admin-provider-balance'),
    path('vtu/fetch-from-provider/', FetchFromProviderView.as_view(), name='admin-vtu-fetch'),
    path('vtu/variations/<int:pk>/update-price/<str:service_type>/', VariationUpdatePriceView.as_view(), name='admin-vtu-variation-price'),
    path('vtu/variations/bulk-update-price/<str:service_type>/', BulkVariationUpdatePriceView.as_view(), name='admin-vtu-bulk-price'),
    path('vtu/variations/<int:pk>/toggle/<str:service_type>/', VariationToggleView.as_view(), name='admin-vtu-variation-toggle'),
    path('vtu/services/<str:service_type>/toggle/', ServiceTypeToggleView.as_view(), name='admin-vtu-service-toggle'),

    path('', include(router.urls)),
    path('reports/users/export/', AdminExportUsersView.as_view(), name='export-users'),
    path('reports/wallet-transactions/export/', AdminExportWalletTransactionsView.as_view(), name='export-wallet-transactions'),
    path('reports/deposits/export/', AdminExportDepositsView.as_view(), name='export-deposits'),
    path('reports/withdrawals/export/', AdminExportWithdrawalsView.as_view(), name='export-withdrawals'),
    path('reports/purchases/export/', AdminExportPurchasesView.as_view(), name='export-purchases'),

    # Permissions & Groups per-user management
    path('permissions/user/<str:identifier>/', AdminUserPermissionView.as_view(), name='admin-user-permissions'),
    path('permissions/user/<str:identifier>/groups/', AdminUserGroupView.as_view(), name='admin-user-groups'),
]
