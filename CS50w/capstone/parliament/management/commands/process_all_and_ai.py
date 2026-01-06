import time
import os
import json
import hashlib
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from parliament.models import Member, Interest, Division, Vote
from parliament.ai_service import analyze_conflict_with_ai


LOCK_PATH = '/tmp/parliament_ai_process.lock'


def acquire_lock(member_id: int | None) -> bool:
    """Create a simple lock file containing the member_id to avoid concurrent AI runs."""
    if os.path.exists(LOCK_PATH):
        return False
    try:
        with open(LOCK_PATH, 'w') as fh:
            fh.write(str(member_id or 'all'))
        return True
    except Exception:
        return False


def release_lock():
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except Exception:
        pass


def call_with_retries(func, *args, retries=3, backoff=1, **kwargs):
    attempt = 0
    while attempt < retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                raise
            time.sleep(backoff * attempt)


class Command(BaseCommand):
    help = 'Seed data, tag divisions, process interests via AI and compute vote conflicts. Can be limited to one member.'

    def add_arguments(self, parser):
        parser.add_argument('--member_id', type=int, help='Restrict processing to a single member ID')
        parser.add_argument('--skip-seed', action='store_true', help='Skip seeding MPs')
        parser.add_argument('--skip-tags', action='store_true', help='Skip tagging divisions')
        parser.add_argument('--skip-interests', action='store_true', help='Skip interest AI processing')
        parser.add_argument('--dry-run', action='store_true', help='Run without writing results')
        parser.add_argument('--confirm', action='store_true', help='Confirm writes when not dry-run')
        parser.add_argument('--limit-interests', type=int, default=None, help='Limit number of interests processed (when running interest processing)')
        parser.add_argument('--force', action='store_true', help='Force reprocessing even if already processed')

    def handle(self, *args, **options):
        member_id = options.get('member_id')
        skip_seed = options.get('skip_seed')
        skip_tags = options.get('skip_tags')
        skip_interests = options.get('skip_interests')
        dry_run = options.get('dry_run')
        confirm = options.get('confirm')
        limit_interests = options.get('limit_interests')
        force = options.get('force')

        self.stdout.write(self.style.WARNING('Starting full AI processing workflow'))

        if not acquire_lock(member_id):
            owner = None
            try:
                with open(LOCK_PATH, 'r') as fh:
                    owner = fh.read().strip()
            except Exception:
                owner = 'unknown'
            self.stdout.write(self.style.ERROR(f'Another AI job is running (owner={owner}). Aborting.'))
            return

        try:
            # Step 1: seed MPs if requested
            if not skip_seed:
                self.stdout.write('Seeding MPs (seed_parliament)...')
                call_command('seed_parliament')
            
            # Step 1.5: sync interests and votes
            self.stdout.write('Syncing financial interests (sync_interests)...')
            args = []
            if member_id is not None:
                args.extend(['--member-id', str(member_id)])
            call_command('sync_interests', *args)
            
            self.stdout.write('Syncing voting records (sync_votes)...')
            args = []
            if member_id is not None:
                args.extend(['--member-id', str(member_id)])
            call_command('sync_votes', *args)

            # Step 2: tag divisions via AI
            if not skip_tags:
                self.stdout.write('Tagging divisions via AI (tag_divisions_ai)...')
                call_command('tag_divisions_ai')

            # Step 3: process interests via existing command
            if not skip_interests:
                self.stdout.write('Processing interests via AI (process_interests_ai)...')
                args = ['--force']  # Always force to process everything
                if limit_interests is not None:
                    args.extend(['--limit', str(limit_interests)])
                if member_id is not None:
                    args.extend(['--member-id', str(member_id)])

                call_command('process_interests_ai', *args)

            # Step 4: compute vote conflicts and update Vote.conflict_score
            self.stdout.write('Computing vote conflict scores...')

            votes_qs = Vote.objects.all().select_related('member', 'division')
            if member_id is not None:
                votes_qs = votes_qs.filter(member=member_id)

            total_votes = votes_qs.count()
            if total_votes == 0:
                self.stdout.write(self.style.WARNING('No votes found to process'))
            else:
                self.stdout.write(f'Found {total_votes} votes to analyze')

            processed = 0
            errors = 0

            CACHE_TTL = getattr(settings, 'AI_CONFLICT_CACHE_TTL', 60 * 60 * 24 * 7)
            FAILURE_TTL = getattr(settings, 'AI_CONFLICT_FAILURE_TTL', 60 * 5)

            for vote in votes_qs.iterator():
                try:
                    # Build interests relevant to this member
                    interests = list(Interest.objects.filter(member=vote.member, is_current=True))

                    if not interests:
                        self.stdout.write(self.style.WARNING(f'No interests for member {vote.member.member_id}; skipping vote {vote.division.id}'))
                        continue

                    interests_data = [
                        {
                            'summary': i.summary or i.raw_summary,
                            'sector': i.ai_sector or i.interest_type or 'Other',
                            'payer': i.ai_payer or 'Unknown',
                            'value': float(i.ai_value) if i.ai_value else None,
                        }
                        for i in interests
                    ]

                    # Build cache key based on member/division and interests meta
                    interest_meta = []
                    for i in interests:
                        ts = i.last_ai_processed.isoformat() if i.last_ai_processed else 'none'
                        interest_meta.append(f"{i.id}:{ts}")

                    interest_key = '|'.join(sorted(interest_meta))
                    key_raw = f"ai_conflict:{vote.member.member_id}:{vote.division.id}:{interest_key}"
                    cache_key = hashlib.sha1(key_raw.encode('utf-8')).hexdigest()

                    cached = cache.get(cache_key)
                    if cached is not None:
                        analysis = cached
                    else:
                        # Call AI with retries
                        analysis = call_with_retries(
                            analyze_conflict_with_ai,
                            vote.member.name,
                            interests_data,
                            vote.division.title,
                            vote.division.description or '',
                            retries=3,
                            backoff=2
                        )

                        try:
                            confidence = float(analysis.get('confidence', 0.0))
                        except Exception:
                            confidence = 0.0

                        ttl = CACHE_TTL if confidence >= 0.1 else FAILURE_TTL
                        cache.set(cache_key, analysis, ttl)

                    conflict_score = float(analysis.get('conflict_score', 0.0))

                    if dry_run:
                        self.stdout.write(f'[DRY] Member {vote.member.member_id} vote {vote.division.id} => score {conflict_score:.3f} (confidence {analysis.get("confidence")})')
                    else:
                        # Save score
                        vote.conflict_score = conflict_score
                        vote.save(update_fields=['conflict_score'])
                        self.stdout.write(self.style.SUCCESS(f'Updated vote {vote.division.id} conflict={conflict_score:.3f} (member {vote.member.member_id})'))

                    processed += 1
                    time.sleep(0.25)

                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.WARNING(f'Error analyzing vote {getattr(vote.division, "id", "?")}: {str(e)}'))

            self.stdout.write(self.style.SUCCESS(f'AI processing finished: processed={processed} errors={errors}'))

        finally:
            release_lock()
