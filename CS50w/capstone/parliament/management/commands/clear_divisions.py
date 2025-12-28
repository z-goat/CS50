from django.core.management.base import BaseCommand
from django.conf import settings
import shutil
import os
from parliament.models import Division, Vote

class Command(BaseCommand):
    help = 'Safely delete all Division and Vote records (with optional DB backup for sqlite)'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true', help='Confirm deletion without prompt')

    def handle(self, *args, **options):
        yes = options.get('yes', False)
        div_count = Division.objects.count()
        vote_count = Vote.objects.count()

        self.stdout.write(self.style.WARNING('About to delete all Division and Vote data'))
        self.stdout.write(f'  Divisions: {div_count}')
        self.stdout.write(f'  Votes: {vote_count}')

        if not yes:
            confirm = input('Type YES to confirm permanent deletion: ')
            if confirm.strip() != 'YES':
                self.stdout.write(self.style.ERROR('Aborted. No changes made.'))
                return

        # Attempt sqlite backup if applicable
        db_name = settings.DATABASES.get('default', {}).get('NAME')
        if db_name and 'sqlite' in settings.DATABASES.get('default', {}).get('ENGINE', ''):
            try:
                backup_path = f"{db_name}.bak"
                shutil.copy(db_name, backup_path)
                self.stdout.write(self.style.SUCCESS(f'Created sqlite backup: {backup_path}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not create sqlite backup: {e}'))

        # Delete records
        Vote.objects.all().delete()
        Division.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('All divisions and votes deleted.'))
