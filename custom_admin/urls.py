from django.urls import path
from custom_admin.views.auth import PortalLoginView, PortalLogoutView
from custom_admin.views.dashboard import (
    DashboardView, RevenueChartDataView, DashboardStatsApiView, DashboardServiceStatsApiView,
    DashboardProvidersApiView, DashboardOverviewExtraApiView
)
from custom_admin.views.users import (
    UserListView, UserDetailView, UserEditView, UserSuspendView, UserRoleUpdateView, UserPermissionsUpdateView,
    KYCListView, KYCDetailView, KYCApproveView
)
from custom_admin.views.purchases import (
    PurchaseListView, PurchaseDetailView, PurchaseRefundView, ManualPurchaseView,
    ManualPurchaseOptionsView, ManualRecipientVerifyView
)
from custom_admin.views.services import (
    AirtimeNetworkListView, AirtimeNetworkDetailView, AirtimeNetworkCreateView,
    DataServiceListView, DataServiceDetailView, DataServiceCreateView,
    DataVariationListView, DataVariationDetailView, DataVariationCreateView,
    TVServiceListView, TVServiceDetailView, TVVariationListView, TVVariationDetailView,
    ElectricityServiceListView, ElectricityServiceDetailView, ElectricityVariationListView, ElectricityVariationDetailView,
    InternetServiceListView, InternetServiceDetailView, InternetVariationListView, InternetVariationDetailView,
    EducationServiceListView, EducationServiceDetailView, EducationVariationListView, EducationVariationDetailView,
    BulkVariationActionView
)
from custom_admin.views.providers import (
    ProviderListView, ProviderDetailView, ProviderCreateView, ProviderServiceConfigListView,
    ProviderServiceConfigConfigureView, ServiceRoutingListView, ProviderSyncTriggerView, ServiceRoutingCreateView
)
from custom_admin.views.wallet import (
    WalletListView, WalletDetailView, TransactionListView, ManualTransactionView, WalletUserLookupView
)
from custom_admin.views.payments import (
    DepositListView, DepositDetailView, WithdrawalListView, WithdrawalDetailView, WithdrawalApproveView,
    AdminTransferListView, PaystackRecordsView, AdminBankListView, AdminAccountResolveView
)
from custom_admin.views.automation import (
    SyncScheduleListView, SyncScheduleToggleView, SyncLogListView, ManualSyncTriggerView
)
from custom_admin.views.reports import ReportsIndexView
from custom_admin.views.settings import (
    SiteConfigView, PaystackConfigView, ReferralConfigView, RoleUpgradeConfigView,
    CashbackConfigView, PromoCodesView
)
from custom_admin.views.staff import (
    StaffListView, PortalGroupListView, PortalGroupDetailView
)
from custom_admin.views.support import (
    SupportListView, SupportDetailView
)
from custom_admin.views.notifications import (
    SendNotificationView, NotificationLogView,
    AnnouncementListView, AnnouncementCreateView, AnnouncementEditView,
    AnnouncementToggleView, AnnouncementDeleteView
)

app_name = 'custom_admin'

