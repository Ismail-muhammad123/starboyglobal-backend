
from django.db import models
from django.conf import settings

class Notification(models.Model):
    CHANNEL_CHOICES = [
        ('fcm', 'Push (FCM)'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    title = models.CharField(max_length=255)
    body = models.TextField()
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    
    # Metadata for deep linking or extra info
    data = models.JSONField(default=dict, blank=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_notifications")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("send_notification", "Can send notifications and announcements to users"),
        ]

    def __str__(self):
        return f"{self.get_channel_display()}: {self.title}"

class UserNotification(models.Model):
    STATUS_CHOICES = [
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="user_notifications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SENT")
    error_message = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('notification', 'user')

    def __str__(self):
        return f"Notification for {self.user.phone_number}: {self.notification.title}"


class NotificationTemplate(models.Model):
    slug = models.SlugField(unique=True, help_text="System identifier (e.g. wallet-funded, purchase-success)")
    title = models.CharField(max_length=255)
    body = models.TextField(help_text="Default body. Use placeholders: {username}, {amount}, {reference}, {service}, {status}, {balance}")
    
    # Per-template channel toggles
    use_fcm = models.BooleanField(default=True)
    use_email = models.BooleanField(default=True)
    use_sms = models.BooleanField(default=False)
    use_whatsapp = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.slug} ({self.title})"

class Announcement(models.Model):
    AUDIENCE_CHOICES = [('all','All Users'),('agents','Agents Only'),('customers','Customers Only')]
    title = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to='announcements/', blank=True, null=True)
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_announcements")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("send_announcement", "Can create and broadcast announcements"),
        ]

    def __str__(self):
        return self.title
