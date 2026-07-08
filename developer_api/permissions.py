from rest_framework import permissions

class IsDeveloperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if hasattr(request, 'developer_profile'):
            return request.developer_profile.is_active
        if request.user and request.user.is_authenticated:
            try:
                profile = request.user.developer_profile
                request.developer_profile = profile
                return profile.is_active
            except Exception:
                pass
        return False
