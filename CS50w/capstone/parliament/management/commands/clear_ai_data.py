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
        
        parser.add_argument(
            '--member_id',
            type=int,
            help='Clear AI data for interests of a specific member only'
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
        
        # Apply filtering if member_id is specified
        interests = Interest.objects.all()
        if options['member_id']:
            interests = interests.filter(member=options['member_id'])

        count = interests.count()
        interests.update(
            ai_sector=None,
            ai_confidence=0.0,
            ai_payer=None,
            ai_value=None,
            is_current=True,
            last_ai_processed=None
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'✓ Cleared AI data from {count} interests'
        ))