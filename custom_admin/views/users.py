from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import Group, Permission
from custom_admin.mixins import PortalPermissionMixin
from users.models import User, KYC
from wallet.models import Wallet, WalletTransaction
from orders.models import Purchase
from admin_api.models import AdminActionLog


class UserListView(PortalPermissionMixin, View):
    required_permission = ('users.User', 'view')

    def get(self, request):
        qs = User.objects.all().order_by('-created_at')

        role = request.GET.get('role')
        if role:
            qs = qs.filter(role=role)

        status_filter = request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        search = request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(phone_number__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        per_page = request.GET.get('per_page', 25)
        try:
            per_page = int(per_page)
            if per_page not in [25, 50, 100, 200]:
                per_page = 25
        except (ValueError, TypeError):
            per_page = 25

        paginator = Paginator(qs, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'users': page_obj,
            'role_filter': role or '',
            'status_filter': status_filter or '',
            'search_query': search or '',
            'per_page': per_page,
        }
        return render(request, 'custom_admin/users/list.html', context)


class UserEditView(PortalPermissionMixin, View):
    required_permission = ('users.User', 'change')

    def get(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        all_groups = Group.objects.all()
        all_permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'content_type__model', 'codename')
        context = {
            'target_user': user_obj,
            'country_codes': User.country_code_choices,
            'role_choices': User.ROLE_CHOICES,
            'all_groups': all_groups,
            'all_permissions': all_permissions,
            'user_group_ids': set(user_obj.groups.values_list('id', flat=True)),
            'user_permission_ids': set(user_obj.user_permissions.values_list('id', flat=True)),
        }
        return render(request, 'custom_admin/users/edit.html', context)

    def post(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)

        user_obj.first_name = request.POST.get('first_name', '').strip()
        user_obj.last_name = request.POST.get('last_name', '').strip()
        user_obj.middle_name = request.POST.get('middle_name', '').strip()
        user_obj.email = request.POST.get('email', '').strip()
        user_obj.phone_country_code = request.POST.get('phone_country_code', '+234').strip()
        user_obj.phone_number = request.POST.get('phone_number', '').strip()
        user_obj.role = request.POST.get('role', 'customer').strip()

        user_obj.is_active = request.POST.get('is_active') == 'true'
        user_obj.is_verified = request.POST.get('is_verified') == 'true'
        user_obj.email_verified = request.POST.get('email_verified') == 'true'
        user_obj.phone_number_verified = request.POST.get('phone_number_verified') == 'true'
        user_obj.is_kyc_verified = request.POST.get('is_kyc_verified') == 'true'

        comm_rate = request.POST.get('agent_commission_rate', '0.00').strip()
        try:
            user_obj.agent_commission_rate = float(comm_rate)
        except ValueError:
            pass

        referral_code = request.POST.get('referral_code', '').strip()
        if referral_code:
            user_obj.referral_code = referral_code

        # Optional new transaction PIN
        new_pin = request.POST.get('new_transaction_pin', '').strip()
        if new_pin:
            user_obj.set_transaction_pin(new_pin)

        # Optional new password
        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            user_obj.set_password(new_password)

        user_obj.save()

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type="UPDATE_USER_PROFILE",
            target_model="User",
            target_id=str(user_obj.pk),
            description=f"Updated profile details for user {user_obj.phone_number}."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Profile for user {user_obj.phone_number} updated successfully.",
            'redirect_url': f"/portal/users/{user_obj.pk}/"
        })


class UserDetailView(PortalPermissionMixin, View):
    required_permission = ('users.User', 'view')

    def get(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        wallet, _ = Wallet.objects.get_or_create(user=user_obj)
        recent_purchases = Purchase.objects.filter(user=user_obj).order_by('-time')[:15]
        recent_txs = WalletTransaction.objects.filter(user=user_obj).order_by('-timestamp')[:15]
        kyc = getattr(user_obj, 'kyc', None)

        all_groups = Group.objects.all()
        all_permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'content_type__model', 'codename')

        context = {
            'target_user': user_obj,
            'wallet': wallet,
            'purchases': recent_purchases,
            'transactions': recent_txs,
            'kyc': kyc,
            'all_groups': all_groups,
            'all_permissions': all_permissions,
            'user_group_ids': set(user_obj.groups.values_list('id', flat=True)),
            'user_permission_ids': set(user_obj.user_permissions.values_list('id', flat=True)),
        }
        return render(request, 'custom_admin/users/detail.html', context)


