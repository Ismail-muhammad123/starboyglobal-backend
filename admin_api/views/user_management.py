from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from django.db.models import Q, Sum, Count
from drf_spectacular.utils import extend_schema_view, extend_schema, inline_serializer
from users.models import User, KYC, StaffPermission
from admin_api.serializers import (
    AdminUserListSerializer, AdminUserDetailSerializer,
    AdminCreateUserRequestSerializer, AdminSetRoleRequestSerializer,
    AdminSetPermissionsRequestSerializer, AdminResetPinRequestSerializer,
    AdminKYCActionRequestSerializer, AdminAgentUpgradeRequestSerializer,
    AdminStatusResponseSerializer, AdminErrorResponseSerializer,
    StaffPermissionSerializer, KYCSerializer, AdminKYCActionRequestSerializer
)
from admin_api.permissions import CanManageUsers
from admin_api.utils import log_admin_action
from wallet.models import Wallet, VirtualAccount
from summary.models import SiteConfig
import pyotp
import random
from notifications.utils import NotificationService


class UserPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(tags=["Admin User Management"], summary="List all users with pagination, filters, and search"),
    retrieve=extend_schema(tags=["Admin User Management"], summary="Get full user details including wallet, transactions, beneficiaries"),
    partial_update=extend_schema(tags=["Admin User Management"], summary="Update user profile fields"),
    update=extend_schema(tags=["Admin User Management"], summary="Update user profile fields"),
)
class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related('wallet', 'kyc', 'staff_permissions').all().order_by('-created_at')
    permission_classes = [CanManageUsers]
    pagination_class = UserPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['phone_number', 'first_name', 'last_name', 'email', 'referral_code']
    ordering_fields = ['created_at', 'first_name', 'last_name', 'role']
    filterset_fields = ['role', 'is_active', 'is_kyc_verified', 'is_staff', 'is_closed']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdminUserDetailSerializer
        if self.action == 'create':
            return AdminCreateUserRequestSerializer
        return AdminUserListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Extra query param filters
        role = self.request.query_params.get('role')
        is_active = self.request.query_params.get('is_active')
        is_kyc_verified = self.request.query_params.get('is_kyc_verified')
        is_closed = self.request.query_params.get('is_closed')

        if role:
            qs = qs.filter(role=role)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        if is_kyc_verified is not None:
            qs = qs.filter(is_kyc_verified=is_kyc_verified.lower() == 'true')
        if is_closed is not None:
            qs = qs.filter(is_closed=is_closed.lower() == 'true')
        return qs

    # ─── Create User ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Add a new user",
        request=AdminCreateUserRequestSerializer,
        responses={201: AdminUserDetailSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = AdminCreateUserRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if User.objects.filter(phone_number=d['phone_number']).exists():
            return Response({"error": "User with this phone number already exists."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            phone_number=d['phone_number'],
            password=d['password'],
            first_name=d.get('first_name', ''),
            last_name=d.get('last_name', ''),
            email=d.get('email'),
            role=d.get('role', 'customer'),
            is_active=d.get('is_active', True),
        )

        config = SiteConfig.objects.first()
        # Always create wallet if enabled in config
        if not config or config.auto_create_wallet:
            Wallet.objects.get_or_create(user=user)

        # Auto create VA if profile is somehow complete or if configured to always try
        if config and config.auto_create_virtual_account:
            # Check if user has minimum required info for VA (usually Email, name, phone)
            if user.email and user.first_name and user.last_name:
                # Logic to trigger VA creation (usually a service call or background task)
                # For now, we assume a signal or subsequent step handles the real API call
                pass

        # Apply is_staff / is_admin flags if supplied
        if d.get('is_staff', False):
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            StaffPermission.objects.get_or_create(user=user)
        if d.get('is_admin', False):
            user.is_admin = True
            user.save(update_fields=['is_admin'])

        log_admin_action(
            user=request.user,
            action_type="CREATE_USER",
            description=f"Created new user {user.phone_number} with role {user.role}",
            target=user
        )

        return Response(AdminUserDetailSerializer(user).data, status=status.HTTP_201_CREATED)

    # ─── Activate / Deactivate ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Activate a user account",
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        log_admin_action(
            user=request.user,
            action_type="ACTIVATE_USER",
            description=f"Activated user {user.phone_number}",
            target=user
        )
        return Response({"status": "SUCCESS", "message": f"User {user.phone_number} activated."})

    @extend_schema(
        tags=["Admin User Management"],
        summary="Deactivate a user account",
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        log_admin_action(
            user=request.user,
            action_type="DEACTIVATE_USER",
            description=f"Deactivated user {user.phone_number}",
            target=user
        )
        return Response({"status": "SUCCESS", "message": f"User {user.phone_number} deactivated."})

    # ─── Block / Unblock ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Block a user (close account)",
        request={"application/json": {"type": "object", "properties": {"reason": {"type": "string"}}}},
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='block')
    def block(self, request, pk=None):
        user = self.get_object()
        user.is_closed = True
        user.is_active = False
        user.closed_at = timezone.now()
        user.closed_reason = request.data.get('reason', 'Blocked by Admin')
        user.save(update_fields=['is_closed', 'is_active', 'closed_at', 'closed_reason'])
        log_admin_action(
            user=request.user,
            action_type="BLOCK_USER",
            description=f"Blocked user {user.phone_number}. Reason: {user.closed_reason}",
            target=user
        )
        NotificationService.send_from_template(user, "account-blocked", {"reason": user.closed_reason})
        return Response({"status": "SUCCESS", "message": f"User {user.phone_number} blocked."})

    @extend_schema(
        tags=["Admin User Management"],
        summary="Unblock a user (reopen account)",
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='unblock')
    def unblock(self, request, pk=None):
        user = self.get_object()
        user.is_closed = False
        user.is_active = True
        user.closed_at = None
        user.closed_reason = None
        user.save(update_fields=['is_closed', 'is_active', 'closed_at', 'closed_reason'])
        log_admin_action(
            user=request.user,
            action_type="UNBLOCK_USER",
            description=f"Unblocked user {user.phone_number}.",
            target=user
        )
        NotificationService.send_from_template(user, "account-unblocked", {})
        return Response({"status": "SUCCESS", "message": f"User {user.phone_number} unblocked."})

    # ─── KYC ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Approve user KYC",
        request=AdminKYCActionRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='approve-kyc')
    def approve_kyc(self, request, pk=None):
        user = self.get_object()
        kyc, _ = KYC.objects.get_or_create(user=user)
        user.is_kyc_verified = True
        user.save(update_fields=['is_kyc_verified'])

        kyc.status = 'APPROVED'
        kyc.time_accepted = timezone.now()
        kyc.remarks = request.data.get('reason', 'Approved by Admin')
        kyc.processed_by = request.user
        kyc.save()
        log_admin_action(
            user=request.user,
            action_type="APPROVE_KYC",
            description=f"Approved KYC for user {user.phone_number}",
            target=kyc
        )
        NotificationService.send_from_template(user, "kyc-approved", {})
        return Response({"status": "SUCCESS", "message": "User KYC approved."})

    @extend_schema(
        tags=["Admin User Management"],
        summary="Reject user KYC with reason",
        request=AdminKYCActionRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='reject-kyc')
    def reject_kyc(self, request, pk=None):
        user = self.get_object()
        kyc, _ = KYC.objects.get_or_create(user=user)
        user.is_kyc_verified = False
        user.save(update_fields=['is_kyc_verified'])

        kyc.status = 'REJECTED'
        kyc.time_rejected = timezone.now()
        kyc.remarks = request.data.get('reason', 'Rejected by Admin')
        kyc.processed_by = request.user
        kyc.save()
        log_admin_action(
            user=request.user,
            action_type="REJECT_KYC",
            description=f"Rejected KYC for user {user.phone_number}. Reason: {kyc.remarks}",
            target=kyc
        )
        NotificationService.send_from_template(user, "kyc-rejected", {"reason": kyc.remarks})
        return Response({"status": "REJECTED", "message": "User KYC rejected."})

    # ─── Reset Transaction PIN ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Reset or change a user's transaction PIN",
        request=AdminResetPinRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='reset-pin')
    def reset_pin(self, request, pk=None):
        user = self.get_object()
        serializer = AdminResetPinRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_pin = serializer.validated_data['new_pin']
        user.set_transaction_pin(new_pin)
        NotificationService.send_from_template(user, "transaction-pin-reset", {})
        return Response({"status": "SUCCESS", "message": f"Transaction PIN reset for user {user.phone_number}."})

    # ─── Set Role (Upgrade to Agent / Staff / Downgrade to Customer) ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Set user role (customer / agent / developer) and optionally grant is_staff / is_admin flags",
        request=AdminSetRoleRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='set-role')
    def set_role(self, request, pk=None):
        user = self.get_object()
        serializer = AdminSetRoleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_role = serializer.validated_data['role']
        commission_rate = serializer.validated_data.get('commission_rate', 0.0)

        user.role = new_role
        user.upgraded_at = timezone.now()
        user.upgraded_by = request.user

        if new_role == 'agent':
            user.agent_commission_rate = commission_rate

        # Handle explicit is_staff / is_admin flag overrides (independent of role)
        is_staff_override = serializer.validated_data.get('is_staff')
        is_admin_override = serializer.validated_data.get('is_admin')
        if is_staff_override is not None:
            user.is_staff = is_staff_override
            if is_staff_override:
                StaffPermission.objects.get_or_create(user=user)
        if is_admin_override is not None:
            user.is_admin = is_admin_override

        user.save()
        log_admin_action(
            user=request.user,
            action_type="SET_USER_ROLE",
            description=f"Set role of {user.phone_number} to {new_role}",
            target=user,
            metadata={"commission_rate": str(commission_rate)} if new_role == 'agent' else None
        )
        return Response({"status": "SUCCESS", "message": f"User {user.phone_number} role set to '{new_role}'."})

    # ─── Update Permissions (for staff users) ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Update staff user permissions",
        request=AdminSetPermissionsRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='set-permissions')
    def set_permissions(self, request, pk=None):
        user = self.get_object()
        if not user.is_staff and not user.is_admin and not user.is_superuser:
            return Response({"error": "User does not have staff or admin status. Set is_staff or is_admin first."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AdminSetPermissionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        perms, _ = StaffPermission.objects.get_or_create(user=user)
        for field, value in serializer.validated_data.items():
            setattr(perms, field, value)
        perms.save()
        log_admin_action(
            user=request.user,
            action_type="UPDATE_STAFF_PERMISSIONS",
            description=f"Updated permissions for staff user {user.phone_number}",
            target=user
        )

        return Response({"status": "SUCCESS", "message": f"Permissions updated for {user.phone_number}."})

    # ─── Agent Performance ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="View agent performance and commission stats",
        responses={200: {"type": "object"}}
    )
    @action(detail=True, methods=['get'], url_path='agent-performance')
    def agent_performance(self, request, pk=None):
        user = self.get_object()
        from orders.models import Purchase

        today = timezone.now().date()
        purchases = Purchase.objects.filter(user=user, status='success')

        total_sales = purchases.aggregate(total=Sum('amount'))['total'] or 0
        total_count = purchases.count()
        today_sales = purchases.filter(time__date=today).aggregate(total=Sum('amount'))['total'] or 0
        today_count = purchases.filter(time__date=today).count()

        # Per-service breakdown
        by_service = purchases.values('purchase_type').annotate(
            count=Count('id'), total=Sum('amount')
        )

        return Response({
            "user_id": user.id,
            "phone": user.phone_number,
            "role": user.role,
            "commission_rate": float(user.agent_commission_rate),
            "referral_earnings_count": user.referral_earnings_count,
            "referral_earnings_amount": float(user.referral_earnings_amount),
            "total_sales": float(total_sales),
            "total_transactions": total_count,
            "today_sales": float(today_sales),
            "today_transactions": today_count,
            "by_service": list(by_service),
        })

    # ─── Backward-compatible: upgrade-to-agent ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Upgrade user to agent (legacy)",
        request=AdminAgentUpgradeRequestSerializer,
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='upgrade-to-agent')
    def upgrade_to_agent(self, request, pk=None):
        user = self.get_object()
        user.role = 'agent'
        user.agent_commission_rate = request.data.get('commission_rate', 0.0)
        user.upgraded_at = timezone.now()
        user.upgraded_by = request.user
        user.save()
        return Response({"status": "SUCCESS", "message": f"User {user.phone_number} upgraded to Agent."})

    # ─── Virtual Account ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Create a virtual account for a user",
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='create-virtual-account')
    def create_virtual_account(self, request, pk=None):
        user = self.get_object()
        
        # Check if already exists
        if hasattr(user, 'virtual_account') and user.virtual_account:
             return Response({"status": "ERROR", "message": "User already has a virtual account"}, status=400)

        # Base requirement for Paystack KYC
        if not user.first_name or not user.last_name or not user.email:
            return Response({"status": "ERROR", "message": "User profile information is incomplete. First name, last name, and email are required for virtual account provisioning."}, status=400)

        try:
            from payments.utils import PaystackGateway
            from wallet.models import VirtualAccount
            from django.conf import settings
            client = PaystackGateway(settings.PAYSTACK_SECRET_KEY)

            # Initiate call to Paystack
            # Note: Paystack needs a cleaned phone number
            phone = user.phone_country_code + user.phone_number
            if phone.startswith('+'):
                phone = phone[1:]
            
            account_res = client.create_virtual_account(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=phone
            )

            if account_res and account_res.get('status'):
                # Extract data from Paystack response
                data = account_res['data']
                bank = data.get('bank', {})
                
                # Save to database
                va = VirtualAccount.objects.create(
                    user=user,
                    account_number=data['account_number'],
                    bank_name=bank.get('name', 'Wema Bank'),
                    account_name=data['account_name'],
                    account_reference=data.get('assignment', {}).get('integration', 'PAYSTACK'),
                    customer_email=user.email,
                    customer_name=f"{user.first_name} {user.last_name}",
                    status='ACTIVE'
                )

                return Response({
                    "status": "SUCCESS", 
                    "message": "Virtual account provisioned successfully",
                    "data": {
                        "account_number": va.account_number,
                        "bank_name": va.bank_name,
                        "account_name": va.account_name
                    }
                }, status=200)
            else:
                msg = account_res.get('message') if account_res else "Unexpected error during virtual account creation"
                return Response({"status": "ERROR", "message": msg}, status=500)

        except Exception as e:
            return Response({"status": "ERROR", "message": f"An error occurred: {str(e)}"}, status=500)

    # ─── Reset User Login PIN (Admin) ───

    @extend_schema(
        tags=["Admin User Management"],
        summary="Reset a user's login PIN",
        description="Allows an admin to reset a specific user's login PIN (password). "
                    "Admins should change their own PIN via the account endpoint `/api/account/change-pin/`.",
        request={"application/json": {"type": "object", "properties": {
            "new_pin": {"type": "string", "description": "New login PIN for the user (4-6 digits)"}
        }, "required": ["new_pin"]}},
        responses={200: AdminStatusResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='reset-login-pin')
    def reset_login_pin(self, request, pk=None):
        user = self.get_object()
        new_pin = request.data.get('new_pin')
        if not new_pin or len(new_pin) < 4:
            return Response({"error": "A valid PIN (min 4 digits) is required."}, status=400)
        user.set_password(new_pin)
        user.save()
        log_admin_action(
            user=request.user,
            action_type="RESET_LOGIN_PIN",
            description=f"Reset login PIN for user {user.phone_number}",
            target=user
        )
        NotificationService.send_from_template(user, "login-pin-reset", {})
        return Response({"status": "SUCCESS", "message": f"Login PIN reset for user {user.phone_number}."})


@extend_schema_view(
    list=extend_schema(tags=["Admin KYC Management"], summary="List all KYC applications"),
    retrieve=extend_schema(tags=["Admin KYC Management"], summary="Get details of a specific KYC application"),
)
class AdminKYCViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user KYC applications. Allows listing, searching, 
    and updating statuses.
    """
    queryset = KYC.objects.select_related('user', 'processed_by').all().order_by('-created_at')
    serializer_class = KYCSerializer
    permission_classes = [CanManageUsers]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__phone_number', 'user__first_name', 'user__last_name', 'id_number']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        return self.queryset

    @extend_schema(tags=["Admin KYC Management"], summary="Find KYC by User ID")
    @action(detail=False, methods=['get'], url_path='by-user/(?P<user_id>[^/.]+)')
    def by_user_id(self, request, user_id=None):
        kyc = get_object_or_404(KYC, user_id=user_id)
        return Response(KYCSerializer(kyc).data)

    @extend_schema(tags=["Admin KYC Management"], summary="Find KYC by Phone Number")
    @action(detail=False, methods=['get'], url_path='by-phone/(?P<phone>[^/.]+)')
    def by_phone(self, request, phone=None):
        kyc = get_object_or_404(KYC, user__phone_number=phone)
        return Response(KYCSerializer(kyc).data)

    @extend_schema(
        tags=["Admin KYC Management"],
        summary="Update KYC status (Approve/Reject)",
        request=inline_serializer("KYCUpdateStatusRequest", fields={
            "action": serializers.ChoiceField(choices=['APPROVE', 'REJECT']),
            "reason": serializers.CharField(required=False)
        }),
        responses={200: AdminStatusResponseSerializer, 400: AdminErrorResponseSerializer}
    )
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        kyc = self.get_object()
        if kyc.status == 'APPROVED':
            return Response({"error": "KYC already approved and cannot be modified."}, status=400)
             
        action_type = request.data.get('action') # 'APPROVE' or 'REJECT'
        reason = request.data.get('reason', '')

        if action_type == 'APPROVE':
            kyc.status = 'APPROVED'
            kyc.time_accepted = timezone.now()
            kyc.user.is_kyc_verified = True
            kyc.user.save(update_fields=['is_kyc_verified'])
            NotificationService.send_from_template(kyc.user, "kyc-approved", {})
        elif action_type == 'REJECT':
            kyc.status = 'REJECTED'
            kyc.time_rejected = timezone.now()
            kyc.user.is_kyc_verified = False
            kyc.user.save(update_fields=['is_kyc_verified'])
            NotificationService.send_from_template(kyc.user, "kyc-rejected", {"reason": reason})
        else:
            return Response({"error": "Invalid action. Use 'APPROVE' or 'REJECT'."}, status=400)
        
        kyc.remarks = reason
        kyc.processed_by = request.user
        kyc.save()
        
        log_admin_action(
            user=request.user,
            action_type=f"{action_type}_KYC",
            description=f"{action_type.capitalize()}d KYC for user {kyc.user.phone_number}",
            target=kyc
        )
        
        return Response({"status": "SUCCESS", "message": f"KYC status updated to {kyc.status}."})
