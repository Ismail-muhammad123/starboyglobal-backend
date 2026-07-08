from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from orders.models import (
    Purchase, AirtimeNetwork, DataVariation, 
    ElectricityService, TVVariation, InternetVariation, 
    EducationVariation, ElectricityVariation
)
from orders.utils.purchase_logic import process_vtu_purchase
from ..authentication import APIKeyAuthentication
from ..permissions import IsDeveloperUser
import uuid

class DeveloperPurchaseView(generics.CreateAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def post(self, request, *args, **kwargs):
        user = request.user
        mode = request.mode
        data = request.data
        
        purchase_type = data.get('service_type')
        beneficiary = data.get('beneficiary')
        amount = data.get('amount')
        
        if not all([purchase_type, beneficiary, amount]):
            return Response({"error": "Missing required fields: service_type, beneficiary, amount"}, status=400)

        # Sandbox Mode: Simulate success without hitting real providers or debiting real wallet
        if mode == 'sandbox':
            ref = f"SBX-{uuid.uuid4().hex[:10].upper()}"
            return Response({
                "status": "success",
                "message": "Sandbox transaction successful (Simulated)",
                "reference": ref,
                "amount": float(amount),
                "beneficiary": beneficiary,
                "mode": "sandbox"
            }, status=201)

        # Live Mode: Process regular purchase
        ref = data.get('reference', f"DEV-{uuid.uuid4().hex[:10].upper()}")
        
        # Prepare specific kwargs based on type
        vtu_kwargs = {'reference': ref, 'initiator': 'api', 'initiated_by': user}
        
        try:
            from orders.serializers.variations import resolve_price
            
            if purchase_type == 'airtime':
                network_id = data.get('network_id')
                network = get_object_or_404(AirtimeNetwork, id=network_id)
                # Apply developer-specific price (as discount percentage) or fall back to standard discount
                discount_val = network.developer_price if (hasattr(network, 'developer_price') and network.developer_price > 0) else network.discount
                face_value = float(amount)
                actual_amount = face_value - (face_value * float(discount_val) / 100)
                amount = actual_amount
                vtu_kwargs.update({
                    'airtime_service': network,
                    'network': network.service_id,
                    'provider_amount': face_value,
                    'action': 'buy_airtime',
                    'service_name': f"{network.service_name} Airtime"
                })
            
            elif purchase_type == 'data':
                plan_id = data.get('plan_id')
                plan = get_object_or_404(DataVariation, id=plan_id)
                amount = resolve_price(plan, 'developer', 'data')
                vtu_kwargs.update({
                    'data_variation': plan,
                    'network': plan.service.service_id,
                    'plan_id': plan.variation_id,
                    'provider_amount': amount,
                    'action': 'buy_data',
                    'service_name': f"{plan.name} Data"
                })
            
            elif purchase_type == 'tv':
                variation_id = data.get('variation_id')
                variation = get_object_or_404(TVVariation, id=variation_id)
                amount = resolve_price(variation, 'developer', 'tv')
                vtu_kwargs.update({
                    'tv_variation': variation,
                    'tv_id': variation.service.service_id,
                    'package_id': variation.variation_id,
                    'smart_card_number': beneficiary,
                    'provider_amount': amount,
                    'action': 'buy_tv',
                    'service_name': f"{variation.name} TV"
                })
            
            elif purchase_type == 'electricity':
                variation_id = data.get('variation_id')
                variation = get_object_or_404(ElectricityVariation, id=variation_id)
                discount_val = variation.developer_price if (hasattr(variation, 'developer_price') and variation.developer_price > 0) else variation.discount
                face_value = float(amount)
                actual_amount = face_value - (face_value * float(discount_val) / 100)
                amount = actual_amount
                vtu_kwargs.update({
                    'electricity_variation': variation,
                    'disco_id': variation.service.service_id,
                    'plan_id': variation.variation_id,
                    'meter_number': beneficiary,
                    'provider_amount': face_value,
                    'action': 'buy_electricity',
                    'service_name': f"{variation.name} Electricity"
                })

            elif purchase_type == 'internet':
                variation_id = data.get('variation_id')
                variation = get_object_or_404(InternetVariation, id=variation_id)
                amount = resolve_price(variation, 'developer', 'internet')
                vtu_kwargs.update({
                    'internet_variation': variation,
                    'plan_id': variation.variation_id,
                    'provider_amount': amount,
                    'action': 'buy_internet',
                    'service_name': f"{variation.name} Internet"
                })

            elif purchase_type == 'education':
                variation_id = data.get('variation_id')
                variation = get_object_or_404(EducationVariation, id=variation_id)
                quantity = int(data.get('quantity', 1))
                amount = resolve_price(variation, 'developer', 'education') * quantity
                vtu_kwargs.update({
                    'education_variation': variation,
                    'exam_type': variation.service.service_id,
                    'variation_id': variation.variation_id,
                    'quantity': quantity,
                    'provider_amount': amount,
                    'action': 'buy_education',
                    'service_name': f"{variation.name} Education"
                })

            else:
                return Response({"error": f"Unsupported service type: {purchase_type}"}, status=400)
            
            # Execute purchase
            result = process_vtu_purchase(user, purchase_type, amount, beneficiary, **vtu_kwargs)
            
            return Response({
                "status": result['status'],
                "reference": ref,
                "purchase_id": result.get('purchase_id'),
                "message": "Transaction initiated" if result['status'] == 'pending' else "Transaction successful" if result['status'] == 'success' else "Transaction failed",
                "error": result.get('error') if result['status'] == 'failed' else None
            }, status=status.HTTP_201_CREATED if result['status'] != 'failed' else status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

class DeveloperVerifyPurchaseView(generics.RetrieveAPIView):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsDeveloperUser]

    def get(self, request, reference):
        purchase = get_object_or_404(Purchase, reference=reference, user=request.user)
        return Response({
            "reference": purchase.reference,
            "status": purchase.status,
            "amount": float(purchase.amount),
            "beneficiary": purchase.beneficiary,
            "type": purchase.purchase_type,
            "created_at": purchase.time,
            "remarks": purchase.remarks
        })
