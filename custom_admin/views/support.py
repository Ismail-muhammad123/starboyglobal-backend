from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from custom_admin.mixins import PortalPermissionMixin
from support.models import SupportTicket, TicketMessage


class SupportListView(PortalPermissionMixin, View):
    required_permission = ('support.SupportTicket', 'view')

    def get(self, request):
        qs = SupportTicket.objects.all().select_related('user').order_by('-created_at')

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.lower())

        paginator = Paginator(qs, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'custom_admin/support/list.html', {
            'tickets': page_obj,
            'status_filter': status_filter or ''
        })


class SupportDetailView(PortalPermissionMixin, View):
    required_permission = ('support.SupportTicket', 'view')

    def get(self, request, pk):
        ticket = get_object_or_404(SupportTicket.objects.select_related('user'), pk=pk)
        messages = TicketMessage.objects.filter(ticket=ticket).select_related('sender').order_by('created_at')
        return render(request, 'custom_admin/support/detail.html', {
            'ticket': ticket,
            'messages': messages,
            'status_choices': SupportTicket.STATUS_CHOICES,
        })

    def post(self, request, pk):
        ticket = get_object_or_404(SupportTicket, pk=pk)
        reply_text = request.POST.get('message', '').strip()
        new_status = request.POST.get('status', '').strip()

        # Update status if provided
        if new_status and new_status in [s[0] for s in SupportTicket.STATUS_CHOICES]:
            ticket.status = new_status
            ticket.save(update_fields=['status', 'updated_at'])

        # Save reply if text is provided
        if reply_text:
            TicketMessage.objects.create(
                ticket=ticket,
                sender=request.user,
                message=reply_text,
                is_admin=True
            )
            if not new_status:
                ticket.status = 'in_progress'
                ticket.save(update_fields=['status', 'updated_at'])
            return JsonResponse({'status': 'success', 'message': 'Reply sent & ticket updated.'})

        return JsonResponse({'status': 'success', 'message': f'Ticket status updated to {ticket.get_status_display()}.'})
