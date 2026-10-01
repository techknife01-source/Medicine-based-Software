from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from store.models import Appointment
from store.notifications import notify_user


class Command(BaseCommand):
    help = "Send site/email/SMS reminders for appointments happening tomorrow."

    def handle(self, *args, **options):
        target_date = timezone.localdate() + timedelta(days=1)
        appointments = Appointment.objects.select_related("customer", "doctor").filter(
            appointment_date=target_date,
            status__in=("requested", "confirmed", "rescheduled"),
        )
        sent = 0
        for appointment in appointments:
            notify_user(
                appointment.customer,
                "appointment_reminder",
                doctor=appointment.doctor.name,
                date=appointment.appointment_date.strftime("%d %b %Y"),
                time=appointment.appointment_time.strftime("%I:%M %p"),
            )
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} appointment reminder(s) for {target_date}."))
