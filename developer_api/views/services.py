from rest_framework import generics, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from orders.models import (
    AirtimeNetwork, DataService, DataVariation, 
    ElectricityService, TVService, InternetService, 
    EducationService, EducationVariation, TVVariation,
    InternetVariation, ElectricityVariation
)
from .serializers import (
    DeveloperCategoryListResponseSerializer,
    DeveloperAirtimeNetworkResponseSerializer,
    DeveloperDataNetworkResponseSerializer,
    DeveloperDataPlanResponseSerializer,
    DeveloperTVServiceResponseSerializer,
    DeveloperTVPackageResponseSerializer,
    DeveloperElectricityServiceResponseSerializer,
    DeveloperElectricityVariationResponseSerializer,
    DeveloperInternetServiceResponseSerializer,
    DeveloperInternetPlanResponseSerializer,
    DeveloperEducationServiceResponseSerializer,
    DeveloperEducationVariationResponseSerializer
)
from orders.serializers.variations import resolve_price
from ..authentication import APIKeyAuthentication
from ..permissions import IsDeveloperUser


def get_routed_provider(service):
    """Returns the primary provider for the given service type from ServiceRouting, or None."""
    from orders.models import ServiceRouting
    routing = ServiceRouting.objects.filter(service=service).select_related('primary_provider').first()
    if routing and routing.primary_provider:
        return routing.primary_provider
    return None


def get_api_prices(obj, service_name):
    """
    Returns api_seller_price and api_discount with conditional priority:
    - If developer_price (api_seller_price) is set and non-zero, show it and null out api_discount.
    - Otherwise, show api_discount only.
    """
    api_seller_price = resolve_price(obj, 'developer', service_name)
    raw_discount = getattr(obj, 'agent_discount', None) or getattr(obj, 'discount', None)
    try:
        api_discount = float(raw_discount) if raw_discount is not None else None
    except (TypeError, ValueError):
        api_discount = None

    if api_seller_price and float(api_seller_price) != 0.0:
        return {"api_seller_price": api_seller_price, "api_discount": None}
    elif api_discount:
        return {"api_seller_price": None, "api_discount": api_discount}
    return {"api_seller_price": api_seller_price, "api_discount": None}


