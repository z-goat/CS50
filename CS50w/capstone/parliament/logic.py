from parliament.models import Division, Vote, Interest

def calculate_composite_influence_score(member):
    score = 0.0
    for interest in member.interests.all():
        score += interest.get_weight()
    return round(score, 2)


def calculate_correlation_score(member, division):
    score = 0.0
    for interest in member.interests.all():
        for tag in division.policy_tags:
            if interest.sector == tag:
                score += interest.get_weight()
    return round(score, 2)


def calculate_cri(member, division):
    correlation = calculate_correlation_score(member, division)
    composite = calculate_composite_influence_score(member)
    return round((correlation + composite) / 2, 2)