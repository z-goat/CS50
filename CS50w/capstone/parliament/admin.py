from django.contrib import admin
from .models import Member, Interest, Division, Vote, AnalyticsTrend

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'party', 'constituency', 'current_status']
    search_fields = ['name', 'constituency']
    list_filter = ['party', 'current_status']

admin.site.register(Interest)
admin.site.register(Division)
admin.site.register(Vote)
admin.site.register(AnalyticsTrend)