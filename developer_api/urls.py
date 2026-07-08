from django.urls import path
from .views.auth import (
    UpgradeToDeveloperView, DeveloperDetailsView, RegenerateAPIKeyView,
    DeveloperLoginView, WalletFundingDetailsView, DeveloperWebhookUpdateView
)
from .views.services import (
    DeveloperServiceListView, DeveloperAirtimeNetworkListView,
    DeveloperDataNetworkListView, DeveloperDataPlanListView,
    DeveloperTVServiceListView, DeveloperTVPackageListView,
    DeveloperElectricityServiceListView, DeveloperElectricityVariationListView,
    DeveloperInternetServiceListView, DeveloperInternetPlanListView,
    DeveloperEducationServiceListView, DeveloperEducationVariationListView
)
from .views.purchase import DeveloperPurchaseView, DeveloperVerifyPurchaseView

urlpatterns = [
    # Auth & Account
    path('login/', DeveloperLoginView.as_view(), name='developer-login'),
    path('upgrade/', UpgradeToDeveloperView.as_view(), name='developer-upgrade'),
    path('profile/', DeveloperDetailsView.as_view(), name='developer-profile'),
    path('funding-details/', WalletFundingDetailsView.as_view(), name='developer-funding-details'),
    path('webhook/update/', DeveloperWebhookUpdateView.as_view(), name='developer-webhook-update'),
    path('keys/regenerate/', RegenerateAPIKeyView.as_view(), name='developer-keys-regenerate'),
    
    # Discovery
    path('services/', DeveloperServiceListView.as_view(), name='developer-service-list'),
    path('airtime/networks/', DeveloperAirtimeNetworkListView.as_view(), name='developer-airtime-networks'),
    path('data/networks/', DeveloperDataNetworkListView.as_view(), name='developer-data-networks'),
    path('data/networks/<int:network_id>/plans/', DeveloperDataPlanListView.as_view(), name='developer-data-plans'),
    path('tv/services/', DeveloperTVServiceListView.as_view(), name='developer-tv-services'),
    path('tv/services/<int:service_id>/packages/', DeveloperTVPackageListView.as_view(), name='developer-tv-packages'),
    path('electricity/services/', DeveloperElectricityServiceListView.as_view(), name='developer-electricity-services'),
    path('electricity/services/<int:service_id>/variations/', DeveloperElectricityVariationListView.as_view(), name='developer-electricity-variations'),
    path('internet/services/', DeveloperInternetServiceListView.as_view(), name='developer-internet-services'),
    path('internet/services/<int:service_id>/plans/', DeveloperInternetPlanListView.as_view(), name='developer-internet-plans'),
    path('education/services/', DeveloperEducationServiceListView.as_view(), name='developer-education-services'),
    path('education/services/<int:service_id>/variations/', DeveloperEducationVariationListView.as_view(), name='developer-education-variations'),
    
    # Transactions
    path('purchase/', DeveloperPurchaseView.as_view(), name='developer-purchase'),
    path('verify/<str:reference>/', DeveloperVerifyPurchaseView.as_view(), name='developer-verify'),
]

