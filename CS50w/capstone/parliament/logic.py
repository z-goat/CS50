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
    if not division.policy_tags:
        return 0.0

    conflict_sectors = set(division.policy_tags)
    score = 0.0

    for interest in interests:
        if not interest.is_current:
            continue

        sector = interest.ai_sector or interest.interest_type
        if sector in conflict_sectors:
            weight = interest.get_weight()
            if interest.ai_sector:
                weight *= interest.ai_confidence or 1.0
            score += weight

    return score


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
        if i.ai_sector and i.ai_sector in division.policy_tags
    ]

    if not relevant:
        return 0.0

    return sum(relevant) / len(relevant) * 10


def calculate_cri(member, division, interests, composite_score):
    correlation = calculate_correlation_score(member, division, interests)
    conflict = calculate_division_conflict_score(member, division, interests)

    return round((correlation + (10 - conflict) + composite_score) / 3, 2)
