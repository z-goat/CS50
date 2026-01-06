import requests
import hashlib
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.db import models
from django.conf import settings
from parliament.models import Division, Member
from .logic import (
    calculate_composite_influence_score,
    calculate_cri,
    calculate_division_conflict_score,
)

from parliament.ai_service import analyze_conflict_with_ai

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
def get_stats(request):
    """
    Get basic statistics about the database
    """
    from parliament.models import Interest 
    
    last_member = Member.objects.order_by('-last_updated').first()
    stats = {
        'total_members': Member.objects.filter(current_status=True).count(),
        'parties': list(
            Member.objects.filter(current_status=True)
            .values_list('party', flat=True)
            .distinct()
            .order_by('party')
        ),
        'total_interests': Interest.objects.count(),  
        'last_sync': last_member.last_updated.isoformat() if last_member else None
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
                'category': interest.get_interest_type_display() if interest.interest_type else 'Unknown',
                'category_code': interest.interest_type,
                'summary': interest.summary or interest.raw_summary,
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
@require_http_methods(["GET"])
def get_influenced_votes(request, member_id):
    """
    Get votes influenced by member's interests
    """
    try:
        from parliament.models import Interest

        member = Member.objects.get(member_id=member_id)
        interests = list(member.interests.all())

        # Get all votes for this member with related divisions
        votes = member.votes.select_related('division').all()

        influenced = []
        for vote in votes:
            conflict = calculate_division_conflict_score(member, vote.division, interests)

            # Only include votes with conflict > 0.1
            if conflict > 0.1:
                # Find which interests are related to this division
                related_interests = []
                for interest in interests:
                    # Check if any policy tags match the interest sector
                    if interest.ai_sector and vote.division.policy_tags:
                        try:
                            tags = [tag.strip() for tag in vote.division.policy_tags]
                            if any(interest.ai_sector.lower() in (tag or '').lower() for tag in tags):
                                related_interests.append(interest)
                        except (AttributeError, TypeError):
                            pass

                # If no tag match, include a few interests as fallback
                if not related_interests and interests:
                    related_interests = interests[:3]  # Limit to first 3

                # Only add if we have related interests
                if related_interests:
                    influenced.append({
                        'division_id': vote.division.id,
                        'division_title': vote.division.title,
                        'division_date': vote.division.date.isoformat(),
                        'vote_type': vote.vote_type,
                        'conflict_score': conflict,
                        'relevant_interests': [
                            {
                                'id': i.id,
                                'summary': i.summary,
                                'sector': i.ai_sector
                            }
                            for i in related_interests
                        ]
                    })

        # For each influenced vote, get AI analysis if not already cached
        CACHE_TTL = getattr(settings, 'AI_CONFLICT_CACHE_TTL', 60 * 60 * 24 * 7)  # 7 days default
        FAILURE_TTL = getattr(settings, 'AI_CONFLICT_FAILURE_TTL', 60 * 5)  # 5 minutes for failures

        for vote_data in influenced:
            try:
                division = Division.objects.get(id=vote_data['division_id'])

                # Build a stable hash of the relevant interests (id + last_ai_processed)
                interest_meta = []
                for ri in vote_data['relevant_interests']:
                    try:
                        iobj = Interest.objects.get(id=ri['id'])
                        ts = iobj.last_ai_processed.isoformat() if iobj.last_ai_processed else 'none'
                        interest_meta.append(f"{iobj.id}:{ts}")
                    except Exception:
                        interest_meta.append(f"{ri['id']}:missing")

                interest_key = '|'.join(sorted(interest_meta))
                key_raw = f"ai_conflict:{member.member_id}:{division.id}:{interest_key}"
                cache_key = hashlib.sha1(key_raw.encode('utf-8')).hexdigest()

                cached_analysis = cache.get(cache_key)
                if cached_analysis is not None:
                    analysis = cached_analysis
                else:
                    interests_list = [
                        {
                            'summary': i.summary or i.raw_summary,
                            'sector': i.ai_sector or i.interest_type,
                            'payer': i.ai_payer or 'Unknown',
                            'value': float(i.ai_value) if i.ai_value else None,
                        }
                        for i in [Interest.objects.get(id=ri['id']) for ri in vote_data['relevant_interests']]
                    ]

                    analysis = analyze_conflict_with_ai(
                        member_name=member.name,
                        interests=interests_list,
                        division_title=division.title,
                        division_description=division.description or ""
                    )

                    # Cache the analysis; if AI reported no confidence or an error, cache briefly
                    try:
                        confidence = float(analysis.get('confidence', 0.0))
                    except Exception:
                        confidence = 0.0

                    ttl = CACHE_TTL if confidence >= 0.1 else FAILURE_TTL
                    cache.set(cache_key, analysis, ttl)

                vote_data['ai_reasoning'] = analysis.get('reasoning', 'Unable to analyze')
                vote_data['ai_confidence'] = analysis.get('confidence', 0.0)

            except Exception as e:
                vote_data['ai_reasoning'] = f'Error during analysis: {str(e)}'
                vote_data['ai_confidence'] = 0.0

        # Sort by conflict score descending
        influenced.sort(key=lambda x: x['conflict_score'], reverse=True)

        return JsonResponse({
            'member_id': member.member_id,
            'votes': influenced[:10]  # Return top 10 most conflicted votes (reduced for performance)
        })
    except Member.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)