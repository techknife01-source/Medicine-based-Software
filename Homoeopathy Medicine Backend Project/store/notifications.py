import logging
from django.conf import settings
from django.core.mail import send_mail

from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)

EVENT_COPY = {
    "order_placed": ("Order received", "Your order #{id} has been placed successfully."),
    "order_confirmed": ("Order confirmed", "Your order #{id} has been confirmed and is being prepared."),
    "order_shipped": ("Order on the way", "Your order #{id} has been shipped."),
    "order_delivered": ("Order delivered", "Your order #{id} has been delivered. We hope it serves you well."),
    "order_cancelled": ("Order cancelled", "Your order #{id} has been cancelled."),
    "appointment_booked": ("Appointment request received", "Your appointment with Dr. {doctor} has been booked."),
    "appointment_confirmed": ("Appointment confirmed", "Your appointment with Dr. {doctor} is confirmed for {date} at {time}."),
    "appointment_rescheduled": ("Appointment rescheduled", "Your appointment with Dr. {doctor} is now {date} at {time}."),
    "appointment_cancelled": ("Appointment cancelled", "Your appointment with Dr. {doctor} has been cancelled."),
    "appointment_reminder": ("Appointment reminder", "A reminder: your appointment with Dr. {doctor} is {date} at {time}."),
}


def notify_user(user, event, **values):
    if not user or not user.is_active or event not in EVENT_COPY:
        return
    preferences, _ = NotificationPreference.objects.get_or_create(user=user)
    title_template, message_template = EVENT_COPY[event]
    values.setdefault("id", values.get("order_id", ""))
    title = title_template.format(**values)
    message = message_template.format(**values)
    channels = []
    if preferences.site_enabled:
        channels.append("site")
    if preferences.email_enabled and user.email:
        channels.append("email")
    if preferences.sms_enabled and preferences.phone_number:
        channels.append("sms")
    for channel in channels:
        notification = Notification.objects.create(user=user, event=event, channel=channel, title=title, message=message)
        if channel == "site":
            notification.delivered = True
        elif channel == "email":
            send_mail(title, message, getattr(settings, "DEFAULT_FROM_EMAIL", "notifications@verdantcare.local"), [user.email], fail_silently=True)
            notification.delivered = True
        else:
            # SMS is intentionally provider-neutral. Configure a provider in production;
            # local development records the delivery without sending an external message.
            logger.info("SMS notification for %s to %s: %s", user.username, preferences.phone_number, message)
            notification.delivered = True
        notification.save(update_fields=["delivered"])
