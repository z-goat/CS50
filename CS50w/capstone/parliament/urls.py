from django.urls import path
from . import views

app_name = 'parliament'

urlpatterns = [
    # Main page
    path('', views.index, name='index'),
    
    # API endpoints
    path('api/search/', views.search_by_constituency, name='search_constituency'),
    path('api/members/', views.list_all_members, name='list_members'),
    path('api/members/<int:member_id>/', views.get_member_profile, name='member_profile'),
    path('api/stats/', views.get_stats, name='stats'),
]