from rest_framework import permissions

class StaffPermissionBase(permissions.BasePermission):
    """
    Base permission for staff users.
    Checks if user is staff or superuser.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_admin or request.user.is_superuser)


class CanManageUsers(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_manage_users', False)


class CanManageWallets(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_manage_wallets', False)


class CanManageVTU(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_manage_vtu', False)


class CanManagePayments(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_manage_payments', False)


class CanManageSiteConfig(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_manage_site_config', False)


class CanInitiateTransfers(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_initiate_transfers', False)
        

class CanManageNotifications(StaffPermissionBase):
    def has_permission(self, request, view):
        if not super().has_permission(request, view): return False
        if request.user.is_superuser: return True
        return getattr(getattr(request.user, 'staff_permissions', None), 'can_manage_notifications', False)


class IsSuperUserOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser
