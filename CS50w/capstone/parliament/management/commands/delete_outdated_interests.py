from django.utils import timezone
from models import Interest
from django_q.tasks import async_task

def delete_outdated_interests():
    """
    Deletes interests where the expiration date is in the past.
    """
    now = timezone.now()
    
    # Filter for items that are not current AND their expiration date is past due
    outdated_interests = Interest.objects.filter(
        is_current=False,
        expiration_date__lte=now
    )
    
    count = outdated_interests.count()
    if count > 0:
        outdated_interests.delete()
        print(f"Deleted {count} outdated interests.")
    
    return f"Deletion task completed. {count} items removed."
