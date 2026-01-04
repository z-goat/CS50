import requests
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.db import models
from parliament.models import Division, Member
from .logic import (
    calculate_composite_influence_score,
    calculate_cri,
    calculate_division_conflict_score,
)


def index(request, *args, **kwargs):
    return render(request, 'parliament/index.html')

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
def search_by_constituency(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return JsonResponse({'error': 'Search term is required'}, status=400)

    cache_key = f'search_{query.replace(" ", "").upper()}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    is_postcode = any(char.isdigit() for char in query) and len(query) <= 8

    if is_postcode:
        try:
            postcode_response = requests.get(
                'https://members-api.parliament.uk/api/Location/Constituency/Search',
                params={'searchText': query},
                timeout=5
            )

            if postcode_response.ok:
                postcode_data = postcode_response.json()
                if postcode_data.get('items'):
                    constituency_name = postcode_data['items'][0]['value']['name']
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
        except Exception:
            pass

    members = Member.objects.filter(
        models.Q(constituency__icontains=query) |
        models.Q(name__icontains=query),
        current_status=True
    )

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

    return JsonResponse({'error': 'MP not found'}, status=404)


@require_http_methods(["GET"])
def get_member_profile(request, member_id):
    cache_key = f"member_profile_{member_id}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        member = Member.objects.get(member_id=member_id)

        interests = list(member.interests.all())
        divisions = list(
            Division.objects
            .filter(votes__member=member)
            .only("id", "policy_tags")
            .distinct()
        )

        composite = calculate_composite_influence_score(member)

        conflict_total = 0.0
        cri_total = 0.0
        count = 0

        for d in divisions:
            conflict = calculate_division_conflict_score(member, d, interests)
            cri = calculate_cri(member, d, interests, composite)

            conflict_total += conflict
            cri_total += cri
            count += 1

        avg_conflict = round(conflict_total / count, 2) if count else 0.0
        avg_cri = round(cri_total / count, 2) if count else 0.0

        data = {
            'member_id': member.member_id,
            'name': member.name,
            'party': member.party,
            'constituency': member.constituency,
            'portrait_url': member.portrait_url,
            'current_status': member.current_status,
            'interest_count': len(interests),
            'avg_conflict': avg_conflict,
            'avg_cri': avg_cri,
            'last_updated': member.last_updated.isoformat(),
        }

        cache.set(cache_key, data, 60 * 60 * 6)
        return JsonResponse(data)

    except Member.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)
