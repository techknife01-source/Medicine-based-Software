from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create least-privilege staff groups for RBAC."

    def handle(self, *args, **options):
        roles = {
            "Content Manager": ["add_banner", "change_banner", "delete_banner", "add_faq", "change_faq", "delete_faq", "add_sitecontent", "change_sitecontent"],
            "Order Manager": ["change_order", "view_order", "change_appointment", "view_appointment"],
            "Care Manager": ["change_doctor", "view_doctor", "change_doctorslot", "view_doctorslot", "change_prescription", "view_prescription"],
        }
        for name, codenames in roles.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(Permission.objects.filter(codename__in=codenames, content_type__app_label="store"))
        self.stdout.write(self.style.SUCCESS("RBAC groups ready: Content Manager, Order Manager, Care Manager."))
