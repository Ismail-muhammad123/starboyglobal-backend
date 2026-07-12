from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
# Register drf-spectacular OpenAPI extensions
import developer_api.openapi



urlpatterns = [
    path('', RedirectView.as_view(url='admin/', permanent=True)),
    path('admin/', admin.site.urls),
    path('api/account/', include("users.urls")),
    path('api/wallet/', include("wallet.urls")),
    path('api/payment/', include("payments.urls")),
    path('api/orders/', include("orders.urls")),
    path('api/summary/', include("summary.urls")),
    path('api/admin/', include("admin_api.urls")),
    path('api/support/', include("support.urls")),
    path('api/v1/developer/', include("developer_api.urls")),
    
    # SWAGGER
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),   
]


# Let WhiteNoise serve static files in all environments.
# Keep local media serving only for debug convenience.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
