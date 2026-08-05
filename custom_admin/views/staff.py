from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from custom_admin.mixins import SuperuserOnlyMixin
from users.models import User
from custom_admin.permissions import PortalPermission, PortalGroup, PortalGroupMembership, RESOURCES_LIST


class StaffListView(SuperuserOnlyMixin, View):
    def get(self, request):
        staff_users = User.objects.filter(is_staff=True).order_by('-created_at')
        groups = PortalGroup.objects.all()
        return render(request, 'custom_admin/staff/list.html', {
            'staff_members': staff_users,
            'groups': groups
        })

    def post(self, request):
        phone = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        if User.objects.filter(phone_number=phone).exists():
            return JsonResponse({'status': 'error', 'message': 'User with this phone number already exists.'}, status=400)

        user = User.objects.create_user(
            phone_number=phone,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_active=True
        )

        group_ids = request.POST.getlist('groups')
        for gid in group_ids:
            grp = PortalGroup.objects.filter(pk=gid).first()
            if grp:
                PortalGroupMembership.objects.create(user=user, group=grp)

        return JsonResponse({'status': 'success', 'message': f"Staff account {phone} created successfully."})


class PortalGroupListView(SuperuserOnlyMixin, View):
    def get(self, request):
        groups = PortalGroup.objects.all().prefetch_related('permissions')
        return render(request, 'custom_admin/staff/groups.html', {'groups': groups})

    def post(self, request):
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if PortalGroup.objects.filter(name=name).exists():
            return JsonResponse({'status': 'error', 'message': f"Group '{name}' already exists."}, status=400)

        group = PortalGroup.objects.create(name=name, description=description)

        perm_ids = request.POST.getlist('permissions')
        if perm_ids:
            group.permissions.set(perm_ids)

        return JsonResponse({'status': 'success', 'message': f"Permission group '{name}' created."})


class PortalGroupDetailView(SuperuserOnlyMixin, View):
    def get(self, request, pk):
        group = get_object_or_404(PortalGroup, pk=pk)
        all_perms = PortalPermission.objects.all()

        # Group perms by resource
        resource_map = {}
        for res_code, res_title in RESOURCES_LIST:
            resource_map[res_code] = {
                'title': res_title,
                'view': all_perms.filter(resource=res_code, action='view').first(),
                'add': all_perms.filter(resource=res_code, action='add').first(),
                'change': all_perms.filter(resource=res_code, action='change').first(),
                'delete': all_perms.filter(resource=res_code, action='delete').first(),
            }

        assigned_perm_ids = set(group.permissions.values_list('id', flat=True))

        return render(request, 'custom_admin/staff/group_detail.html', {
            'group': group,
            'resource_map': resource_map,
            'assigned_perm_ids': assigned_perm_ids
        })

    def post(self, request, pk):
        group = get_object_or_404(PortalGroup, pk=pk)
        group.name = request.POST.get('name', group.name).strip()
        group.description = request.POST.get('description', '').strip()
        group.save()

        perm_ids = request.POST.getlist('permissions')
        group.permissions.set(perm_ids)

        return JsonResponse({'status': 'success', 'message': f"Group '{group.name}' updated successfully."})
