from django.core.management.base import BaseCommand
from parliament.models import Interest

class Command(BaseCommand):
    help = 'Clear all AI-processed data from interests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of AI data'
        )

    def handle(self, *args, **options):
        total = Interest.objects.count()
        processed = Interest.objects.filter(last_ai_processed__isnull=False).count()
        
        self.stdout.write(f'Found {processed} processed interests out of {total} total')
        
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                'Run with --confirm to clear AI data'
            ))
            return
        
        # Clear AI data
        Interest.objects.all().update(
            ai_sector=None,
            ai_confidence=0.0,
            ai_payer=None,
            ai_value=None,
            is_current=True,
            last_ai_processed=None
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'✓ Cleared AI data from {total} interests'
        ))