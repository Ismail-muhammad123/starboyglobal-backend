from rest_framework import generics, permissions, status
from rest_framework.response import Response
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

class DeveloperServiceListView(generics.GenericAPIView):
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

class DeveloperAirtimeNetworkListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def list(self, request):
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

class DeveloperDataNetworkListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def list(self, request):
        services = DataService.objects.filter(is_active=True).order_by('id')
        data = [{
            "id": s.id,
            "service_id": s.service_id,
            "name": s.service_name,
        } for s in services]
        return Response(data)

class DeveloperDataPlanListView(generics.ListAPIView):
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

class DeveloperTVServiceListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def list(self, request):
        services = TVService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

class DeveloperTVPackageListView(generics.ListAPIView):
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

class DeveloperElectricityServiceListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def list(self, request):
        services = ElectricityService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

class DeveloperElectricityVariationListView(generics.ListAPIView):
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

class DeveloperInternetServiceListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def list(self, request):
        services = InternetService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

class DeveloperInternetPlanListView(generics.ListAPIView):
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

class DeveloperEducationServiceListView(generics.ListAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def list(self, request):
        services = EducationService.objects.filter(is_active=True).order_by('id')
        data = [{"id": s.id, "service_id": s.service_id, "name": s.service_name} for s in services]
        return Response(data)

class DeveloperEducationVariationListView(generics.ListAPIView):
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
