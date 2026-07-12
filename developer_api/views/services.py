from rest_framework import generics, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

class DeveloperCategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    endpoint = serializers.CharField()

class DeveloperCategoryListResponseSerializer(serializers.Serializer):
    categories = DeveloperCategorySerializer(many=True)

class DeveloperAirtimeNetworkResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()
    min_amount = serializers.FloatField()
    max_amount = serializers.FloatField()
    normal_discount = serializers.FloatField()
    api_seller_discount = serializers.FloatField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField()

class DeveloperDataNetworkResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperDataPlanResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField()
    plan_type = serializers.CharField()

class DeveloperTVServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperTVPackageResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField()

class DeveloperElectricityServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperElectricityVariationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    min_amount = serializers.FloatField()
    max_amount = serializers.FloatField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField()

class DeveloperInternetServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperInternetPlanResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField()

class DeveloperEducationServiceResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    service_id = serializers.CharField()
    name = serializers.CharField()

class DeveloperEducationVariationResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variation_id = serializers.CharField()
    name = serializers.CharField()
    normal_price = serializers.FloatField()
    api_seller_price = serializers.FloatField()
from orders.models import (
    AirtimeNetwork, DataService, DataVariation, 
    ElectricityService, TVService, InternetService, 
    EducationService, EducationVariation, TVVariation,
    InternetVariation, ElectricityVariation
)
from orders.serializers.variations import resolve_price
from ..authentication import APIKeyAuthentication
from ..permissions import IsDeveloperUser

def get_resolved_prices(obj, service_name):
    return {
        "normal_price": resolve_price(obj, 'customer', service_name),
        "api_seller_price": resolve_price(obj, 'developer', service_name),
    }

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
        networks = AirtimeNetwork.objects.filter(is_active=True).order_by('id')
        data = [{
            "id": n.id,
            "service_id": n.service_id,
            "name": n.service_name,
            "min_amount": n.min_amount,
            "max_amount": n.max_amount,
            "normal_discount": float(n.discount),
            "api_seller_discount": float(n.agent_discount),
            "normal_price": resolve_price(n, 'customer', 'airtime'),
            "api_seller_price": resolve_price(n, 'developer', 'airtime'),
        } for n in networks]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperDataNetworkResponseSerializer(many=True)}
)
class DeveloperDataNetworkListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request):
        services = DataService.objects.filter(is_active=True).order_by('id')
        data = [{
            "id": s.id,
            "service_id": s.service_id,
            "name": s.service_name,
        } for s in services]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperDataPlanResponseSerializer(many=True)}
)
class DeveloperDataPlanListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, network_id):
        plans = DataVariation.objects.filter(service_id=network_id, is_active=True).order_by('id')
        data = []
        for p in plans:
            prices = get_resolved_prices(p, 'data')
            data.append({
                "id": p.id,
                "variation_id": p.variation_id,
                "name": p.name,
                "normal_price": prices["normal_price"],
                "api_seller_price": prices["api_seller_price"],
                "plan_type": p.plan_type
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
        services = TVService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperTVPackageResponseSerializer(many=True)}
)
class DeveloperTVPackageListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        variations = TVVariation.objects.filter(service_id=service_id, is_active=True).order_by('id')
        data = []
        for v in variations:
            prices = get_resolved_prices(v, 'tv')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "normal_price": prices["normal_price"],
                "api_seller_price": prices["api_seller_price"]
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
        services = ElectricityService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperElectricityVariationResponseSerializer(many=True)}
)
class DeveloperElectricityVariationListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        variations = ElectricityVariation.objects.filter(service_id=service_id, is_active=True).order_by('id')
        data = []
        for v in variations:
            prices = get_resolved_prices(v, 'electricity')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "min_amount": v.min_amount,
                "max_amount": v.max_amount,
                "normal_price": prices["normal_price"],
                "api_seller_price": prices["api_seller_price"]
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
        services = InternetService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperInternetPlanResponseSerializer(many=True)}
)
class DeveloperInternetPlanListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        variations = InternetVariation.objects.filter(service_id=service_id, is_active=True).order_by('id')
        data = []
        for v in variations:
            prices = get_resolved_prices(v, 'internet')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "normal_price": prices["normal_price"],
                "api_seller_price": prices["api_seller_price"]
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
        services = EducationService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

@extend_schema(
    tags=["Developer - Services"],
    responses={200: DeveloperEducationVariationResponseSerializer(many=True)}
)
class DeveloperEducationVariationListView(APIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, service_id):
        variations = EducationVariation.objects.filter(service_id=service_id, is_active=True).order_by('id')
        data = []
        for v in variations:
            prices = get_resolved_prices(v, 'education')
            data.append({
                "id": v.id,
                "variation_id": v.variation_id,
                "name": v.name,
                "normal_price": prices["normal_price"],
                "api_seller_price": prices["api_seller_price"]
            })
        return Response(data)
