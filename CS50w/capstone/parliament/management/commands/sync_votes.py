import requests
import time
from django.core.management.base import BaseCommand
from parliament.models import Member, Division, Vote
from datetime import datetime

class Command(BaseCommand):
    help = 'Syncs voting records (divisions) from UK Parliament API'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Number of divisions to fetch')
        parser.add_argument('--member-id', type=int, help='Sync votes for specific member only')

    def handle(self, *args, **options):
        self.start_time = time.time()
        self.processed_count = 0
        self.error_count = 0
        
        limit = options['limit']
        member_id = options.get('member_id')
        
        if member_id:
            try:
                member = Member.objects.get(member_id=member_id)
                self.stdout.write(f'Syncing votes for {member.name} (ID: {member_id})...')
                self.sync_member_votes(member, limit)
            except Member.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Member {member_id} not found in database'))
                self.error_count += 1
        else:
            self.stdout.write(f'Fetching {limit} most recent divisions...\n')
            self.sync_recent_divisions(limit)

        # Final Summary
        total_time = time.time() - self.start_time
        avg_time = total_time / self.processed_count if self.processed_count > 0 else 0

        self.stdout.write(self.style.SUCCESS(f'\n✓ Processing complete!'))
        self.stdout.write(f'  Processed: {self.processed_count}')
        self.stdout.write(f'  Errors: {self.error_count}')
        self.stdout.write(f'  Total time: {total_time:.2f} seconds')
        self.stdout.write(f'  Average: {avg_time:.2f} seconds per item.')

    def sync_recent_divisions(self, limit):
        """Standard sync: Gets a list of recent divisions and their full details"""
        search_url = 'https://commonsvotes-api.parliament.uk/data/divisions.json/search'
        params = {'queryParameters.take': min(limit, 50), 'queryParameters.skip': 0}
        
        try:
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            divisions_list = response.json()
            
            for item in divisions_list:
                # API documentation shows search returns the full model, 
                # but we'll fetch the specific ID detail to ensure we have every Aye/No list.
                div_id = item.get('DivisionId')
                if not div_id: continue
                
                self.process_single_division(div_id)
                time.sleep(0.2) # Avoid hitting API too hard
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Search failed: {e}'))
            self.error_count += 1

    def sync_member_votes(self, member, limit):
        """Uses the 'membervoting' endpoint from your documentation"""
        url = 'https://commonsvotes-api.parliament.uk/data/divisions.json/membervoting'
        params = {
            'queryParameters.memberId': member.member_id,
            'queryParameters.take': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            votes_data = response.json()
            
            for item in votes_data:
                div_data = item.get('PublishedDivision')
                if not div_data: continue
                
                # 1. Save/Update Division
                division = self.save_division_data(div_data)
                self.processed_count += 1
                
                # 2. Save the specific member's vote
                vote_type = 'AYE' if item.get('MemberVotedAye') else 'NO'
                # Note: API model shows separate bools for VotedAye and VotedNo
                
                Vote.objects.update_or_create(
                    member=member,
                    division=division,
                    defaults={'vote_type': vote_type}
                )
                self.stdout.write(f'  Recorded {vote_type} on: {division.title[:50]}...')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Member sync failed: {e}'))
            self.error_count += 1

    def process_single_division(self, division_id):
        """Fetches detail for one division and records all votes"""
        url = f"https://commonsvotes-api.parliament.uk/data/division/{division_id}.json"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            division = self.save_division_data(data)
            self.processed_count += 1
            
            # Record Ayes
            for v in data.get('Ayes', []):
                self.create_vote_record(division, v.get('MemberId'), 'AYE')
            
            # Record Noes
            for v in data.get('Noes', []):
                self.create_vote_record(division, v.get('MemberId'), 'NO')
            
            self.stdout.write(f'Synced Division: {division.title[:60]}...')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error on ID {division_id}: {e}'))
            self.error_count += 1

    def save_division_data(self, data):
        """Helper to create/update Division object from API dict"""
        date_str = data.get('Date')
        vote_date = None
        if date_str:
            try:
                vote_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            except: pass

        division, created = Division.objects.update_or_create(
            division_id=data.get('DivisionId'),
            defaults={
                'title': data.get('Title', 'Unknown')[:500],
                'date': vote_date,
                'aye_count': data.get('AyeCount', 0),
                'no_count': data.get('NoCount', 0),
            }
        )
        return division

    def create_vote_record(self, division, member_id, vote_type):
        """Helper to link a vote to a member if they exist in our DB"""
        if not member_id: return
        try:
            member = Member.objects.get(member_id=member_id)
            Vote.objects.update_or_create(
                member=member,
                division=division,
                defaults={'vote_type': vote_type}
            )
        except Member.DoesNotExist:
            pass # Member not in our DB; skip vote recording