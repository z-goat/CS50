import requests
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from parliament.models import Member, Interest
from datetime import datetime


class Command(BaseCommand):
    help = 'Syncs financial interests for all MPs from UK Parliament API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--member-id',
            type=int,
            help='Sync interests for a specific member only'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of MPs to process (for testing)'
        )

    def handle(self, *args, **options):
        member_id = options.get('member_id')
        limit = options.get('limit')
        
        if member_id:
            # Process single member
            try:
                member = Member.objects.get(member_id=member_id)
                self.stdout.write(f'Processing interests for {member.name}...')
                count = self.sync_member_interests(member)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Synced {count} interests for {member.name}'
                ))
            except Member.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Member {member_id} not found'))
        else:
            # Process all members
            members = Member.objects.filter(current_status=True)
            if limit:
                members = members[:limit]
            
            total_members = members.count()
            self.stdout.write(f'Starting sync for {total_members} MPs...\n')
            
            total_interests = 0
            processed = 0
            
            for member in members:
                processed += 1
                try:
                    count = self.sync_member_interests(member)
                    total_interests += count
                    self.stdout.write(
                        f'[{processed}/{total_members}] {member.name}: {count} interests'
                    )
                    time.sleep(0.3)  # Rate limiting
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Error with {member.name}: {str(e)}')
                    )
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Sync complete!\n'
                f'  Processed: {processed} MPs\n'
                f'  Total interests: {total_interests}'
            ))

    def sync_member_interests(self, member):
        """Fetch and store interests for a specific member"""
        url = f'https://members-api.parliament.uk/api/Members/{member.member_id}/RegisteredInterests'
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            interests_data = data.get('value', [])
            created_count = 0
            
            for interest_item in interests_data:
                category = interest_item.get('category', {})
                category_code = str(category.get('id', '7'))
                
                # Get all interest lines
                lines = interest_item.get('interests', [])
                for line in lines:
                    summary = line.get('interest', '')
                    if not summary:
                        continue
                    
                    # Parse date
                    created_date_str = line.get('created')
                    registered_date = None
                    if created_date_str:
                        try:
                            registered_date = datetime.fromisoformat(
                                created_date_str.replace('Z', '+00:00')
                            ).date()
                        except:
                            pass
                    
                    # Create or update interest
                    Interest.objects.update_or_create(
                        member=member,
                        category_code=category_code,
                        summary=summary,
                        defaults={
                            'registered_date': registered_date,
                            'is_current': True
                        }
                    )
                    created_count += 1
            
            return created_count
            
        except Exception as e:
            raise Exception(f'API error: {str(e)}')