class UserPermissionsUpdateView(PortalPermissionMixin, View):
    required_permission = ('users.User', 'change')

    def post(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)

        if request.user.is_superuser:
            user_obj.is_staff = request.POST.get('is_staff') == 'true' or request.POST.get('is_staff') == 'on'
            user_obj.is_superuser = request.POST.get('is_superuser') == 'true' or request.POST.get('is_superuser') == 'on'
            user_obj.save(update_fields=['is_staff', 'is_superuser'])

        group_ids = request.POST.getlist('groups')
        user_obj.groups.set(group_ids)

        perm_ids = request.POST.getlist('user_permissions')
        user_obj.user_permissions.set(perm_ids)

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type="UPDATE_USER_PERMISSIONS",
            target_model="User",
            target_id=str(user_obj.pk),
            description=f"Updated groups and permissions for user {user_obj.phone_number}."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"Groups & permissions updated for user {user_obj.phone_number}."
        })


class UserSuspendView(PortalPermissionMixin, View):
    required_permission = ('users.User', 'change')

    def post(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        user_obj.is_active = not user_obj.is_active
        user_obj.save()

        state = "activated" if user_obj.is_active else "suspended"
        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type="TOGGLE_USER_STATUS",
            target_model="User",
            target_id=str(user_obj.pk),
            description=f"User {user_obj.phone_number} set to {state}."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"User {user_obj.phone_number} is now {state}.",
            'is_active': user_obj.is_active
        })


class UserRoleUpdateView(PortalPermissionMixin, View):
    required_permission = ('users.User', 'change')

    def post(self, request, pk):
        user_obj = get_object_or_404(User, pk=pk)
        new_role = request.POST.get('role')

        if new_role not in ['customer', 'agent', 'developer']:
            return JsonResponse({'status': 'error', 'message': 'Invalid role.'}, status=400)

        old_role = user_obj.role
        user_obj.role = new_role
        user_obj.upgraded_at = timezone.now()
        user_obj.upgraded_by = request.user
        user_obj.save()

        AdminActionLog.objects.create(
            admin_user=request.user,
            action_type="UPDATE_USER_ROLE",
            target_model="User",
            target_id=str(user_obj.pk),
            description=f"Role for {user_obj.phone_number} updated from {old_role} to {new_role}."
        )

        return JsonResponse({
            'status': 'success',
            'message': f"User role updated to {new_role}."
        })


class KYCListView(PortalPermissionMixin, View):
    required_permission = ('users.KYC', 'view')

    def get(self, request):
        qs = KYC.objects.all().order_by('-created_at')

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        per_page = request.GET.get('per_page', 25)
        try:
            per_page = int(per_page)
            if per_page not in [25, 50, 100, 200]:
                per_page = 25
        except (ValueError, TypeError):
            per_page = 25

        paginator = Paginator(qs, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'kycs': page_obj,
            'status_filter': status_filter or '',
            'per_page': per_page,
        }
        return render(request, 'custom_admin/kyc/list.html', context)


class KYCDetailView(PortalPermissionMixin, View):
    required_permission = ('users.KYC', 'view')

    def get(self, request, pk):
        kyc_obj = get_object_or_404(KYC, pk=pk)
        return render(request, 'custom_admin/kyc/detail.html', {'kyc': kyc_obj})


class KYCApproveView(PortalPermissionMixin, View):
    required_permission = ('users.KYC', 'change')

    def post(self, request, pk):
        kyc_obj = get_object_or_404(KYC, pk=pk)
        action_type = request.POST.get('action_type')  # approve / reject
        remarks = request.POST.get('remarks', '').strip()

        if action_type == 'approve':
            kyc_obj.status = 'APPROVED'
            kyc_obj.time_accepted = timezone.now()
            kyc_obj.processed_by = request.user
            kyc_obj.remarks = remarks
            kyc_obj.save()

            kyc_obj.user.is_kyc_verified = True
            kyc_obj.user.is_verified = True
            kyc_obj.user.save(update_fields=['is_kyc_verified', 'is_verified'])

            msg = "KYC approved successfully."
        elif action_type == 'reject':
            kyc_obj.status = 'REJECTED'
            kyc_obj.time_rejected = timezone.now()
            kyc_obj.processed_by = request.user
            kyc_obj.remarks = remarks
            kyc_obj.save()

            kyc_obj.user.is_kyc_verified = False
            kyc_obj.user.save(update_fields=['is_kyc_verified'])

            msg = "KYC rejected."
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

        return JsonResponse({'status': 'success', 'message': msg})