@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperCategoryListResponseSerializer}
)
class DeveloperServiceListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        """Returns all categories of services available"""
        return Response({
            "categories": [
                {"id": "airtime", "name": "Airtime Purchase", "endpoint": "/api/v1/developer/airtime/networks/"},
                {"id": "data", "name": "Data Bundles", "endpoint": "/api/v1/developer/data/networks/"},
                {"id": "electricity", "name": "Electricity Bills", "endpoint": "/api/v1/developer/electricity/services/"},
                {"id": "cable", "name": "Cable TV Subscription", "endpoint": "/api/v1/developer/cable/services/"},
                {"id": "internet", "name": "Internet Subscription", "endpoint": "/api/v1/developer/internet/services/"},
                {"id": "education", "name": "Education Pins", "endpoint": "/api/v1/developer/education/services/"},
            ]
        })

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperAirtimeNetworkResponseSerializer(many=True)}
)
class DeveloperAirtimeNetworkListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        qs = AirtimeNetwork.objects.filter(is_active=True)
        provider = get_routed_provider('airtime')
        if provider:
            qs = qs.filter(provider=provider)
        data = []
        for n in qs.order_by('id'):
            prices = get_api_prices(n, 'airtime')
            data.append({
                "id": n.id,
                "service_id": n.service_id,
                "name": n.service_name,
                "min_amount": n.min_amount,
                "max_amount": n.max_amount,
                "normal_price": resolve_price(n, 'customer', 'airtime'),
                "api_seller_price": prices["api_seller_price"],
                "api_discount": prices["api_discount"],
            })
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperDataNetworkResponseSerializer(many=True)}
)
class DeveloperDataNetworkListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        qs = DataService.objects.filter(is_active=True)
        provider = get_routed_provider('data')
        if provider:
            qs = qs.filter(provider=provider)
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in qs.order_by('id')]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperDataPlanResponseSerializer(many=True)}
)
class DeveloperDataPlanListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, network_id):
        qs = DataVariation.objects.filter(service_id=network_id, is_active=True)
        provider = get_routed_provider('data')
        if provider:
            qs = qs.filter(service__provider=provider)
        data = []
        for p in qs.order_by('id'):
            prices = get_api_prices(p, 'data')
            data.append({
                "id": p.id,
                "variation_id": p.variation_id,
                "name": p.name,
                "normal_price": resolve_price(p, 'customer', 'data'),
                "api_seller_price": prices["api_seller_price"],
                "api_discount": prices["api_discount"],
                "plan_type": p.plan_type,
                "last_updated": p.updated_at,
            })
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperTVServiceResponseSerializer(many=True)}
)
class DeveloperTVServiceListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        qs = TVService.objects.filter(is_active=True)
        provider = get_routed_provider('tv')
        if provider:
            qs = qs.filter(provider=provider)
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in qs.order_by('id')]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperTVPackageResponseSerializer(many=True)}
)
class DeveloperTVPackageListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        qs = TVVariation.objects.filter(service_id=service_id, is_active=True)
        provider = get_routed_provider('tv')
        if provider:
            qs = qs.filter(service__provider=provider)
        data = []
        for v in qs.order_by('id'):
            prices = get_api_prices(v, 'tv')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "normal_price": resolve_price(v, 'customer', 'tv'),
                "api_seller_price": prices["api_seller_price"],
                "api_discount": prices["api_discount"],
                "last_updated": v.updated_at,
            })
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperElectricityServiceResponseSerializer(many=True)}
)
class DeveloperElectricityServiceListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        qs = ElectricityService.objects.filter(is_active=True)
        provider = get_routed_provider('electricity')
        if provider:
            qs = qs.filter(provider=provider)
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in qs.order_by('id')]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperElectricityVariationResponseSerializer(many=True)}
)
class DeveloperElectricityVariationListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        qs = ElectricityVariation.objects.filter(service_id=service_id, is_active=True)
        provider = get_routed_provider('electricity')
        if provider:
            qs = qs.filter(service__provider=provider)
        data = []
        for v in qs.order_by('id'):
            prices = get_api_prices(v, 'electricity')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "min_amount": v.min_amount,
                "max_amount": v.max_amount,
                "normal_price": resolve_price(v, 'customer', 'electricity'),
                "api_seller_price": prices["api_seller_price"],
                "api_discount": prices["api_discount"],
                "last_updated": v.updated_at,
            })
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperInternetServiceResponseSerializer(many=True)}
)
class DeveloperInternetServiceListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        qs = InternetService.objects.filter(is_active=True)
        provider = get_routed_provider('internet')
        if provider:
            qs = qs.filter(provider=provider)
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in qs.order_by('id')]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperInternetPlanResponseSerializer(many=True)}
)
class DeveloperInternetPlanListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        qs = InternetVariation.objects.filter(service_id=service_id, is_active=True)
        provider = get_routed_provider('internet')
        if provider:
            qs = qs.filter(service__provider=provider)
        data = []
        for v in qs.order_by('id'):
            prices = get_api_prices(v, 'internet')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "normal_price": resolve_price(v, 'customer', 'internet'),
                "api_seller_price": prices["api_seller_price"],
                "api_discount": prices["api_discount"],
                "last_updated": v.updated_at,
            })
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperEducationServiceResponseSerializer(many=True)}
)
class DeveloperEducationServiceListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        qs = EducationService.objects.filter(is_active=True)
        provider = get_routed_provider('education')
        if provider:
            qs = qs.filter(provider=provider)
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in qs.order_by('id')]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperEducationVariationResponseSerializer(many=True)}
)
class DeveloperEducationVariationListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        qs = EducationVariation.objects.filter(service_id=service_id, is_active=True)
        provider = get_routed_provider('education')
        if provider:
            qs = qs.filter(service__provider=provider)
        data = []
        for v in qs.order_by('id'):
            prices = get_api_prices(v, 'education')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "normal_price": resolve_price(v, 'customer', 'education'),
                "api_seller_price": prices["api_seller_price"],
                "api_discount": prices["api_discount"],
                "last_updated": v.updated_at,
            })
        return Response(data)

