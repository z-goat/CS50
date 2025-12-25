import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db import models
from parliament.models import Member
import json


def index(request):
    """Main landing page"""
    return render(request, 'parliament/index.html')


@require_http_methods(["GET"])
def search_by_constituency(request):
    """
    Search for MP by postcode, constituency name, or MP name
    Returns: MP basic info and member_id for further lookups
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'error': 'Search term is required'}, status=400)
    
    # Check cache first (cache for 24 hours)
    cache_key = f'search_{query.replace(" ", "").upper()}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
    
    # Check if query looks like a postcode (contains numbers and is short)
    is_postcode = any(char.isdigit() for char in query) and len(query) <= 8
    
    if is_postcode:
        # Try postcode lookup using Parliament API
        try:
            postcode_response = requests.get(
                'https://members-api.parliament.uk/api/Location/Constituency/Search',
                params={'searchText': query},
                timeout=5
            )
            
            if postcode_response.ok:
                postcode_data = postcode_response.json()
                if postcode_data.get('items') and len(postcode_data['items']) > 0:
                    constituency_name = postcode_data['items'][0]['value']['name']
                    # Now search for MP by this constituency
                    member = Member.objects.filter(
                        constituency__iexact=constituency_name
                    ).first()
                    
                    if member:
                        result = {
                            'name': member.name,
                            'constituency': member.constituency,
                            'party': member.party,
                            'member_id': member.member_id,
                            'portrait_url': member.portrait_url,
                            'in_database': True,
                            'search_method': 'postcode'
                        }
                        cache.set(cache_key, result, 86400)
                        return JsonResponse(result)
        except Exception as e:
            # If postcode lookup fails, fall through to name search
            print(f"Postcode lookup failed: {e}")
    
    # Search in our database by constituency or name
    members = Member.objects.filter(
        models.Q(constituency__icontains=query) |
        models.Q(name__icontains=query)
    ).filter(current_status=True)
    
    if members.exists():
        member = members.first()
        result = {
            'name': member.name,
            'constituency': member.constituency,
            'party': member.party,
            'member_id': member.member_id,
            'portrait_url': member.portrait_url,
            'in_database': True,
            'total_matches': members.count(),
            'search_method': 'name'
        }
        cache.set(cache_key, result, 86400)
        return JsonResponse(result)
    
    return JsonResponse({
        'error': 'MP not found. Try a full postcode (e.g., SW1A 0AA), constituency name (e.g., "Westminster"), or MP name (e.g., "Keir Starmer")'
    }, status=404)
            


@require_http_methods(["GET"])
def get_member_profile(request, member_id):
    """
    Get complete member profile from local database
    Returns: Member details with basic statistics
    """
    try:
        member = Member.objects.get(member_id=member_id)
        
        # Get interest count (will be populated in Phase 2)
        interest_count = member.interests.count()
        
        data = {
            'member_id': member.member_id,
            'name': member.name,
            'party': member.party,
            'constituency': member.constituency,
            'portrait_url': member.portrait_url,
            'current_status': member.current_status,
            'interest_count': interest_count,
            'last_updated': member.last_updated.isoformat(),
        }
        
        return JsonResponse(data)
        
    except Member.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)


@require_http_methods(["GET"])
def list_all_members(request):
    """
    List all MPs with optional filtering
    Query params: party, constituency (partial match)
    """
    queryset = Member.objects.filter(current_status=True)
    
    # Apply filters
    party = request.GET.get('party')
    if party:
        queryset = queryset.filter(party__iexact=party)
    
    constituency = request.GET.get('constituency')
    if constituency:
        queryset = queryset.filter(constituency__icontains=constituency)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    
    start = (page - 1) * page_size
    end = start + page_size
    
    members = queryset[start:end]
    total = queryset.count()
    
    data = {
        'members': [
            {
                'member_id': m.member_id,
                'name': m.name,
                'party': m.party,
                'constituency': m.constituency,
                'portrait_url': m.portrait_url,
            }
            for m in members
        ],
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size
        }
    }
    
    return JsonResponse(data)


@require_http_methods(["GET"])
def get_stats(request):
    """
    Get basic statistics about the database
    """
    from parliament.models import Interest 
    
    stats = {
        'total_members': Member.objects.filter(current_status=True).count(),
        'parties': list(
            Member.objects.filter(current_status=True)
            .values_list('party', flat=True)
            .distinct()
            .order_by('party')
        ),
        'total_interests': Interest.objects.count(),  
        'last_sync': Member.objects.order_by('-last_updated').first().last_updated.isoformat()
        if Member.objects.exists() else None
    }
    
    return JsonResponse(stats)


@require_http_methods(["GET"])
def get_member_interests(request, member_id):
    """
    Get all interests for a specific member with AI categorization
    """
    try:
        member = Member.objects.get(member_id=member_id)
        interests = member.interests.all()
        
        data = {
            'member_id': member.member_id,
            'name': member.name,
            'total_interests': interests.count(),
            'interests': []
        }
        
        for interest in interests:
            data['interests'].append({
                'id': interest.id,
                'category': interest.get_category_code_display(),
                'category_code': interest.category_code,
                'summary': interest.summary,
                'registered_date': interest.registered_date.isoformat() if interest.registered_date else None,
                'ai_sector': interest.ai_sector,
                'ai_confidence': interest.ai_confidence,
                'ai_payer': interest.ai_payer,
                'ai_value': float(interest.ai_value) if interest.ai_value else None,
                'is_current': interest.is_current,
                'processed': interest.last_ai_processed is not None
            })
        
        return JsonResponse(data)
        
    except Member.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)