from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from custom_admin.permissions import PortalPermission, PortalGroupMembership


def user_has_portal_permission(user, resource, action='view'):
    """
    Check if a user has a specific permission on a portal resource.
    - Superusers always pass.
    - Must be authenticated and staff/admin.
    - Checks standard Django model permissions (app_label.action).
    - Checks assigned PortalGroup permissions.
    - Falls back to StaffPermission model flags for backwards compatibility.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if not (getattr(user, 'is_staff', False) or getattr(user, 'is_admin', False)):
        return False

    # Check standard Django Model permissions (e.g. 'wallet.adjust_wallet', 'payments.approve_withdrawal')
    if '.' in resource:
        app_label = resource.split('.')[0].lower()
        if user.has_perm(f"{app_label}.{action}"):
            return True

    # Check PortalGroup permissions
    has_group_perm = PortalPermission.objects.filter(
        resource=resource,
        action=action,
        groups__memberships__user=user
    ).exists()

    if has_group_perm:
        return True

    # Fallback to StaffPermission flags
    staff_perm = getattr(user, 'staff_permissions', None)
    if not staff_perm:
        return False

    resource_app = resource.split('.')[0] if '.' in resource else resource

    if resource_app == 'users':
        return getattr(staff_perm, 'can_manage_users', False)

    if resource_app == 'orders':
        return getattr(staff_perm, 'can_manage_vtu', False)

    if resource_app in ['wallet']:
        return getattr(staff_perm, 'can_manage_wallets', False)

    if resource in ['payments.Deposit', 'payments.Withdrawal', 'payments.PaystackConfig']:
        return getattr(staff_perm, 'can_manage_payments', False)

    if resource in ['payments.AdminTransfer', 'payments.AdminTransferBeneficiary']:
        return getattr(staff_perm, 'can_initiate_transfers', False) or getattr(staff_perm, 'can_manage_payments', False)

    if resource_app == 'summary' or resource in ['wallet.BonusConfig', 'users.ReferralConfig', 'users.RoleUpgradeConfig']:
        return getattr(staff_perm, 'can_manage_site_config', False)

    if resource_app == 'notifications' or resource == 'support.SupportTicket':
        return getattr(staff_perm, 'can_manage_notifications', False)

    return False


class PortalLoginRequired(LoginRequiredMixin):
    """Ensures user is logged in and is staff/admin."""
    login_url = reverse_lazy('portal:login')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_staff or request.user.is_admin or request.user.is_superuser):
            raise PermissionDenied("You do not have administrative access to the portal.")
        return super().dispatch(request, *args, **kwargs)


class PortalPermissionMixin(PortalLoginRequired):
    """
    Mixin for CBVs. Requires required_permission = ('resource', 'action')
    or a list of such tuples (any match or all match based on require_all_permissions).
    """
    required_permission = None  # e.g. ('orders.Purchase', 'view')
    require_all_permissions = False

    def get_required_permissions(self):
        if self.required_permission is None:
            return []
        if isinstance(self.required_permission, tuple) and len(self.required_permission) == 2 and isinstance(self.required_permission[0], str):
            return [self.required_permission]
        return self.required_permission

    def has_permission(self):
        perms = self.get_required_permissions()
        if not perms:
            return True

        if self.require_all_permissions:
            return all(user_has_portal_permission(self.request.user, res, act) for res, act in perms)
        else:
            return any(user_has_portal_permission(self.request.user, res, act) for res, act in perms)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portal:login')
        if not self.has_permission():
            raise PermissionDenied("You do not have permission to access this portal page.")
        return super().dispatch(request, *args, **kwargs)


class SuperuserOnlyMixin(PortalLoginRequired):
    """Mixin that restricts access strictly to superusers."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portal:login')
        if not request.user.is_superuser:
            raise PermissionDenied("This page is restricted to superusers only.")
        return super().dispatch(request, *args, **kwargs)
