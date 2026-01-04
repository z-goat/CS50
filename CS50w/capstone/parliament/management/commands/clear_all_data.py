from django.core.management.base import BaseCommand
from django.db import transaction
from parliament.models import Member, Interest, Division, Vote, PolicyTag, AnalyticsTrend


class Command(BaseCommand):
    help = 'Clear specified models or all data from the parliament app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm', action='store_true', help='Required to actually perform deletions'
        )
        parser.add_argument(
            '--models', type=str, default='all',
            help='Comma-separated list of models to clear: members,interests,divisions,votes,tags,analytics or "all"'
        )
        parser.add_argument(
            '--member_id', type=int, help='If provided, only clear data for this member'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        models_arg = options['models'] or 'all'
        confirm = options['confirm']
        member_id = options.get('member_id')

        available = {
            'members': Member,
            'interests': Interest,
            'divisions': Division,
            'votes': Vote,
            'tags': PolicyTag,
            'analytics': AnalyticsTrend,
        }

        if models_arg.strip().lower() == 'all':
            target_keys = list(available.keys())
        else:
            target_keys = [k.strip().lower() for k in models_arg.split(',') if k.strip()]

        invalid = [k for k in target_keys if k not in available]
        if invalid:
            self.stdout.write(self.style.ERROR(f'Invalid model names: {invalid}'))
            return

        # Summary
        self.stdout.write('Clear data plan:')
        for k in target_keys:
            self.stdout.write(f' - {k}')

        if not confirm:
            self.stdout.write(self.style.WARNING('Run with --confirm to execute deletions'))
            return

        # Perform deletions
        for k in target_keys:
            model = available[k]
            qs = model.objects.all()
            if member_id and hasattr(model, 'member'):
                qs = qs.filter(member_id=member_id)

            count = qs.count()
            if count == 0:
                self.stdout.write(self.style.WARNING(f'No records to delete for {k}'))
                continue

            self.stdout.write(f'Deleting {count} records from {k}...')
            qs.delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted {count} records from {k}'))

        self.stdout.write(self.style.SUCCESS('All requested deletions completed'))
