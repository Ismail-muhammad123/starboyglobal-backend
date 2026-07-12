from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema
from orders.models import PurchaseBeneficiary
from orders.serializers import PurchaseBeneficiarySerializer


@extend_schema(tags=["Orders - Beneficiaries"])
class PurchaseBeneficiaryListCreateView(generics.ListCreateAPIView):
    """List and create saved purchase beneficiaries (e.g. saved meter numbers, smartcard IDs)."""
    serializer_class = PurchaseBeneficiarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PurchaseBeneficiary.objects.filter(user=self.request.user).order_by('-id')
        service_type = self.request.query_params.get('type')
        if service_type:
            qs = qs.filter(service_type=service_type)
        return qs

    def perform_create(self, serializer):
        # Prevent IntegrityError by using update_or_create logic or checking existence
        user = self.request.user
        service_type = serializer.validated_data.get('service_type')
        identifier = serializer.validated_data.get('identifier')
        nickname = serializer.validated_data.get('nickname', '')

        # Use get_or_create to ignore duplicates
        obj, created = PurchaseBeneficiary.objects.get_or_create(
            user=user,
            service_type=service_type,
            identifier=identifier,
            defaults={'nickname': nickname}
        )
        if not created and nickname:
            obj.nickname = nickname
            obj.save()



@extend_schema(tags=["Orders - Beneficiaries"])
class PurchaseBeneficiaryDeleteView(generics.DestroyAPIView):
    """Delete a saved purchase beneficiary."""
    serializer_class = PurchaseBeneficiarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PurchaseBeneficiary.objects.filter(user=self.request.user).order_by('-id')
