from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Appointment, Order
from .notifications import notify_user


@receiver(pre_save, sender=Order, dispatch_uid="store.capture_order_status")
def capture_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_event = "order_placed"
        return
    previous = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    instance._notification_event = f"order_{instance.status}" if previous != instance.status and instance.status in {"confirmed", "shipped", "delivered", "cancelled"} else None


@receiver(post_save, sender=Order, dispatch_uid="store.order_notification")
def order_notification(sender, instance, created, **kwargs):
    event = getattr(instance, "_notification_event", None)
    if created:
        event = "order_placed"
    if event:
        notify_user(instance.customer, event, order_id=instance.pk)


@receiver(pre_save, sender=Appointment, dispatch_uid="store.capture_appointment_event")
def capture_appointment_event(sender, instance, **kwargs):
    if not instance.pk:
        instance._notification_event = "appointment_booked"
        return
    previous = sender.objects.filter(pk=instance.pk).values("status", "appointment_date", "appointment_time").first()
    if previous and (previous["appointment_date"] != instance.appointment_date or previous["appointment_time"] != instance.appointment_time):
        instance._notification_event = "appointment_rescheduled"
    elif previous and previous["status"] != instance.status and instance.status in {"confirmed", "rescheduled", "cancelled"}:
        instance._notification_event = f"appointment_{instance.status}"
    else:
        instance._notification_event = None


@receiver(post_save, sender=Appointment, dispatch_uid="store.appointment_notification")
def appointment_notification(sender, instance, created, **kwargs):
    event = getattr(instance, "_notification_event", None)
    if created:
        event = "appointment_booked"
    if event:
        notify_user(
            instance.customer,
            event,
            doctor=instance.doctor.name,
            date=instance.appointment_date.strftime("%d %b %Y"),
            time=instance.appointment_time.strftime("%I:%M %p"),
        )
