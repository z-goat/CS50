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
    
    CATEGORY_CHOICES = [
        ('1', 'Employment and earnings'),
        ('2', 'Donations and other support'),
        ('3', 'Gifts, benefits and hospitality'),
        ('4', 'Visits outside the UK'),
        ('5', 'Land and property'),
        ('6', 'Shareholdings'),
        ('7', 'Miscellaneous'),
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='interests')
    category_code = models.CharField(max_length=2, choices=CATEGORY_CHOICES)
    summary = models.TextField()
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
            models.Index(fields=['member', 'category_code']),
            models.Index(fields=['ai_sector']),
        ]
    
    def get_weight(self):
        """Return category weight for scoring algorithm"""
        weights = {
            '6': 1.0,  # Shareholdings
            '1': 0.9,  # Employment (directorships)
            '2': 0.8,  # Donations
            '5': 0.7,  # Land/property
            '3': 0.5,  # Gifts
            '4': 0.4,  # Visits
            '7': 0.3,  # Misc
        }
        return weights.get(self.category_code, 0.5)
    
    def __str__(self):
        return f"{self.member.name} - {self.get_category_code_display()}"


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