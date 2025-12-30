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

def calculate_interest_conflict_score(interest, member, division) -> float:
    vote = Vote.objects.filter(
        member=member,
        division=division
    ).first()

    if not vote:
        return 0.0

    vote_value = VOTE_MAP.get(vote.vote_type, 0)
    stance_value = STANCE_MAP.get(interest.stance, 0)

    if stance_value == 0:
        return 0.0

    if vote_value == stance_value:
        return 0.0

    if vote_value == 0:
        return 5.0 * interest.get_weight()

    return 10.0 * interest.get_weight()

def calculate_division_conflict_score(member, division) -> float:
    interests = Interest.objects.filter(member=member)

    relevant_interests = [
        i for i in interests
            if i.ai_sector and i.ai_sector in division.policy_tags
    ]

    if not relevant_interests:
        return 0.0

    scores = [
        calculate_interest_conflict_score(i, member, division)
        for i in relevant_interests
    ]

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