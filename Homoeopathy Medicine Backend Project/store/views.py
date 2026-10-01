from datetime import timedelta
from decimal import Decimal, InvalidOperation
import csv
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponse
from django.db.models import Count, Q, Sum
from django.utils.timezone import now
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Appointment, Banner, Coupon, Doctor, DoctorSlot, FAQ, Medicine, Notification, NotificationPreference, Order, OrderItem, Payment, Prescription, Review, SiteContent


def home(request):
    context = {
        "featured_medicines": Medicine.objects.filter(featured=True)[:4],
        "doctors": Doctor.objects.filter(available=True)[:3],
        "banners": Banner.objects.filter(published=True, featured=True)[:3],
    }
    return render(request, "store/home.html", context)


def medicine_list(request):
    return render(request, "store/medicines.html", {"medicines": Medicine.objects.prefetch_related("reviews").all()})


@login_required
def review_medicine(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    review = Review.objects.filter(medicine=medicine, customer=request.user).first()
    if request.method == "POST":
        if review is None:
            review = Review(medicine=medicine, customer=request.user)
        review.rating = request.POST["rating"]
        review.comment = request.POST["comment"].strip()
        review.approved = False
        review.moderated_at = None
        review.save()
        messages.success(request, "Thanks. Your review is waiting for moderation.")
        return redirect("medicine_list")
    return render(request, "store/review_form.html", {"medicine": medicine, "review": review})


def doctor_list(request):
    return render(request, "store/doctors.html", {"doctors": Doctor.objects.filter(available=True)})


@login_required
def appointment_list(request):
    appointments = Appointment.objects.filter(customer=request.user).select_related("doctor")
    return render(request, "store/appointments.html", {"appointments": appointments})


@login_required
def book_appointment(request):
    if request.method == "POST":
        doctor = Doctor.objects.get(pk=request.POST["doctor"])
        Appointment.objects.create(
            customer=request.user,
            doctor=doctor,
            appointment_date=request.POST["appointment_date"],
            appointment_time=request.POST["appointment_time"],
            reason=request.POST.get("reason", ""),
        )
        messages.success(request, "Appointment request received. Our team will confirm it shortly.")
        return redirect("appointment_list")
    return render(request, "store/book_appointment.html", {"doctors": Doctor.objects.filter(available=True)})


def staff_required(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(staff_required)
def dashboard(request):
    revenue = Order.objects.filter(status="completed").aggregate(total=Sum("total_amount"))["total"] or 0
    context = {
        "customer_count": User.objects.filter(is_staff=False).count(),
        "doctor_count": Doctor.objects.count(),
        "medicine_count": Medicine.objects.count(),
        "order_count": Order.objects.count(),
        "pending_orders": Order.objects.filter(status="pending").count(),
        "completed_orders": Order.objects.filter(status="completed").count(),
        "appointment_count": Appointment.objects.count(),
        "pending_appointments": Appointment.objects.filter(status="requested").count(),
        "revenue": revenue,
        "recent_orders": Order.objects.select_related("customer").all()[:5],
        "upcoming_appointments": Appointment.objects.select_related("customer", "doctor").filter(appointment_date__gte=timezone.localdate()).all()[:5],
    }
    return render(request, "store/dashboard.html", context)


@user_passes_test(staff_required)
def medicine_management(request):
    query = request.GET.get("q", "").strip()
    medicines = Medicine.objects.all()
    if query:
        medicines = medicines.filter(Q(name__icontains=query) | Q(category__icontains=query))
    if request.method == "POST":
        Medicine.objects.create(
            name=request.POST["name"], category=request.POST["category"], description=request.POST.get("description", ""),
            price=request.POST["price"], discount_percent=request.POST.get("discount_percent", 0), stock=request.POST.get("stock", 0),
            featured=request.POST.get("featured") == "on", image=request.FILES.get("image"), image_url=request.POST.get("image_url", ""),
        )
        messages.success(request, "Medicine added to the catalogue.")
        return redirect("medicine_management")
    return render(request, "store/manage_medicines.html", {"medicines": medicines, "query": query})


@user_passes_test(staff_required)
def medicine_edit(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    if request.method == "POST":
        for field in ("name", "category", "description", "price", "discount_percent", "stock", "image_url"):
            setattr(medicine, field, request.POST.get(field, getattr(medicine, field)))
        medicine.featured = request.POST.get("featured") == "on"
        if request.FILES.get("image"):
            medicine.image = request.FILES["image"]
        medicine.save()
        messages.success(request, "Medicine details updated.")
        return redirect("medicine_management")
    return render(request, "store/manage_medicine_form.html", {"medicine": medicine})


@user_passes_test(staff_required)
def medicine_delete(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    if request.method == "POST":
        medicine.delete()
        messages.success(request, "Medicine removed from the catalogue.")
    return redirect("medicine_management")


@user_passes_test(staff_required)
def doctor_management(request):
    doctors = Doctor.objects.prefetch_related("slots").all()
    if request.method == "POST":
        doctor = Doctor.objects.create(
            name=request.POST["name"], specialty=request.POST["specialty"], qualification=request.POST.get("qualification", ""),
            bio=request.POST.get("bio", ""), experience_years=request.POST.get("experience_years", 1), consultation_fee=request.POST["consultation_fee"],
        )
        messages.success(request, f"Dr. {doctor.name} added to the care team.")
        return redirect("doctor_management")
    return render(request, "store/manage_doctors.html", {"doctors": doctors})


@user_passes_test(staff_required)
def doctor_edit(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    if request.method == "POST":
        for field in ("name", "specialty", "qualification", "bio", "experience_years", "consultation_fee"):
            setattr(doctor, field, request.POST.get(field, getattr(doctor, field)))
        doctor.available = request.POST.get("available") == "on"
        doctor.save()
        messages.success(request, "Doctor profile updated.")
        return redirect("doctor_management")
    return render(request, "store/manage_doctor_form.html", {"doctor": doctor})


@user_passes_test(staff_required)
def doctor_toggle(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    if request.method == "POST":
        doctor.available = not doctor.available
        doctor.save(update_fields=["available"])
        messages.success(request, f"Dr. {doctor.name} is now {'available' if doctor.available else 'deactivated'}.")
    return redirect("doctor_management")


@user_passes_test(staff_required)
def slot_create(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    if request.method == "POST":
        DoctorSlot.objects.create(doctor=doctor, weekday=request.POST["weekday"], start_time=request.POST["start_time"], end_time=request.POST["end_time"])
        messages.success(request, "Availability slot added.")
    return redirect("doctor_management")


@user_passes_test(staff_required)
def slot_delete(request, slot_id):
    slot = get_object_or_404(DoctorSlot, pk=slot_id)
    doctor_id = slot.doctor_id
    if request.method == "POST":
        slot.delete()
        messages.success(request, "Availability slot removed.")
    return redirect("doctor_management")


@user_passes_test(staff_required)
def appointment_management(request):
    status = request.GET.get("status", "")
    appointments = Appointment.objects.select_related("customer", "doctor").all()
    if status:
        appointments = appointments.filter(status=status)
    if request.method == "POST":
        appointment = get_object_or_404(Appointment, pk=request.POST["appointment_id"])
        action = request.POST["action"]
        if action == "reschedule":
            appointment.appointment_date = request.POST["appointment_date"]
            appointment.appointment_time = request.POST["appointment_time"]
            appointment.status = "confirmed"
        else:
            appointment.status = action
        appointment.save()
        messages.success(request, f"Appointment {appointment.get_status_display().lower()}.")
        return redirect("appointment_management")
    return render(request, "store/manage_appointments.html", {"appointments": appointments, "status": status, "status_choices": Appointment.STATUS_CHOICES})


@user_passes_test(staff_required)
def customer_management(request):
    query = request.GET.get("q", "").strip()
    customers = User.objects.filter(is_staff=False).order_by("username")
    if query:
        customers = customers.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
    return render(request, "store/manage_customers.html", {"customers": customers, "query": query})


@user_passes_test(staff_required)
def customer_toggle(request, customer_id):
    customer = get_object_or_404(User, pk=customer_id, is_staff=False)
    if request.method == "POST":
        customer.is_active = not customer.is_active
        customer.save(update_fields=["is_active"])
        messages.success(request, f"{customer.username} is now {'active' if customer.is_active else 'deactivated'}.")
    return redirect("customer_management")


@user_passes_test(staff_required)
def customer_detail(request, customer_id):
    customer = get_object_or_404(User, pk=customer_id, is_staff=False)
    return render(request, "store/customer_detail.html", {"customer": customer, "orders": customer.orders.all(), "appointments": customer.appointments.select_related("doctor").all()})


@user_passes_test(staff_required)
def coupon_management(request):
    coupons = Coupon.objects.all()
    if request.method == "POST":
        coupon = Coupon(
            code=request.POST["code"].strip().upper(), discount_type=request.POST["discount_type"], discount_value=request.POST["discount_value"],
            valid_from=request.POST["valid_from"], valid_until=request.POST["valid_until"], min_order_amount=request.POST.get("min_order_amount", 0),
            enabled=request.POST.get("enabled") == "on", usage_limit=request.POST.get("usage_limit") or None,
        )
        try:
            coupon.full_clean()
            coupon.save()
            messages.success(request, "Coupon created.")
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        return redirect("coupon_management")
    return render(request, "store/manage_coupons.html", {"coupons": coupons})


@user_passes_test(staff_required)
def coupon_toggle(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == "POST":
        coupon.enabled = not coupon.enabled
        coupon.save(update_fields=["enabled"])
        messages.success(request, f"Coupon {coupon.code} is now {'enabled' if coupon.enabled else 'disabled'}.")
    return redirect("coupon_management")


@login_required
def validate_coupon(request):
    code = request.GET.get("code", "").strip().upper()
    try:
        subtotal = Decimal(request.GET.get("subtotal", "0"))
    except InvalidOperation:
        subtotal = Decimal("0")
    coupon = Coupon.objects.filter(code=code).first()
    if not coupon or not coupon.is_valid_for(subtotal):
        return render(request, "store/coupon_result.html", {"valid": False, "message": "This coupon is invalid, expired, disabled, or below its minimum order amount."})
    return render(request, "store/coupon_result.html", {"valid": True, "coupon": coupon, "discount": coupon.calculate_discount(subtotal)})


@user_passes_test(staff_required)
def website_management(request):
    if request.method == "POST":
        kind = request.POST["kind"]
        if kind == "content":
            SiteContent.objects.update_or_create(key=request.POST["key"], defaults={"title": request.POST.get("title", ""), "body": request.POST.get("body", ""), "published": request.POST.get("published") == "on"})
        elif kind == "faq":
            FAQ.objects.create(question=request.POST["question"], answer=request.POST["answer"], published=request.POST.get("published") == "on", sort_order=request.POST.get("sort_order", 0))
        elif kind == "banner":
            Banner.objects.create(title=request.POST["banner_title"], subtitle=request.POST.get("subtitle", ""), image=request.FILES.get("image"), link_url=request.POST.get("link_url", ""), featured=request.POST.get("featured") == "on", published=request.POST.get("published") == "on", sort_order=request.POST.get("sort_order", 0))
        messages.success(request, "Website content saved.")
        return redirect("website_management")
    return render(request, "store/manage_website.html", {"banners": Banner.objects.all(), "content": SiteContent.objects.all(), "faqs": FAQ.objects.all()})


def content_page(request, key):
    content = get_object_or_404(SiteContent, key=key, published=True)
    return render(request, "store/content_page.html", {"content": content})


def faq_page(request):
    return render(request, "store/faq.html", {"faqs": FAQ.objects.filter(published=True)})


@login_required
def upload_prescription(request):
    if request.method == "POST":
        uploaded = request.FILES.get("file")
        allowed = {"application/pdf", "image/jpeg", "image/png"}
        if not uploaded or uploaded.content_type not in allowed or uploaded.size > 5 * 1024 * 1024:
            messages.error(request, "Upload a PDF, JPG, or PNG prescription up to 5 MB.")
        else:
            Prescription.objects.create(customer=request.user, file=uploaded, original_name=uploaded.name, notes=request.POST.get("notes", ""))
            messages.success(request, "Prescription uploaded securely for review.")
        return redirect("upload_prescription")
    return render(request, "store/prescriptions.html", {"prescriptions": request.user.prescriptions.all()})


@login_required
def download_prescription(request, prescription_id):
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    if prescription.customer_id != request.user.id and not request.user.is_staff:
        raise Http404
    if not prescription.file:
        raise Http404
    return FileResponse(prescription.file.open("rb"), as_attachment=True, filename=prescription.original_name)


@login_required
def payment_checkout(request, order_id):
    order = get_object_or_404(Order, pk=order_id, customer=request.user)
    payment, created = Payment.objects.get_or_create(order=order, defaults={"amount": order.total_amount, "provider": "sandbox"})
    if request.method == "POST":
        payment.status = "authorized"
        payment.provider_payment_id = f"sandbox_{payment.pk}"
        payment.save(update_fields=["status", "provider_payment_id"])
        messages.success(request, "Sandbox payment authorized. No card details were stored.")
        return redirect("appointment_list")
    return render(request, "store/payment_checkout.html", {"order": order, "payment": payment})


@user_passes_test(staff_required)
def reports(request):
    today = timezone.localdate()
    period = request.GET.get("period", "monthly")
    period_ranges = {
        "daily": (today, today),
        "weekly": (today - timedelta(days=today.weekday()), today),
        "monthly": (today.replace(day=1), today),
        "yearly": (today.replace(month=1, day=1), today),
    }
    start_date, end_date = period_ranges.get(period, period_ranges["monthly"])
    sales_orders = Order.objects.filter(placed_at__date__range=(start_date, end_date)).exclude(status="cancelled")
    sales_total = sales_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
    sales_by_day = sales_orders.values("placed_at__date").annotate(total=Sum("total_amount"), orders=Count("id")).order_by("placed_at__date")
    product_totals = defaultdict(lambda: {"quantity": 0, "revenue": Decimal("0")})
    for item in OrderItem.objects.filter(order__in=sales_orders).select_related("medicine"):
        product_totals[item.medicine.name]["quantity"] += item.quantity
        product_totals[item.medicine.name]["revenue"] += item.unit_price * item.quantity
    product_sales = sorted(({"medicine__name": name, **totals} for name, totals in product_totals.items()), key=lambda item: item["quantity"], reverse=True)
    low_stock = Medicine.objects.filter(stock__gt=0, stock__lte=10).order_by("stock", "name")
    out_of_stock = Medicine.objects.filter(stock=0).order_by("name")
    registered_customers = User.objects.filter(is_staff=False).order_by("-date_joined")
    active_customers = registered_customers.filter(is_active=True)
    appointments = Appointment.objects.select_related("doctor", "customer").all()
    appointment_by_doctor = appointments.values("doctor__name").annotate(total=Count("id"), completed=Count("id", filter=Q(status="completed")), cancelled=Count("id", filter=Q(status="cancelled"))).order_by("doctor__name")
    appointment_by_date = appointments.values("appointment_date").annotate(total=Count("id"), completed=Count("id", filter=Q(status="completed")), cancelled=Count("id", filter=Q(status="cancelled"))).order_by("-appointment_date")
    context = {
        "period": period, "start_date": start_date, "end_date": end_date, "sales_total": sales_total,
        "sales_order_count": sales_orders.count(), "sales_by_day": sales_by_day, "product_sales": product_sales,
        "low_stock": low_stock, "out_of_stock": out_of_stock, "registered_customers": registered_customers[:12],
        "registered_count": registered_customers.count(), "active_customers": active_customers[:12], "active_count": active_customers.count(),
        "appointment_count": appointments.count(), "completed_appointments": appointments.filter(status="completed").count(),
        "cancelled_appointments": appointments.filter(status="cancelled").count(), "appointment_by_doctor": appointment_by_doctor,
        "appointment_by_date": appointment_by_date[:12],
    }
    if request.GET.get("export") == "sales":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="sales-{period}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Date", "Orders", "Revenue"])
        writer.writerows((row["placed_at__date"], row["orders"], row["total"]) for row in sales_by_day)
        return response
    return render(request, "store/reports.html", context)


@login_required
def notification_list(request):
    channel = request.GET.get("channel", "")
    event_group = request.GET.get("group", "")
    notifications = request.user.notifications.all()
    if channel:
        notifications = notifications.filter(channel=channel)
    if event_group == "orders":
        notifications = notifications.filter(event__startswith="order_")
    elif event_group == "appointments":
        notifications = notifications.filter(event__startswith="appointment_")
    request.user.notifications.filter(read=False).update(read=True)
    preferences, _ = NotificationPreference.objects.get_or_create(user=request.user)
    return render(request, "store/notifications.html", {"notifications": notifications, "preferences": preferences, "channel": channel, "event_group": event_group})


@login_required
def notification_preferences(request):
    preferences, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        preferences.site_enabled = request.POST.get("site_enabled") == "on"
        preferences.email_enabled = request.POST.get("email_enabled") == "on"
        preferences.sms_enabled = request.POST.get("sms_enabled") == "on"
        preferences.phone_number = request.POST.get("phone_number", "").strip()
        preferences.save()
        messages.success(request, "Notification preferences saved.")
    return redirect("notification_list")


@user_passes_test(staff_required)
def review_management(request):
    status = request.GET.get("status", "pending")
    reviews = Review.objects.select_related("medicine", "customer").all()
    if status == "pending":
        reviews = reviews.filter(approved=False)
    elif status == "approved":
        reviews = reviews.filter(approved=True)
    if request.method == "POST":
        review = get_object_or_404(Review, pk=request.POST["review_id"])
        action = request.POST["action"]
        review.approved = action == "approve"
        review.moderated_at = now()
        review.save(update_fields=["approved", "moderated_at"])
        messages.success(request, "Review approved." if review.approved else "Review rejected.")
        return redirect("review_management")
    return render(request, "store/manage_reviews.html", {"reviews": reviews, "status": status})
