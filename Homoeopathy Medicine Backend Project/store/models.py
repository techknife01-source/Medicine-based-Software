from decimal import Decimal

from django.contrib.auth.models import User
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
private_prescription_storage = FileSystemStorage(location=settings.BASE_DIR / "private_prescriptions")



class Doctor(models.Model):
    name = models.CharField(max_length=120)
    specialty = models.CharField(max_length=120)
    qualification = models.CharField(max_length=180, blank=True)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=1)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"Dr. {self.name}"


class DoctorSlot(models.Model):
    WEEKDAY_CHOICES = [(str(index), day) for index, day in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="slots")
    weekday = models.CharField(max_length=1, choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]

    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()}"


class Medicine(models.Model):
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False)
    image = models.ImageField(upload_to="medicines/", blank=True, null=True)
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-featured", "name"]

    def __str__(self):
        return self.name

    @property
    def sale_price(self):
        return self.price * (1 - self.discount_percent / 100)

    @property
    def average_rating(self):
        result = self.reviews.filter(approved=True).aggregate(models.Avg("rating"))
        return result["rating__avg"] or 0


class Order(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("confirmed", "Confirmed"), ("shipped", "Shipped"), ("delivered", "Delivered"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    shipping_address = models.TextField()
    placed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self):
        return f"Order #{self.pk}"


class Coupon(models.Model):
    DISCOUNT_TYPES = [("percent", "Percentage"), ("fixed", "Fixed amount")]
    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES, default="percent")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    enabled = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.valid_until <= self.valid_from:
            raise ValidationError("Coupon end time must be after the start time.")
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValidationError("Percentage discounts cannot exceed 100%.")

    def is_valid_for(self, subtotal, at=None):
        from django.utils import timezone
        at = at or timezone.now()
        subtotal = Decimal(str(subtotal))
        return self.enabled and self.valid_from <= at <= self.valid_until and subtotal >= self.min_order_amount and (self.usage_limit is None or self.used_count < self.usage_limit)

    def calculate_discount(self, subtotal):
        subtotal = Decimal(str(subtotal))
        if self.discount_type == "percent":
            return min(subtotal, subtotal * self.discount_value / 100)
        return min(subtotal, self.discount_value)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)


class Payment(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("authorized", "Authorized"), ("paid", "Paid"), ("failed", "Failed"), ("refunded", "Refunded")]
    PROVIDERS = [("sandbox", "Sandbox"), ("stripe", "Stripe"), ("razorpay", "Razorpay")]
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    provider = models.CharField(max_length=20, choices=PROVIDERS, default="sandbox")
    provider_payment_id = models.CharField(max_length=180, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for order #{self.order_id}"


class Prescription(models.Model):
    STATUS_CHOICES = [("pending", "Pending review"), ("approved", "Approved"), ("rejected", "Rejected")]
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="prescriptions")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, null=True, blank=True, related_name="prescriptions")
    file = models.FileField(storage=private_prescription_storage, upload_to="")
    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Prescription #{self.pk} - {self.customer.username}"


class Banner(models.Model):
    title = models.CharField(max_length=160)
    subtitle = models.CharField(max_length=240, blank=True)
    image = models.ImageField(upload_to="banners/", blank=True, null=True)
    link_url = models.URLField(blank=True)
    featured = models.BooleanField(default=False)
    published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-id"]

    def __str__(self):
        return self.title


class SiteContent(models.Model):
    key = models.CharField(max_length=40, unique=True)
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField(blank=True)
    published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


class FAQ(models.Model):
    question = models.CharField(max_length=240)
    answer = models.TextField()
    published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.question


class Appointment(models.Model):
    STATUS_CHOICES = [("requested", "Booked"), ("confirmed", "Confirmed"), ("rescheduled", "Rescheduled"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="appointments")
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["appointment_date", "appointment_time"]

    def __str__(self):
        return f"{self.customer.username} with {self.doctor}"


class Review(models.Model):
    RATING_CHOICES = [(value, str(value)) for value in range(1, 6)]
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medicine_reviews")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["medicine", "customer"], name="one_review_per_customer_medicine")]

    def __str__(self):
        return f"{self.rating}/5 for {self.medicine} by {self.customer.username}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")
    site_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"Notification preferences for {self.user.username}"


class Notification(models.Model):
    CHANNEL_CHOICES = [("site", "Site"), ("email", "Email"), ("sms", "SMS")]
    EVENT_CHOICES = [
        ("order_placed", "Order placed"), ("order_confirmed", "Order confirmed"), ("order_shipped", "Order shipped"),
        ("order_delivered", "Order delivered"), ("order_cancelled", "Order cancelled"), ("appointment_booked", "Appointment booked"),
        ("appointment_confirmed", "Appointment confirmed"), ("appointment_rescheduled", "Appointment rescheduled"),
        ("appointment_cancelled", "Appointment cancelled"), ("appointment_reminder", "Appointment reminder"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    event = models.CharField(max_length=40, choices=EVENT_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    title = models.CharField(max_length=180)
    message = models.TextField()
    read = models.BooleanField(default=False)
    delivered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_channel_display()}: {self.title}"
