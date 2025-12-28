import requests
import time
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from parliament.models import Member, Division, Vote


class Command(BaseCommand):
    help = 'Syncs voting records (Commons divisions) from UK Parliament API'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1000, help='Max votes per member (safety cap)')
        parser.add_argument('--member-id', type=int, help='Sync votes for a specific member only')
        parser.add_argument('--full-reload', action='store_true', help='Delete all divisions and votes before syncing')
        parser.add_argument('--yes', action='store_true', help='Confirm destructive actions')
        parser.add_argument('--throttle', type=float, default=0.25, help='Seconds to sleep between API calls')
        parser.add_argument('--resume', action='store_true', help='Resume from member.last_synced_at')

    def handle(self, *args, **options):
        self.start_time = time.time()
        self.processed_votes = 0
        self.error_count = 0

        limit = options['limit']
        throttle = options['throttle']
        resume = options['resume']
        member_id = options.get('member_id')

        # Destructive reset
        if options['full_reload']:
            if not options['yes']:
                self.stdout.write(self.style.ERROR('Full reload requires --yes'))
                return
            self.stdout.write(self.style.WARNING('Deleting ALL divisions and votes...'))
            Vote.objects.all().delete()
            Division.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Database cleared.'))

        # Single member
        if member_id:
            try:
                member = Member.objects.get(member_id=member_id)
                self.stdout.write(f'Syncing votes for {member.name}')
                self.sync_member_votes(member, limit, resume, throttle)
                member.last_synced_at = datetime.now(timezone.utc)
                member.save(update_fields=['last_synced_at'])
            except Member.DoesNotExist:
                self.stdout.write(self.style.ERROR('Member not found'))
                return
        else:
            members = Member.objects.filter(current_status=True).order_by('name')
            total = members.count()
            self.stdout.write(f'Starting full Commons sync for {total} MPs')

            for idx, member in enumerate(members, start=1):
                if not member.parliament_start_date:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping {member.name} (missing start date)')
                    )
                    self.error_count += 1
                    continue

                self.stdout.write(f'[{idx}/{total}] {member.name}')
                try:
                    self.sync_member_votes(member, limit, resume, throttle)
                    member.last_synced_at = datetime.now(timezone.utc)
                    member.save(update_fields=['last_synced_at'])
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error: {e}'))
                    self.error_count += 1

        # Summary
        elapsed = time.time() - self.start_time
        avg = elapsed / self.processed_votes if self.processed_votes else 0

        self.stdout.write(self.style.SUCCESS('\n✓ Sync complete'))
        self.stdout.write(f'  Votes saved: {self.processed_votes}')
        self.stdout.write(f'  Errors: {self.error_count}')
        self.stdout.write(f'  Time: {elapsed:.2f}s')
        self.stdout.write(f'  Avg per vote: {avg:.3f}s')

    # ============================================================
    # Core sync logic
    # ============================================================

    def sync_member_votes(self, member, limit, resume, throttle):
        url = 'https://commonsvotes-api.parliament.uk/data/divisions.json/membervoting'

        page_size = 100
        skip = 0
        saved = 0

        while saved < limit:
            params = {
                'queryParameters.memberId': member.member_id,
                'queryParameters.take': page_size,
                'queryParameters.skip': skip
            }

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            results = response.json()

            if not results:
                break

            for item in results:
                div = item.get('PublishedDivision')
                if not div:
                    continue

                vote_date = self.parse_date(div.get('Date'))

                # Resume support
                if resume and member.last_synced_at and vote_date:
                    if vote_date <= member.last_synced_at.date():
                        continue

                # Parliament start date guard
                if vote_date and vote_date < member.parliament_start_date:
                    continue

                division = self.save_division(div)

                # Vote type
                if item.get('MemberVotedAye'):
                    vote_type = 'AYE'
                elif item.get('MemberVotedNo'):
                    vote_type = 'NO'
                else:
                    vote_type = 'DID_NOT_VOTE'

                Vote.objects.update_or_create(
                    member=member,
                    division=division,
                    defaults={'vote_type': vote_type}
                )

                saved += 1
                self.processed_votes += 1

                if saved >= limit:
                    break

            skip += page_size
            time.sleep(throttle)

        self.stdout.write(f'  → {saved} votes saved')

    # ============================================================
    # Helpers
    # ============================================================

    def save_division(self, data):
        vote_date = self.parse_date(data.get('Date'))

        division, _ = Division.objects.update_or_create(
            division_id=data.get('DivisionId'),
            defaults={
                'title': (data.get('Title') or 'Unknown')[:500],
                'date': vote_date,
                'aye_count': data.get('AyeCount', 0),
                'no_count': data.get('NoCount', 0),
            }
        )
        return division

    def parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except Exception:
            return None
