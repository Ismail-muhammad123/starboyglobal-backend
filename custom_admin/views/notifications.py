from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.core.paginator import Paginator

from custom_admin.mixins import PortalPermissionMixin
from notifications.models import Announcement, Notification, UserNotification
from notifications.utils import NotificationService

User = get_user_model()


# ── Send Notification ─────────────────────────────────────────────────────────

class SendNotificationView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'add')

    TARGET_OPTIONS = [
        ('all',      'All Users',      '👥'),
        ('role',     'By Role',        '🎭'),
        ('kyc',      'By KYC Status',  '✅'),
        ('specific', 'Specific Users', '🔍'),
        ('staff',    'Staff Only',     '🔐'),
    ]

    def get(self, request):
        return render(request, 'custom_admin/notifications/send.html', {
            'target_options': self.TARGET_OPTIONS,
        })

    def post(self, request):
        title    = request.POST.get('title', '').strip()
        body     = request.POST.get('body', '').strip()
        channels = request.POST.getlist('channels')
        target   = request.POST.get('target', 'all')

        if not title or not body:
            return JsonResponse({'status': 'error', 'message': 'Title and body are required.'}, status=400)
        if not channels:
            return JsonResponse({'status': 'error', 'message': 'Select at least one channel.'}, status=400)

        try:
            if target == 'all':
                users = list(User.objects.filter(is_active=True, is_staff=False))
            elif target == 'role':
                role = request.POST.get('role', 'customer')
                users = list(User.objects.filter(is_active=True, role=role, is_staff=False))
            elif target == 'kyc':
                is_verified = request.POST.get('kyc_status', 'verified') == 'verified'
                users = list(User.objects.filter(is_active=True, is_kyc_verified=is_verified, is_staff=False))
            elif target == 'specific':
                raw = request.POST.get('phones', '')
                phone_list = [p.strip() for p in raw.replace(',', '\n').splitlines() if p.strip()]
                users = list(User.objects.filter(phone_number__in=phone_list))
            elif target == 'staff':
                users = list(User.objects.filter(is_staff=True, is_active=True))
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid target type.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error resolving audience: {e}'}, status=500)

        if not users:
            return JsonResponse({'status': 'error', 'message': 'No users matched the selected criteria.'}, status=400)

        sent_channels, errors = [], []
        for channel in channels:
            try:
                NotificationService.create_notification(
                    users=users, title=title, body=body, channel=channel,
                    data={'type': 'admin_broadcast'}, created_by=request.user,
                )
                sent_channels.append(channel.upper())
            except Exception as e:
                errors.append(f'{channel}: {e}')

        if not sent_channels:
            return JsonResponse({'status': 'error', 'message': f'All channels failed: {"; ".join(errors)}'}, status=500)

        msg = f'Sent to {len(users)} user(s) via {", ".join(sent_channels)}.'
        if errors:
            msg += f' Errors: {"; ".join(errors)}'
        return JsonResponse({'status': 'success', 'message': msg})


# ── Notification Log ──────────────────────────────────────────────────────────

class NotificationLogView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'view')

    def get(self, request):
        qs = (
            Notification.objects
            .select_related('created_by')
            .annotate(
                total=Count('user_notifications'),
                sent=Count('user_notifications', filter=Q(user_notifications__status='SENT')),
                failed=Count('user_notifications', filter=Q(user_notifications__status='FAILED')),
            )
        )

        # Filters
        search    = request.GET.get('q', '').strip()
        channel   = request.GET.get('channel', '')
        sent_by   = request.GET.get('sent_by', '').strip()
        date_from = request.GET.get('date_from', '')
        date_to   = request.GET.get('date_to', '')
        sort      = request.GET.get('sort', '-created_at')

        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search))
        if channel:
            qs = qs.filter(channel=channel)
        if sent_by:
            qs = qs.filter(
                Q(created_by__phone_number__icontains=sent_by) |
                Q(created_by__full_name__icontains=sent_by) |
                Q(created_by__first_name__icontains=sent_by) |
                Q(created_by__last_name__icontains=sent_by)
            )
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        VALID_SORTS = {
            '-created_at': '-created_at', 'created_at': 'created_at',
            '-total': '-total', '-sent': '-sent', '-failed': '-failed',
        }
        qs = qs.order_by(VALID_SORTS.get(sort, '-created_at'))

        paginator = Paginator(qs, 50)
        page      = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'custom_admin/notifications/log.html', {
            'page_obj': page,
            'total_count': paginator.count,
            'q': search,
            'channel': channel,
            'sent_by': sent_by,
            'date_from': date_from,
            'date_to': date_to,
            'sort': sort,
            'channel_choices': Notification.CHANNEL_CHOICES,
        })


