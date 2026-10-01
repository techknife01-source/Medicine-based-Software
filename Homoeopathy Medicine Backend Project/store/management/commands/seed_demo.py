from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from store.models import Appointment, Doctor, Medicine, Order, OrderItem, FAQ, SiteContent


class Command(BaseCommand):
    help = "Create the admin account and starter VerdantCare data."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(username="admin", defaults={"email": "admin@verdantcare.local", "is_staff": True, "is_superuser": True})
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("admin12345")
        admin.save()

        customer, _ = User.objects.get_or_create(username="maya", defaults={"first_name": "Maya", "last_name": "Sharma", "email": "maya@example.com"})
        customer.set_password("customer12345")
        customer.save()

        doctors = [
            ("Ananya Mehta", "Classical Homoeopathy", 12, Decimal("800")),
            ("Rohan Kapoor", "Child Wellness", 9, Decimal("650")),
            ("Ishita Sen", "Women's Health", 15, Decimal("900")),
        ]
        doctor_objects = []
        for name, specialty, years, fee in doctors:
            doctor_objects.append(Doctor.objects.get_or_create(name=name, defaults={"specialty": specialty, "experience_years": years, "consultation_fee": fee, "bio": "Thoughtful, evidence-informed homoeopathic consultations."})[0])

        medicines = [
            ("Arnica Montana 30C", "First Aid", Decimal("180"), 42, True),
            ("Nux Vomica 30C", "Digestive Care", Decimal("150"), 28, True),
            ("Rhus Tox 30C", "Joint Comfort", Decimal("210"), 18, True),
            ("Kali Phos 6X", "Daily Wellness", Decimal("195"), 35, False),
            ("Aconite 30C", "Seasonal Care", Decimal("160"), 26, False),
        ]
        medicine_objects = []
        for name, category, price, stock, featured in medicines:
            medicine_objects.append(Medicine.objects.get_or_create(name=name, defaults={"category": category, "price": price, "stock": stock, "featured": featured, "description": "Carefully prepared homoeopathic medicine from our trusted dispensary."})[0])

        if not Order.objects.exists():
            order = Order.objects.create(customer=customer, total_amount=Decimal("330"), status="completed", shipping_address="42 Neem Lane, Pune")
            OrderItem.objects.create(order=order, medicine=medicine_objects[0], quantity=1, unit_price=medicine_objects[0].price)
            OrderItem.objects.create(order=order, medicine=medicine_objects[1], quantity=1, unit_price=medicine_objects[1].price)

        if not Appointment.objects.exists():
            Appointment.objects.create(customer=customer, doctor=doctor_objects[0], appointment_date=date.today() + timedelta(days=2), appointment_time=time(10, 30), reason="Seasonal wellness consultation", status="confirmed")

        pages = {
            "about": ("About VerdantCare", "VerdantCare brings thoughtful homoeopathic care, trusted remedies, and qualified consultations together in one calm place."),
            "contact": ("Contact us", "Email care@verdantcare.local or call +91 00000 00000. Our care team is available Monday to Saturday."),
            "privacy": ("Privacy policy", "We use your information only to provide orders, appointments, support, and notifications. Prescription files are private and access-controlled."),
            "terms": ("Terms of service", "By using VerdantCare, you agree to provide accurate account details and use medicines only as advised by a qualified practitioner."),
            "shipping-returns": ("Shipping & returns", "Orders are packed with care and dispatched after payment confirmation. Contact support for damaged, incorrect, or missing items."),
        }
        for key, (title, body) in pages.items():
            SiteContent.objects.get_or_create(key=key, defaults={"title": title, "body": body})
        FAQ.objects.get_or_create(question="How quickly will my order arrive?", defaults={"answer": "Most local orders arrive within 2 to 5 working days."})

        self.stdout.write(self.style.SUCCESS("Demo data ready. Admin login: admin / admin12345"))
