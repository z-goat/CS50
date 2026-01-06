from django.core.management.base import BaseCommand
from parliament.models import Division
from parliament.ai_service import extract_division_tags

class Command(BaseCommand):
    help = "AI tag divisions with policy sectors"

    def handle(self, *args, **kwargs):
        divisions = Division.objects.all()
        for div in divisions:
            result = extract_division_tags(div.title, div.description or "")
            
            # Save AI sectors directly into ArrayField
            div.policy_tags = result["sectors"]
            div.policy_confidence = result.get("confidence", 0.0)
            div.save()
            
            self.stdout.write(f"Division {div.id} tagged: {result['sectors']}")
