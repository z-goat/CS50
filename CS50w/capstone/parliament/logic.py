from parliament.models import Division, Vote, Interest

from parliament.ai_service import analyze_conflict_with_ai
VOTE_MAP = {
    "AyeVote": 1,
    "NoVote": -1,
    "AbstainVote": 0,
}

STANCE_MAP = {
    "support": 1,
    "oppose": -1,
    "neutral": 0,
}


def calculate_interest_conflict_score(member, conflict_sectors: list[str]) -> float:
    """
    Calculate a member's conflict score based on their declared financial interests
    and relevant policy sectors.
    """
    total_score = 0.0

    for interest in member.interests.all():
        if not interest.is_current:
            continue

        sector = interest.ai_sector or interest.interest_type

        if sector in conflict_sectors:
            weight = interest.get_weight()
            if interest.ai_sector:
                weight *= interest.ai_confidence or 1.0
            total_score += weight

    return total_score


def calculate_division_conflict_score(member, division, interests) -> float:
    """
    Calculate conflict score using AI analysis
    """
    if not interests or not division.title:
        return 0.0
    
    # Build interests list for AI
    interests_data = []
    for interest in interests:
        if not interest.is_current:
            continue
        
        interests_data.append({
            'summary': interest.summary or interest.raw_summary,
            'sector': interest.ai_sector or interest.interest_type,
            'payer': interest.ai_payer or 'Unknown',
            'value': float(interest.ai_value) if interest.ai_value else None,
        })
    
    if not interests_data:
        return 0.0
    
    # Use AI to analyze the conflict
    analysis = analyze_conflict_with_ai(
        member_name=member.name,
        interests=interests_data,
        division_title=division.title,
        division_description=division.description or ""
    )
    
    # Return the AI-determined conflict score
    return analysis.get('conflict_score', 0.0)


def calculate_composite_influence_score(member) -> float:
    interests = Interest.objects.filter(member=member)
    if not interests:
        return 0.0

    weights = [i.get_weight() for i in interests]
    return round(sum(weights) / len(weights) * 10, 2)


def calculate_correlation_score(member, division, interests) -> float:
    if not division.policy_tags:
        return 0.0

    relevant = [
        i.get_weight()
        for i in interests
        if i.ai_sector and any(i.ai_sector.lower() in tag.lower() for tag in division.policy_tags if tag)
    ]

    if not relevant:
        return 0.0

    return round(sum(relevant) / len(relevant) * 10, 2)


def calculate_cri(member, division, interests, composite_score) -> float:
    correlation = calculate_correlation_score(member, division, interests)
    conflict = calculate_division_conflict_score(member, division, interests)
    # CRI is composite influence + correlation - conflict risk
    if conflict > 10:
        conflict = 10
    cri_value = (composite_score + correlation) / 2 if correlation > 0 else composite_score
    return round(max(0, cri_value - (conflict / 2)), 2)
