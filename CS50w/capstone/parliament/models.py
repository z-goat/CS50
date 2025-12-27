from datetime import timedelta
from django.db import models
from django.utils import timezone


class Member(models.Model):
    """Represents a Member of Parliament"""
    member_id = models.IntegerField(unique=True, primary_key=True)
    name = models.CharField(max_length=200)
    party = models.CharField(max_length=100)
    constituency = models.CharField(max_length=200)
    portrait_url = models.URLField(blank=True, null=True)
    current_status = models.BooleanField(default=True)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['constituency']),
            models.Index(fields=['party']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.constituency}"


class Interest(models.Model):
    """Represents a declared financial interest"""
    
    INTEREST_TYPE_CHOICES = [
    ("shareholding", "Shareholding"),
    ("consultancy", "Paid Employment / Consultancy"),
    ("speech", "Paid Speech / Appearance"),
    ("gift", "Gifts / Hospitality / Travel"),
    ("trusteeship", "Unpaid Directorship / Trusteeship"),
    ("donation", "Donation / Grant / Sponsorship"),
    ("property", "Land / Property / Real Estate"),
    ("other", "Other / Miscellaneous"),
]

    interest_type = models.CharField(
    max_length=30,
    choices=INTEREST_TYPE_CHOICES,
    default="other",
)

    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='interests')
    raw_summary = models.TextField()
    registered_date = models.DateField(null=True, blank=True)
    
    # AI-extracted fields (populated in Phase 2)
    ai_sector = models.CharField(max_length=100, blank=True, null=True)
    ai_confidence = models.FloatField(default=0.0)
    ai_payer = models.CharField(max_length=200, blank=True, null=True)
    ai_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_current = models.BooleanField(default=True)
    summary = models.CharField(max_length=300, blank=True, null=True)

    # Add an expiration date field so that non-current interests can be tracked and deleted after a year
    expiration_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Update expiration date logic when is_current changes
        if not self.is_current and self.expiration_date is None:
            # Set the expiration for 1 year from the current time
            self.expiration_date = timezone.now() + timedelta(days=365)
        elif self.is_current and self.expiration_date is not None:
            # Clear the expiration date if the item becomes current again
            self.expiration_date = None
        super().save(*args, **kwargs)

    
    # Metadata
    last_ai_processed = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-registered_date']
        indexes = [
            models.Index(fields=['member']),
            models.Index(fields=['ai_sector']),
        ]
    
    def get_weight(self):
        weights = {
            "shareholding": 4,
            "consultancy": 3,
            "speech": 2,
            "gift": 2,
            "trusteeship": 1,
            "donation": 1,
            "property": 1,
            "other": 0.5,
        }
        return weights.get(self.interest_type, 0.5)
    
    def __str__(self):
        return f"{self.member.name} - {self.interest_type}"


class Division(models.Model):
    """Represents a parliamentary vote/division"""
    division_id = models.IntegerField(unique=True, primary_key=True)
    title = models.CharField(max_length=500)
    date = models.DateField()
    policy_area = models.CharField(max_length=100, blank=True, null=True)
    
    aye_count = models.IntegerField(default=0)
    no_count = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['policy_area']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.date})"


class Vote(models.Model):
    """Represents an individual MP's vote on a division"""
    
    VOTE_CHOICES = [
        ('AYE', 'Aye'),
        ('NO', 'No'),
        ('ABSTAIN', 'Abstain'),
        ('ABSENT', 'Absent'),
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='votes')
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='votes')
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    
    # Conflict scoring (calculated in Phase 3)
    conflict_score = models.FloatField(default=0.0)
    
    class Meta:
        unique_together = ['member', 'division']
        indexes = [
            models.Index(fields=['member', 'division']),
            models.Index(fields=['conflict_score']),
        ]
    
    def __str__(self):
        return f"{self.member.name} - {self.division.title[:50]} ({self.vote_type})"


class AnalyticsTrend(models.Model):
    """Pre-calculated analytics for parliament-wide trends"""
    trend_type = models.CharField(max_length=50)  # e.g., 'sector_breakdown', 'high_risk_members'
    data_json = models.JSONField()
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"{self.trend_type} - {self.calculated_at}"