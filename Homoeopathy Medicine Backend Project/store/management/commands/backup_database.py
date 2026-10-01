from pathlib import Path
from datetime import datetime

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Create a timestamped JSON backup of application data."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="backups")

    def handle(self, *args, **options):
        folder = Path(options["output"])
        folder.mkdir(parents=True, exist_ok=True)
        filename = folder / f"verdantcare-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with filename.open("w", encoding="utf-8") as destination:
            call_command("dumpdata", "store", "auth.User", indent=2, stdout=destination)
        self.stdout.write(self.style.SUCCESS(f"Backup created at {filename}"))
