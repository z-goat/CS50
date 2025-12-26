import requests
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from parliament.models import Member, Interest


class Command(BaseCommand):
    help = 'Seeds the database with current MPs from UK Parliament API'

    def handle(self, *args, **options):
        total = Interest.objects.count()
        processed = Interest.objects.filter(last_ai_processed__isnull=False).count()
        self.stdout.write(
            self.style.SUCCESS(f'✓ Processed {processed} out of {total} interests ({(processed/total)*100:.2f}%)'))
        