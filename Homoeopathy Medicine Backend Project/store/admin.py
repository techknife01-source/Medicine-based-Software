from django.contrib import admin
from .models import Appointment, Banner, Coupon, Doctor, DoctorSlot, FAQ, Medicine, Notification, NotificationPreference, Order, OrderItem, Payment, Prescription, Review, SiteContent


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "specialty", "qualification", "experience_years", "consultation_fee", "available")
    list_filter = ("available", "specialty")
    search_fields = ("name", "specialty")


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "discount_percent", "stock", "featured")
    list_filter = ("category", "featured")
    search_fields = ("name", "category")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("medicine", "customer", "rating", "approved", "created_at", "moderated_at")
    list_filter = ("approved", "rating", "created_at")
    search_fields = ("medicine__name", "customer__username", "comment")
    readonly_fields = ("created_at", "moderated_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "channel", "title", "delivered", "read", "created_at")
    list_filter = ("event", "channel", "delivered", "read")
    search_fields = ("user__username", "title", "message")
    readonly_fields = ("created_at",)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "site_enabled", "email_enabled", "sms_enabled", "phone_number")
    search_fields = ("user__username", "phone_number")


@admin.register(DoctorSlot)
class DoctorSlotAdmin(admin.ModelAdmin):
    list_display = ("doctor", "weekday", "start_time", "end_time", "active")
    list_filter = ("weekday", "active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "total_amount", "status", "placed_at")
    list_filter = ("status",)
    search_fields = ("customer__username",)
    inlines = [OrderItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "valid_from", "valid_until", "min_order_amount", "enabled", "used_count")
    list_filter = ("enabled", "discount_type")
    search_fields = ("code",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "amount", "status", "provider_payment_id", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("provider_payment_id", "order__customer__username")
    readonly_fields = ("created_at",)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("customer", "order", "original_name", "status", "uploaded_at", "reviewed_at")
    list_filter = ("status", "uploaded_at")
    search_fields = ("customer__username", "original_name")
    readonly_fields = ("original_name", "uploaded_at", "reviewed_at")


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "featured", "published", "sort_order")
    list_filter = ("featured", "published")
    ordering = ("sort_order",)


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "published", "updated_at")
    list_filter = ("published",)
    search_fields = ("key", "title", "body")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "published", "sort_order")
    list_filter = ("published",)
    search_fields = ("question", "answer")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("customer", "doctor", "appointment_date", "appointment_time", "status")
    list_filter = ("status", "appointment_date")
    search_fields = ("customer__username", "doctor__name")


admin.site.site_header = "VerdantCare Admin"
admin.site.site_title = "VerdantCare Administration"
admin.site.index_title = "Shop and appointments control centre"
