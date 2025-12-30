# Generated migration to remove policy_area field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parliament', '0008_policytag_alter_interest_raw_summary_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='division',
            name='parliament__policy__1e3792_idx',
        ),
        migrations.RemoveField(
            model_name='division',
            name='policy_area',
        ),
    ]