# ── Announcements List ────────────────────────────────────────────────────────

class AnnouncementListView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'view')

    def get(self, request):
        qs = Announcement.objects.select_related('created_by')

        search    = request.GET.get('q', '').strip()
        audience  = request.GET.get('audience', '')
        status    = request.GET.get('status', '')
        date_from = request.GET.get('date_from', '')
        date_to   = request.GET.get('date_to', '')
        sort      = request.GET.get('sort', '-created_at')

        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(body__icontains=search))
        if audience:
            qs = qs.filter(audience=audience)
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        VALID_SORTS = {
            '-created_at': '-created_at', 'created_at': 'created_at',
            '-expires_at': '-expires_at',  'expires_at': 'expires_at',
            'title': 'title',
        }
        qs = qs.order_by(VALID_SORTS.get(sort, '-created_at'))

        paginator = Paginator(qs, 25)
        page      = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'custom_admin/notifications/announcements_list.html', {
            'page_obj': page,
            'total_count': paginator.count,
            'q': search,
            'audience': audience,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
            'sort': sort,
            'audience_choices': Announcement.AUDIENCE_CHOICES,
        })


# ── Announcement Create ───────────────────────────────────────────────────────

class AnnouncementCreateView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'add')

    def get(self, request):
        return render(request, 'custom_admin/notifications/announcement_form.html', {
            'audience_choices': Announcement.AUDIENCE_CHOICES,
            'form_title': 'Create Announcement',
            'submit_label': 'Create',
            'cancel_url': 'portal:announcements_list',
        })

    def post(self, request):
        title     = request.POST.get('title', '').strip()
        body      = request.POST.get('body', '').strip()
        audience  = request.POST.get('audience', 'all')
        is_active = request.POST.get('is_active') in ('on', 'true', '1')
        starts_at = request.POST.get('starts_at') or None
        expires_at = request.POST.get('expires_at') or None
        image = request.FILES.get('image')

        if not title or not body:
            return JsonResponse({'status': 'error', 'message': 'Title and body are required.'}, status=400)

        ann = Announcement(
            title=title, body=body, audience=audience,
            is_active=is_active, starts_at=starts_at, expires_at=expires_at,
            created_by=request.user,
        )
        if image:
            ann.image = image
        ann.save()
        return JsonResponse({'status': 'success', 'message': f'Announcement "{title}" created.', 'redirect': '/portal/notifications/announcements/'})


# ── Announcement Edit ─────────────────────────────────────────────────────────

class AnnouncementEditView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'change')

    def get(self, request, pk):
        ann = get_object_or_404(Announcement, pk=pk)
        return render(request, 'custom_admin/notifications/announcement_form.html', {
            'announcement': ann,
            'audience_choices': Announcement.AUDIENCE_CHOICES,
            'form_title': 'Edit Announcement',
            'submit_label': 'Save Changes',
            'cancel_url': 'portal:announcements_list',
        })

    def post(self, request, pk):
        ann = get_object_or_404(Announcement, pk=pk)
        ann.title     = request.POST.get('title', '').strip() or ann.title
        ann.body      = request.POST.get('body', '').strip() or ann.body
        ann.audience  = request.POST.get('audience', ann.audience)
        ann.is_active = request.POST.get('is_active') in ('on', 'true', '1')
        ann.starts_at  = request.POST.get('starts_at') or None
        ann.expires_at = request.POST.get('expires_at') or None
        image = request.FILES.get('image')
        if image:
            ann.image = image
        ann.save()
        return JsonResponse({'status': 'success', 'message': f'Announcement "{ann.title}" updated.', 'redirect': '/portal/notifications/announcements/'})


# ── Announcement Toggle ───────────────────────────────────────────────────────

class AnnouncementToggleView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'change')

    def post(self, request, pk):
        ann = get_object_or_404(Announcement, pk=pk)
        ann.is_active = not ann.is_active
        ann.save(update_fields=['is_active'])
        state = 'activated' if ann.is_active else 'deactivated'
        return JsonResponse({'status': 'success', 'message': f'Announcement {state}.', 'is_active': ann.is_active})


# ── Announcement Delete ───────────────────────────────────────────────────────

class AnnouncementDeleteView(PortalPermissionMixin, View):
    required_permission = ('notifications.Announcement', 'delete')

    def post(self, request, pk):
        ann = get_object_or_404(Announcement, pk=pk)
        title = ann.title
        ann.delete()
        return JsonResponse({'status': 'success', 'message': f'Announcement "{title}" deleted.'})