urlpatterns = [
    # Auth & Shell
    path('login/', PortalLoginView.as_view(), name='login'),
    path('logout/', PortalLogoutView.as_view(), name='logout'),
    path('', DashboardView.as_view(), name='dashboard'),
    path('api/chart/revenue/', RevenueChartDataView.as_view(), name='chart_revenue'),
    path('api/dashboard/stats/', DashboardStatsApiView.as_view(), name='api_dashboard_stats'),
    path('api/dashboard/service-stats/', DashboardServiceStatsApiView.as_view(), name='api_dashboard_service_stats'),
    path('api/dashboard/providers/', DashboardProvidersApiView.as_view(), name='api_dashboard_providers'),
    path('api/dashboard/overview-extra/', DashboardOverviewExtraApiView.as_view(), name='api_dashboard_overview_extra'),

    # Users & KYC
    path('users/', UserListView.as_view(), name='users_list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='users_detail'),
    path('users/<int:pk>/edit/', UserEditView.as_view(), name='user_edit'),
    path('users/<int:pk>/permissions/', UserPermissionsUpdateView.as_view(), name='user_permissions_update'),
    path('users/<int:pk>/suspend/', UserSuspendView.as_view(), name='user_suspend'),
    path('users/<int:pk>/role/', UserRoleUpdateView.as_view(), name='user_role_update'),
    path('kyc/', KYCListView.as_view(), name='kyc_list'),
    path('kyc/<int:pk>/', KYCDetailView.as_view(), name='kyc_detail'),
    path('kyc/<int:pk>/approve/', KYCApproveView.as_view(), name='kyc_approve'),

    # Purchases
    path('purchases/', PurchaseListView.as_view(), name='purchases_list'),
    path('purchases/manual/', ManualPurchaseView.as_view(), name='manual_purchase'),
    path('purchases/manual-options/', ManualPurchaseOptionsView.as_view(), name='manual_purchase_options'),
    path('purchases/verify-recipient/', ManualRecipientVerifyView.as_view(), name='verify_recipient'),
    path('purchases/<int:pk>/', PurchaseDetailView.as_view(), name='purchases_detail'),
    path('purchases/<int:pk>/refund/', PurchaseRefundView.as_view(), name='purchase_refund'),

    # Services - Bulk Action
    path('services/bulk-action/', BulkVariationActionView.as_view(), name='bulk_variation_action'),

    # Services - Airtime
    path('services/airtime/networks/', AirtimeNetworkListView.as_view(), name='airtime_networks'),
    path('services/airtime/networks/add/', AirtimeNetworkCreateView.as_view(), name='airtime_network_create'),
    path('services/airtime/networks/<int:pk>/', AirtimeNetworkDetailView.as_view(), name='airtime_network_detail'),

    # Services - Data
    path('services/data/', DataServiceListView.as_view(), name='data_services'),
    path('services/data/add/', DataServiceCreateView.as_view(), name='data_service_create'),
    path('services/data/<int:pk>/', DataServiceDetailView.as_view(), name='data_service_detail'),
    path('services/data/plans/', DataVariationListView.as_view(), name='data_variations'),
    path('services/data/plans/add/', DataVariationCreateView.as_view(), name='data_variation_create'),
    path('services/data/plans/<int:pk>/', DataVariationDetailView.as_view(), name='data_variation_detail'),

    # Services - TV
    path('services/tv/', TVServiceListView.as_view(), name='tv_services'),
    path('services/tv/<int:pk>/', TVServiceDetailView.as_view(), name='tv_service_detail'),
    path('services/tv/variations/', TVVariationListView.as_view(), name='tv_variations'),
    path('services/tv/variations/<int:pk>/', TVVariationDetailView.as_view(), name='tv_variation_detail'),

    # Services - Electricity
    path('services/electricity/', ElectricityServiceListView.as_view(), name='electricity_services'),
    path('services/electricity/<int:pk>/', ElectricityServiceDetailView.as_view(), name='electricity_service_detail'),
    path('services/electricity/variations/', ElectricityVariationListView.as_view(), name='electricity_variations'),
    path('services/electricity/variations/<int:pk>/', ElectricityVariationDetailView.as_view(), name='electricity_variation_detail'),

    # Services - Internet
    path('services/internet/', InternetServiceListView.as_view(), name='internet_services'),
    path('services/internet/<int:pk>/', InternetServiceDetailView.as_view(), name='internet_service_detail'),
    path('services/internet/variations/', InternetVariationListView.as_view(), name='internet_variations'),
    path('services/internet/variations/<int:pk>/', InternetVariationDetailView.as_view(), name='internet_variation_detail'),

    # Services - Education
    path('services/education/', EducationServiceListView.as_view(), name='education_services'),
    path('services/education/<int:pk>/', EducationServiceDetailView.as_view(), name='education_service_detail'),
    path('services/education/variations/', EducationVariationListView.as_view(), name='education_variations'),
    path('services/education/variations/<int:pk>/', EducationVariationDetailView.as_view(), name='education_variation_detail'),

    # VTU Providers & Margin Settings
    path('providers/', ProviderListView.as_view(), name='providers_list'),
    path('providers/add/', ProviderCreateView.as_view(), name='provider_add'),
    path('providers/<int:pk>/', ProviderDetailView.as_view(), name='provider_detail'),
    path('providers/<int:pk>/sync/', ProviderSyncTriggerView.as_view(), name='provider_sync'),
    path('providers/margins/', ProviderServiceConfigListView.as_view(), name='provider_service_configs'),
    path('providers/margins/configure/', ProviderServiceConfigConfigureView.as_view(), name='provider_service_config_configure'),
    path('providers/margins/<int:pk>/', ProviderServiceConfigListView.as_view(), name='provider_service_config_detail'),
    path('providers/margins/<int:pk>/edit/', ProviderServiceConfigConfigureView.as_view(), name='provider_service_config_edit'),
    path('providers/routing/', ServiceRoutingListView.as_view(), name='service_routings'),
    path('providers/routing/add/', ServiceRoutingCreateView.as_view(), name='service_routing_create'),
    path('providers/routing/<int:pk>/', ServiceRoutingListView.as_view(), name='service_routings_detail'),

    # Wallet & Finance
    path('wallets/', WalletListView.as_view(), name='wallets_list'),
    path('wallets/<int:pk>/', WalletDetailView.as_view(), name='wallet_detail'),
    path('wallets/transactions/', TransactionListView.as_view(), name='wallet_transactions'),
    path('wallets/manual-transaction/', ManualTransactionView.as_view(), name='manual_transaction'),
    path('wallets/user-lookup/', WalletUserLookupView.as_view(), name='wallet_user_lookup'),

    # Payments
    path('payments/deposits/', DepositListView.as_view(), name='deposits_list'),
    path('payments/deposits/<int:pk>/', DepositDetailView.as_view(), name='deposit_detail'),
    path('payments/withdrawals/', WithdrawalListView.as_view(), name='withdrawals_list'),
    path('payments/withdrawals/<int:pk>/', WithdrawalDetailView.as_view(), name='withdrawal_detail'),
    path('payments/withdrawals/<int:pk>/approve/', WithdrawalApproveView.as_view(), name='withdrawal_approve'),
    path('payments/transfers/', AdminTransferListView.as_view(), name='admin_transfers'),
    path('payments/banks/', AdminBankListView.as_view(), name='admin_bank_list'),
    path('payments/resolve-account/', AdminAccountResolveView.as_view(), name='admin_resolve_account'),
    path('payments/paystack-records/', PaystackRecordsView.as_view(), name='paystack_records'),

    # Automation
    path('automation/schedules/', SyncScheduleListView.as_view(), name='sync_schedules'),
    path('automation/schedules/<int:pk>/toggle/', SyncScheduleToggleView.as_view(), name='sync_schedule_toggle'),
    path('automation/logs/', SyncLogListView.as_view(), name='sync_logs'),
    path('automation/manual-trigger/', ManualSyncTriggerView.as_view(), name='manual_sync_trigger'),

    # Reports
    path('reports/', ReportsIndexView.as_view(), name='reports_index'),

    # Settings
    path('settings/site/', SiteConfigView.as_view(), name='site_config'),
    path('settings/paystack/', PaystackConfigView.as_view(), name='paystack_config'),
    path('settings/referrals/', ReferralConfigView.as_view(), name='referral_config'),
    path('settings/role-upgrades/', RoleUpgradeConfigView.as_view(), name='role_upgrade_config'),
    path('settings/cashback/', CashbackConfigView.as_view(), name='cashback_config'),
    path('settings/promo-codes/', PromoCodesView.as_view(), name='promo_codes'),

    # Administration (Superuser)
    path('staff/', StaffListView.as_view(), name='staff_list'),
    path('staff/groups/', PortalGroupListView.as_view(), name='groups_list'),
    path('staff/groups/<int:pk>/', PortalGroupDetailView.as_view(), name='group_detail'),

    # Support
    path('support/', SupportListView.as_view(), name='support_tickets'),
    path('support/<int:pk>/', SupportDetailView.as_view(), name='support_detail'),

    # Notifications
    path('notifications/send/', SendNotificationView.as_view(), name='send_notification'),
    path('notifications/log/', NotificationLogView.as_view(), name='notification_log'),
    path('notifications/announcements/', AnnouncementListView.as_view(), name='announcements_list'),
    path('notifications/announcements/create/', AnnouncementCreateView.as_view(), name='announcement_create'),
    path('notifications/announcements/<int:pk>/edit/', AnnouncementEditView.as_view(), name='announcement_edit'),
    path('notifications/announcements/<int:pk>/toggle/', AnnouncementToggleView.as_view(), name='announcement_toggle'),
    path('notifications/announcements/<int:pk>/delete/', AnnouncementDeleteView.as_view(), name='announcement_delete'),
]
