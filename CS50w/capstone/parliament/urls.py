from django.urls import path
from . import views

app_name = 'parliament'

urlpatterns = [

    path('', views.index, name='index'),
    path('research/', views.index, name='research'),
    path('about/', views.index, name='about'),
    path('mp/<int:member_id>/', views.index, name='member_detail'),
    
    # API endpoints
    path('api/search/', views.search_by_constituency, name='search_constituency'),
    path('api/members/', views.list_all_members, name='list_members'),
    path('api/members/<int:member_id>/', views.get_member_profile, name='member_profile'),
    path('api/members/<int:member_id>/interests/', views.get_member_interests, name='member_interests'),
    path('api/members/<int:member_id>/influenced-votes/', views.get_influenced_votes, name='influenced_votes'),
    path('api/stats/', views.get_stats, name='stats'),

]
