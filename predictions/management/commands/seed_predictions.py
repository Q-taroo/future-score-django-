from django.core.management import call_command
from django.core.management.base import BaseCommand

from predictions.models import Prediction


class Command(BaseCommand):
    help = "Seed demo predictions only when the database has none."

    def handle(self, *args, **options):
        if Prediction.objects.exists():
            self.stdout.write("seed_predictions skipped: predictions already exist")
            return
        call_command("seed_data")
        self.stdout.write(self.style.SUCCESS("seed_predictions OK"))
