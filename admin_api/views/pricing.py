from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from orders.models import (
    DataVariation, DataService, AirtimeNetwork, TVVariation, TVService, 
    InternetVariation, InternetService, EducationVariation, EducationService, 
    ElectricityVariation, ElectricityService
)
from admin_api.serializers import (
    AdminDataVariationSerializer, AdminDataServiceSerializer, AdminAirtimeNetworkSerializer,
    AdminTVVariationSerializer, AdminTVServiceSerializer, AdminInternetVariationSerializer, 
    AdminInternetServiceSerializer, AdminEducationVariationSerializer, AdminEducationServiceSerializer, 
    AdminElectricityVariationSerializer, AdminElectricityServiceSerializer
)
from admin_api.permissions import CanManageVTU

class AdminBasePricingViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageVTU]
    http_method_names = ['get', 'post', 'patch', 'delete']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminAirtimeNetworkViewSet(AdminBasePricingViewSet):
    queryset = AirtimeNetwork.objects.all()
    serializer_class = AdminAirtimeNetworkSerializer
    filterset_fields = ['provider', 'is_active']
    search_fields = ['service_name', 'service_id']

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminDataServiceViewSet(AdminBasePricingViewSet):
    queryset = DataService.objects.all()
    serializer_class = AdminDataServiceSerializer
    filterset_fields = ['provider', 'is_active']
    search_fields = ['service_name', 'service_id']

    @extend_schema(responses={200: AdminDataVariationSerializer(many=True)})
    @action(detail=True, methods=['get'])
    def plans(self, request, pk=None):
        network = self.get_object()
        plans = DataVariation.objects.filter(service=network)
        serializer = AdminDataVariationSerializer(plans, many=True)
        return Response(serializer.data)

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminDataVariationViewSet(AdminBasePricingViewSet):
    queryset = DataVariation.objects.all()
    serializer_class = AdminDataVariationSerializer
    filterset_fields = ['service', 'plan_type', 'is_active']
    search_fields = ['name', 'variation_id']

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminTVServiceViewSet(AdminBasePricingViewSet):
    queryset = TVService.objects.all()
    serializer_class = AdminTVServiceSerializer
    filterset_fields = ['provider', 'is_active']
    search_fields = ['service_name', 'service_id']

    @extend_schema(responses={200: AdminTVVariationSerializer(many=True)})
    @action(detail=True, methods=['get'])
    def plans(self, request, pk=None):
        network = self.get_object()
        plans = TVVariation.objects.filter(service=network)
        serializer = AdminTVVariationSerializer(plans, many=True)
        return Response(serializer.data)

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminTVVariationViewSet(AdminBasePricingViewSet):
    queryset = TVVariation.objects.all()
    serializer_class = AdminTVVariationSerializer
    filterset_fields = ['service', 'plan_type', 'is_active']
    search_fields = ['name', 'variation_id']

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminInternetServiceViewSet(AdminBasePricingViewSet):
    queryset = InternetService.objects.all()
    serializer_class = AdminInternetServiceSerializer
    filterset_fields = ['provider', 'is_active']
    search_fields = ['service_name', 'service_id']

    @extend_schema(responses={200: AdminInternetVariationSerializer(many=True)})
    @action(detail=True, methods=['get'])
    def plans(self, request, pk=None):
        network = self.get_object()
        plans = InternetVariation.objects.filter(service=network)
        serializer = AdminInternetVariationSerializer(plans, many=True)
        return Response(serializer.data)

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminInternetVariationViewSet(AdminBasePricingViewSet):
    queryset = InternetVariation.objects.all()
    serializer_class = AdminInternetVariationSerializer
    filterset_fields = ['service', 'plan_type', 'is_active']
    search_fields = ['name', 'variation_id']

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminEducationServiceViewSet(AdminBasePricingViewSet):
    queryset = EducationService.objects.all()
    serializer_class = AdminEducationServiceSerializer
    filterset_fields = ['provider', 'is_active']
    search_fields = ['service_name', 'service_id']

    @extend_schema(responses={200: AdminEducationVariationSerializer(many=True)})
    @action(detail=True, methods=['get'])
    def plans(self, request, pk=None):
        network = self.get_object()
        plans = EducationVariation.objects.filter(service=network)
        serializer = AdminEducationVariationSerializer(plans, many=True)
        return Response(serializer.data)

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminEducationVariationViewSet(AdminBasePricingViewSet):
    queryset = EducationVariation.objects.all()
    serializer_class = AdminEducationVariationSerializer
    filterset_fields = ['service', 'plan_type', 'is_active']
    search_fields = ['name', 'variation_id']

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminElectricityServiceViewSet(AdminBasePricingViewSet):
    queryset = ElectricityService.objects.all()
    serializer_class = AdminElectricityServiceSerializer
    filterset_fields = ['provider', 'is_active']
    search_fields = ['service_name', 'service_id']

    @extend_schema(responses={200: AdminElectricityVariationSerializer(many=True)})
    @action(detail=True, methods=['get'])
    def plans(self, request, pk=None):
        network = self.get_object()
        plans = ElectricityVariation.objects.filter(service=network)
        serializer = AdminElectricityVariationSerializer(plans, many=True)
        return Response(serializer.data)

@extend_schema(tags=["Admin Pricing & Plans"])
class AdminElectricityVariationViewSet(AdminBasePricingViewSet):
    queryset = ElectricityVariation.objects.all()
    serializer_class = AdminElectricityVariationSerializer
    filterset_fields = ['service', 'plan_type', 'is_active']
    search_fields = ['name', 'variation_id']
