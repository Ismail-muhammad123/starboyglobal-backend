import logging
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema
from orders.models import (
    DataVariation, AirtimeNetwork, ElectricityVariation, 
    TVVariation, InternetVariation, Purchase, EducationVariation
)
from orders.serializers import (
    DataPurchaseRequestSerializer, AirtimePurchaseRequestSerializer,
    ElectricityPurchaseRequestSerializer, TVPurchaseRequestSerializer,
    InternetPurchaseRequestSerializer, EducationPurchaseRequestSerializer,
    PurchaseSerializer, RepeatPurchaseRequestSerializer, ErrorResponseSerializer
)
from orders.utils.purchase_logic import (
    purchase_airtime, purchase_data, purchase_tv, purchase_electricity,
    purchase_internet, purchase_education, _json_safe
)
from .utility_views import generate_request_id
from notifications.utils import NotificationService

logger = logging.getLogger(__name__)


class PurchaseDataVariationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Data"],
        summary="Purchase a data bundle",
        description="Buy a data plan for a specified phone number. Requires a valid transaction PIN.",
        request=DataPurchaseRequestSerializer,
        responses={201: PurchaseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = DataPurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        pin = serializer.validated_data.get("transaction_pin")
        if not user.check_transaction_pin(pin):
            logger.warning("Data purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        # check phone number length and format here if needed before proceeding
        if len(serializer.validated_data["phone_number"]) != 11 or not serializer.validated_data["phone_number"].isdigit() or not serializer.validated_data["phone_number"].startswith("0"):
            return Response({"error": "Invalid phone number format."}, status=status.HTTP_400_BAD_REQUEST)
        
        plan_id = serializer.validated_data["plan_id"]
        phone_number = serializer.validated_data["phone_number"]
        promo_code = serializer.validated_data.get("promo_code")

        try:
            # plan_id may be a DB integer PK (db mode) or a provider variation_id string (live mode)
            plan = None
            if str(plan_id).isdigit():
                plan = DataVariation.objects.filter(id=int(plan_id), is_active=True).first()
            if plan is None:
                plan = DataVariation.objects.filter(variation_id=plan_id, is_active=True).first()
            if plan is None:
                raise DataVariation.DoesNotExist
            amount = plan.agent_price if user.role == 'agent' else plan.selling_price
            reference = generate_request_id()
            result = purchase_data(
                user=user,
                plan=plan,
                phone=phone_number,
                reference=reference,
                promo_code_str=promo_code
            )

            if result['status'] == "failed":
                fail_amt = result.get('amount', amount)
                logger.error(
                    "Data purchase FAILED | user=%s plan_id=%s phone=%s ref=%s error=%s",
                    user.id, plan_id, phone_number, reference, result.get("error")
                )
                NotificationService.send_push(user, "Data Purchase Failed", f"Your purchase of {plan.name} was unsuccessful. N{fail_amt} has been refunded.")
                return Response({"error": result.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)

            NotificationService.send_push(user, "Data Purchase Successful", f"Your purchase of {plan.name} to {phone_number} was successful.")
            return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=result['purchase_id'])).data), status=status.HTTP_201_CREATED)
        except DataVariation.DoesNotExist:
            logger.warning("Data purchase: plan_id=%s not found or inactive for user=%s", plan_id, user.id)
            return Response({"error": "Invalid or inactive plan."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Data purchase: unexpected error for user=%s plan_id=%s phone=%s — %s", user.id, plan_id, phone_number, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseAirtimeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Airtime"],
        summary="Purchase airtime",
        description="Buy airtime for a specified phone number. Pass the DB `id` of the AirtimeNetwork record as `service_id`.",
        request=AirtimePurchaseRequestSerializer,
        responses={201: PurchaseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = AirtimePurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        pin = serializer.validated_data.get("transaction_pin")
        if not user.check_transaction_pin(pin):
            logger.warning("Airtime purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        
        # check phone number length and format here if needed before proceeding
        if len(serializer.validated_data["phone_number"]) != 11 or not serializer.validated_data["phone_number"].isdigit() or not serializer.validated_data["phone_number"].startswith("0"):
            return Response({"error": "Invalid phone number format."}, status=status.HTTP_400_BAD_REQUEST)
        

        amount = serializer.validated_data["amount"]
        phone_number = serializer.validated_data["phone_number"]
        service_id = serializer.validated_data["service_id"]   # DB PK of AirtimeNetwork
        promo_code = serializer.validated_data.get("promo_code")

        try:
            # Look up by unique DB PK — no ambiguity across providers.
            network = AirtimeNetwork.objects.get(id=service_id, is_active=True)

            reference = generate_request_id()
            result = purchase_airtime(
                user=user,
                network=network,
                phone=phone_number,
                amount=amount,
                reference=reference,
                promo_code_str=promo_code
            )

            if result['status'] == "failed":
                fail_amt = result.get('amount', amount)
                logger.error(
                    "Airtime purchase FAILED | user=%s network=%s (%s) phone=%s amount=%s ref=%s error=%s",
                    user.id, service_id, network.service_name, phone_number, amount, reference, result.get("error")
                )
                NotificationService.send_push(user, "Airtime Purchase Failed", f"Your purchase of N{amount} airtime was unsuccessful. N{fail_amt} has been refunded.")
                return Response({"error": result.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)

            NotificationService.send_push(user, "Airtime Purchase Successful", f"Your purchase of N{amount} {network.service_name} airtime to {phone_number} was successful.")
            return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=result['purchase_id'])).data), status=status.HTTP_201_CREATED)
        except AirtimeNetwork.DoesNotExist:
            logger.warning("Airtime purchase: network id=%s not found or inactive for user=%s", service_id, user.id)
            return Response({"error": "Airtime network not found or is inactive."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Airtime purchase: unexpected error for user=%s network_id=%s phone=%s — %s", user.id, service_id, phone_number, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseElectricityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Electricity"],
        summary="Purchase electricity token",
        description="Pay for electricity for a specified meter number. Returns a token on success.",
        request=ElectricityPurchaseRequestSerializer,
        responses={201: PurchaseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = ElectricityPurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        pin = serializer.validated_data.get("transaction_pin")
        if not user.check_transaction_pin(pin):
            logger.warning("Electricity purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        amount = serializer.validated_data["amount"]
        service_id = serializer.validated_data["service_id"]
        variation_id = serializer.validated_data["variation_id"]
        customer_id = serializer.validated_data["customer_id"]
        promo_code = serializer.validated_data.get("promo_code")

        try:
            electricity_variation = ElectricityVariation.objects.get(variation_id=variation_id)
            discount_val = electricity_variation.agent_discount if user.role == 'agent' else electricity_variation.discount
            actual_amount = Decimal(amount) - (Decimal(amount) * Decimal(discount_val) / 100)

            reference = generate_request_id()
            result = purchase_electricity(
                user=user,
                electricity_variation=electricity_variation,
                meter_number=customer_id,
                amount=amount,
                reference=reference,
                promo_code_str=promo_code
            )

            if result['status'] == "failed":
                fail_amt = result.get('amount', amount)
                logger.error(
                    "Electricity purchase FAILED | user=%s service=%s variation=%s meter=%s amount=%s ref=%s error=%s",
                    user.id, service_id, variation_id, customer_id, amount, reference, result.get("error")
                )
                NotificationService.send_push(user, "Electricity Purchase Failed", f"Your electricity purchase of N{amount} was unsuccessful. N{fail_amt} has been refunded.")
                return Response({"error": result.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)

            NotificationService.send_push(user, "Electricity Purchase Successful", f"Your electricity purchase for meter {customer_id} was successful.")
            return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=result['purchase_id'])).data), status=status.HTTP_201_CREATED)
        except ElectricityVariation.DoesNotExist:
            logger.warning("Electricity purchase: variation_id=%s not found for user=%s", variation_id, user.id)
            return Response({"error": "Invalid Variation."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Electricity purchase: unexpected error for user=%s meter=%s — %s", user.id, customer_id, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseTVSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Cable TV"],
        summary="Purchase TV subscription",
        description="Subscribe to a Cable TV bouquet (DSTV, GOTV, Startimes) for a specified smartcard number.",
        request=TVPurchaseRequestSerializer,
        responses={201: PurchaseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = TVPurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        pin = serializer.validated_data.get("transaction_pin")
        if not user.check_transaction_pin(pin):
            logger.warning("TV purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        amount = serializer.validated_data["amount"]
        service_id = serializer.validated_data["service_id"]
        variation_id = serializer.validated_data["variation_id"]
        customer_id = serializer.validated_data["customer_id"]
        promo_code = serializer.validated_data.get("promo_code")

        try:
            tv_variation = TVVariation.objects.get(variation_id=variation_id)
            amount = tv_variation.agent_price if user.role == 'agent' else tv_variation.selling_price

            reference = generate_request_id()
            result = purchase_tv(
                user=user,
                tv_variation=tv_variation,
                customer_id=customer_id,
                reference=reference,
                promo_code_str=promo_code
            )

            if result['status'] == "failed":
                fail_amt = result.get('amount', amount)
                logger.error(
                    "TV purchase FAILED | user=%s service=%s variation=%s smartcard=%s amount=%s ref=%s error=%s",
                    user.id, service_id, variation_id, customer_id, amount, reference, result.get("error")
                )
                NotificationService.send_push(user, "TV Subscription Failed", f"Your TV subscription of N{amount} failed. N{fail_amt} has been refunded.")
                return Response({"error": result.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)

            NotificationService.send_push(user, "TV Subscription Successful", f"Your TV subscription for {customer_id} was successful.")
            return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=result['purchase_id'])).data), status=status.HTTP_201_CREATED)
        except TVVariation.DoesNotExist:
            logger.warning("TV purchase: variation_id=%s not found for user=%s", variation_id, user.id)
            return Response({"error": "Invalid TV Service."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("TV purchase: unexpected error for user=%s smartcard=%s — %s", user.id, customer_id, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseInternetSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Internet"],
        summary="Purchase Internet data subscription",
        description="Buy a Internet data package for a specified phone number.",
        request=InternetPurchaseRequestSerializer,
        responses={201: PurchaseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = InternetPurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        pin = serializer.validated_data.get("transaction_pin")
        if not user.check_transaction_pin(pin):
            logger.warning("Internet purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        plan_id = serializer.validated_data["plan_id"]
        phone_number = serializer.validated_data["phone_number"]
        promo_code = serializer.validated_data.get("promo_code")

        try:
            # plan_id may be a DB integer PK (db mode) or a provider variation_id string (live mode)
            plan = None
            if str(plan_id).isdigit():
                plan = InternetVariation.objects.filter(id=int(plan_id), is_active=True).first()
            if plan is None:
                plan = InternetVariation.objects.filter(variation_id=plan_id, is_active=True).first()
            if plan is None:
                raise InternetVariation.DoesNotExist
            amount = plan.agent_price if user.role == 'agent' else plan.selling_price

            reference = generate_request_id()
            result = purchase_internet(
                user=user,
                internet_variation=plan,
                phone=phone_number,
                reference=reference,
                promo_code_str=promo_code
            )

            if result['status'] == "failed":
                fail_amt = result.get('amount', amount)
                logger.error(
                    "Internet purchase FAILED | user=%s plan_id=%s phone=%s ref=%s error=%s",
                    user.id, plan_id, phone_number, reference, result.get("error")
                )
                NotificationService.send_push(user, "Internet Subscription Failed", f"Your Internet subscription failed. N{fail_amt} has been refunded.")
                return Response({"error": result.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)

            NotificationService.send_push(user, "Internet Subscription Successful", f"Your Internet subscription for {phone_number} was successful.")
            return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=result['purchase_id'])).data), status=status.HTTP_201_CREATED)
        except InternetVariation.DoesNotExist:
            logger.warning("Internet purchase: plan_id=%s not found or inactive for user=%s", plan_id, user.id)
            return Response({"error": "Invalid Internet Package."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Internet purchase: unexpected error for user=%s plan_id=%s phone=%s — %s", user.id, plan_id, phone_number, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PurchaseEducationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Education"],
        summary="Purchase education PIN",
        description="Buy an exam PIN (WAEC, NECO, NABTEB, JAMB) for a specified exam type.",
        request=EducationPurchaseRequestSerializer,
        responses={200: PurchaseSerializer, 400: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = EducationPurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        amount = serializer.validated_data['amount']
        service_id = serializer.validated_data['service_id']
        variation_id = serializer.validated_data['variation_id']
        promo_code = serializer.validated_data.get('promo_code')
        pin = serializer.validated_data.get('transaction_pin')

        if not user.check_transaction_pin(pin):
            logger.warning("Education purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        try:
            plan = EducationVariation.objects.get(variation_id=variation_id, service__service_id=service_id, is_active=True)
            amount = plan.agent_price if user.role == 'agent' else plan.selling_price
            phone_number = serializer.validated_data.get('phone_number')

            res = purchase_education(
                user=user,
                education_variation=plan,
                phone=phone_number,
                quantity=1,
                reference=generate_request_id(),
                promo_code_str=promo_code
            )

            if res.get('status') == 'success':
                NotificationService.send_push(user, "Education PIN Successful", f"Your {plan.name} purchase was successful.")
                return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=res['purchase_id'])).data), status=status.HTTP_200_OK)
            else:
                fail_amt = res.get('amount', amount)
                logger.error(
                    "Education purchase FAILED | user=%s service=%s variation=%s error=%s",
                    user.id, service_id, variation_id, res.get("error")
                )
                NotificationService.send_push(user, "Education PIN Failed", f"Your education PIN purchase was unsuccessful. N{fail_amt} has been refunded.")
                return Response({"error": res.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)
        except EducationVariation.DoesNotExist:
            logger.warning("Education purchase: variation_id=%s service=%s not found or inactive for user=%s", variation_id, service_id, user.id)
            return Response({"error": "Invalid or inactive plan."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Education purchase: unexpected error for user=%s service=%s variation=%s — %s", user.id, service_id, variation_id, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RepeatPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Orders - Repeat"],
        summary="Repeat a previous purchase",
        description="Re-trigger a previous transaction by passing the original purchase ID. Requires a valid transaction PIN. The same beneficiary and plan are used.",
        request=RepeatPurchaseRequestSerializer,
        responses={201: PurchaseSerializer, 400: ErrorResponseSerializer, 404: ErrorResponseSerializer, 403: ErrorResponseSerializer}
    )
    def post(self, request):
        serializer = RepeatPurchaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        pin = serializer.validated_data.get("transaction_pin")
        if not user.check_transaction_pin(pin):
            logger.warning("Repeat purchase: invalid PIN attempt by user=%s", user.id)
            return Response({"error": "Invalid transaction PIN."}, status=status.HTTP_403_FORBIDDEN)

        purchase_id = serializer.validated_data["purchase_id"]

        try:
            old_purchase = Purchase.objects.get(id=purchase_id, user=user)
            if old_purchase.purchase_type == 'data' and old_purchase.data_variation:
                 if not old_purchase.data_variation.is_active or not old_purchase.data_variation.service.is_active:
                     logger.warning("Repeat purchase: data plan no longer available | user=%s purchase_id=%s", user.id, purchase_id)
                     return Response({"error": "This data plan is no longer available."}, status=status.HTTP_400_BAD_REQUEST)

            reference = generate_request_id()
            if old_purchase.purchase_type == 'airtime':
                result = purchase_airtime(user, old_purchase.airtime_service, old_purchase.beneficiary, old_purchase.amount, reference)
            elif old_purchase.purchase_type == 'data':
                result = purchase_data(user, old_purchase.data_variation, old_purchase.beneficiary, reference)
            elif old_purchase.purchase_type == 'electricity':
                result = purchase_electricity(user, old_purchase.electricity_variation, old_purchase.beneficiary, old_purchase.amount, reference)
            elif old_purchase.purchase_type == 'tv':
                result = purchase_tv(user, old_purchase.tv_variation, old_purchase.beneficiary, reference)
            elif old_purchase.purchase_type == 'internet':
                result = purchase_internet(user, old_purchase.internet_variation, old_purchase.beneficiary, reference)
            elif old_purchase.purchase_type == 'education':
                result = purchase_education(user, old_purchase.education_variation, old_purchase.beneficiary, 1, reference)
            else:
                logger.error("Repeat purchase: unknown purchase_type=%s for purchase_id=%s user=%s", old_purchase.purchase_type, purchase_id, user.id)
                return Response({"error": "Unknown purchase type for repeat."}, status=status.HTTP_400_BAD_REQUEST)

            if result['status'] == "failed":
                logger.error(
                    "Repeat purchase FAILED | user=%s purchase_id=%s type=%s ref=%s error=%s",
                    user.id, purchase_id, old_purchase.purchase_type, reference, result.get("error")
                )
                return Response({"error": result.get("error", "Transaction failed")}, status=status.HTTP_400_BAD_REQUEST)

            return Response(_json_safe(PurchaseSerializer(Purchase.objects.get(id=result['purchase_id'])).data), status=status.HTTP_201_CREATED)
        except Purchase.DoesNotExist:
            logger.warning("Repeat purchase: purchase_id=%s not found for user=%s", purchase_id, user.id)
            return Response({"error": "Original purchase not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Repeat purchase: unexpected error for user=%s purchase_id=%s — %s", user.id, purchase_id, e)
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
