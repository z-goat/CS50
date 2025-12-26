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
            default=3238,
            help='Number of interests to process (default: 3238)'
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
        
        # Get interests that need processing, ordered by ID to ensure consistent processing order
        if force:
            interests = Interest.objects.order_by("id")[:limit]
        else:
            interests = Interest.objects.filter(
                last_ai_processed__isnull=True
            ).order_by("id")[:limit]

        
        interests_list = list(interests)
        total = len(interests_list)
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ No interests need processing'))
            return
        
        self.stdout.write(f'Processing {total} interest(s) through Gemini AI...\n\n')
        
        processed = 0
        errors = 0
        
        for interest in interests_list:
            try:
                extracted = extract_interest_data(interest.summary)
                
                
                required_fields = {"sector", "confidence", "payer", "value", "is_current"}
                if not extracted or not required_fields.issubset(extracted):
                    raise ValueError(f"Incomplete AI response: {extracted}")


                interest.ai_sector = extracted.get('sector')
                interest.ai_confidence = extracted.get('confidence')
                interest.ai_payer = extracted.get('payer')
                interest.ai_value = extracted.get('value')
                interest.is_current = extracted.get('is_current')
                interest.last_ai_processed = timezone.now()
                
                interest.save()
                processed += 1
                
                time.sleep(2.5)
                self.stdout.write(f'Finished processing an interest of {interest.member.name}')

                
            except Exception as e:
                errors += 1
                self.stdout.write(self.style.WARNING(f'Error on {interest.id}: {e}'))
                time.sleep(2.5)
                
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Processing complete!'))
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  Errors: {errors}')
        
        if processed > 0:
            self.stdout.write(f"  Total time: {elapsed:.2f} seconds")
            self.stdout.write(f"  Average: {elapsed/processed:.2f} seconds per item.")