from django.core.management.base import BaseCommand
import csv
from parliament.models import Member

class Command(BaseCommand):
    help = 'Report current MPs missing parliament_start_date (exports CSV)'

    def add_arguments(self, parser):
        parser.add_argument('--out-file', type=str, default='missing_start_dates.csv')

    def handle(self, *args, **options):
        out_file = options.get('out_file')
        qs = Member.objects.filter(current_status=True, parliament_start_date__isnull=True)
        count = qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No current MPs missing parliament_start_date.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {count} current MPs missing start date. Writing to {out_file}'))

        with open(out_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['member_id', 'name', 'party', 'constituency'])
            for m in qs.order_by('name'):
                writer.writerow([m.member_id, m.name, m.party, m.constituency])

        self.stdout.write(self.style.SUCCESS(f'Wrote {count} records to {out_file}'))
