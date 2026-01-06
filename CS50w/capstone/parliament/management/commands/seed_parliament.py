import requests
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from parliament.models import Member


class Command(BaseCommand):
    help = 'Seeds the database with current MPs from UK Parliament API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of MPs to process in each batch'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        
        self.stdout.write(self.style.WARNING('Starting MP data synchronization...'))
        
        # Step 1: Get all current MPs
        try:
            members = self.fetch_all_members()
            self.stdout.write(self.style.SUCCESS(f'Retrieved {len(members)} MPs from API'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to fetch members: {str(e)}'))
            return
        
        # Step 2: Process in batches
        total_created = 0
        total_updated = 0
        
        for i in range(0, len(members), batch_size):
            batch = members[i:i + batch_size]
            created, updated = self.process_batch(batch)
            total_created += created
            total_updated += updated
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processed batch {i//batch_size + 1}: '
                    f'{created} created, {updated} updated'
                )
            )
            
            # Rate limiting: pause between batches
            if i + batch_size < len(members):
                time.sleep(0.5)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Synchronization complete!\n'
                f'  Created: {total_created} MPs\n'
                f'  Updated: {total_updated} MPs\n'
                f'  Total in database: {Member.objects.count()}'
            )
        )

    def fetch_all_members(self):
        """Fetch all current MPs from Parliament API"""
        base_url = 'https://members-api.parliament.uk/api/Members/Search'
        
        params = {
            'House': 1,  # Commons
            'IsCurrentMember': True,
            'skip': 0,
            'take': 20
        }
        
        all_members = []
        
        while True:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            if not items:
                break
            
            all_members.extend(items)
            
            # Check if there are more results
            total_results = data.get('totalResults', 0)
            if len(all_members) >= total_results:
                break
            
            # Update skip for next page
            params['skip'] += params['take']
            time.sleep(0.3)  # Rate limiting
        
        return all_members

    @transaction.atomic
    def process_batch(self, members):
        """Process a batch of members and save to database"""
        created_count = 0
        updated_count = 0
        
        for member_data in members:
            member_id = member_data['value']['id']
            
            # Fetch detailed member info
            try:
                details = self.fetch_member_details(member_id)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Skipping member {member_id}: {str(e)}')
                )
                continue
            
            # Extract data
            name = member_data['value'].get('nameDisplayAs', 'Unknown')
            party = member_data['value'].get('latestParty', {}).get('name', 'Independent')
            constituency = member_data['value'].get('latestHouseMembership', {}).get(
                'membershipFrom', 'Unknown'
            )
            # Membership start date (try a couple of possible fields)
            start_date_str = None
            latest_mem = member_data['value'].get('latestHouseMembership', {})
            if latest_mem:
                start_date_str = latest_mem.get('membershipStartDate') or latest_mem.get('membershipFrom')
            parliament_start_date = None
            if start_date_str:
                try:
                    # membership fields are typically ISO date strings
                    parliament_start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).date()
                except Exception:
                    try:
                        parliament_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    except Exception:
                        parliament_start_date = None
            
            # Get portrait URL from details
            portrait_url = details.get('value', {}).get('thumbnailUrl', '') if details else ''
            
            # Create or update member
            member, created = Member.objects.update_or_create(
                member_id=member_id,
                defaults={
                    'name': name,
                    'party': party,
                    'constituency': constituency,
                    'portrait_url': portrait_url or '',
                    'current_status': True,
                    'parliament_start_date': parliament_start_date,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return created_count, updated_count

    def fetch_member_details(self, member_id):
        """Fetch detailed information for a specific member"""
        url = f'https://members-api.parliament.uk/api/Members/{member_id}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()