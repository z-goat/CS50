from parliament.models import Division, Vote, Interest

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
    
    Args:
        member: Member instance
        conflict_sectors: List of sector names considered a potential conflict
    
    Returns:
        float: total conflict score
    """
    total_score = 0.0

    for interest in member.interests.all():
        # Only consider current interests
        if not interest.is_current:
            continue

        # Determine which sector to use: AI sector preferred, fallback to interest_type
        sector = interest.ai_sector or interest.interest_type

        # If the interest matches a conflict sector, add weighted score
        if sector in conflict_sectors:
            weight = interest.get_weight()
            
            # Optionally scale by AI confidence if AI sector is used
            if interest.ai_sector:
                weight *= interest.ai_confidence or 1.0

            total_score += weight

    return total_score

def calculate_division_conflict_score(member, division) -> float:
    if not division.policy_tags:
        return 0.0

    score = calculate_interest_conflict_score(
        member,
        division.policy_tags
    )

    return round(score, 2)

    return round(sum(scores) / len(relevant_interests), 2)

def calculate_composite_influence_score(member) -> float:
    interests = Interest.objects.filter(member=member)
    if not interests:
        return 0.0

    weights = [i.get_weight() for i in interests]
    return round(sum(weights) / len(weights) * 10, 2)


def calculate_correlation_score(member, division) -> float:
    interests = Interest.objects.filter(member=member)
    if not interests:
        return 0.0

    relevant = [
        i.get_weight()
        for i in interests
            if i.ai_sector and i.ai_sector in division.policy_tags
    ]

    if not relevant:
        return 0.0

    return round(sum(relevant) / len(relevant) * 10, 2)


def calculate_cri(member, division):
    correlation = calculate_correlation_score(member, division)
    conflict = calculate_division_conflict_score(member, division)
    composite = calculate_composite_influence_score(member)

    return round((correlation + (10 - conflict) + composite) / 3, 2)