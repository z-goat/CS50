import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from parliament.models import Interest
from parliament.ai_service import extract_interest_data

class Command(BaseCommand):
    help = 'Process interests through Gemini AI for categorization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Number of interests to process (default: 50)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocess interests even if already processed'
        )

    def handle(self, *args, **options):
        # Start timer here
        start_time = time.perf_counter()
        
        limit = options['limit']
        force = options['force']
        
        # Get interests that need processing
        if force:
            interests = Interest.objects.all()[:limit]
        else:
            interests = Interest.objects.filter(
                last_ai_processed__isnull=True
            )[:limit]
        
        interests_list = list(interests)
        total = len(interests_list)
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ No interests need processing'))
            return
        
        self.stdout.write(f'Processing {total} interests through Gemini AI...\n')
        
        processed = 0
        errors = 0
        
        for interest in interests:
            try:
                extracted = extract_interest_data(interest.summary)
                
                
                if not extracted or 'sector' not in extracted:
                    raise ValueError("AI failed to return valid data")

                interest.ai_sector = extracted.get('sector')
                
                interest.save()
                processed += 1
                
                time.sleep(3.5)
                
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.WARNING(f'Error on {interest.id}: {e}'))
                time.sleep(3.5)
                
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Processing complete!'))
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Errors: {errors}')
        
        if processed > 0:
            self.stdout.write(f"  Total time: {elapsed:.2f} seconds")
            self.stdout.write(f"  Average: {elapsed/processed:.2f} seconds per item.")