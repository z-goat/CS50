from parliament.models import Division, Vote, Interest

def calculate_vote_conflict(member, division, vote):
    """Calculate conflict score for a member's vote on a division"""
    member_interests = vote.member.interests.filter(iscurrent=True)
    division_policy = division.policy_area
    
    if not division_policy:
        return 0.0  # No policy area means no conflict
    
    conflict_score = 0.0
    for interest in member_interests:
        if interest.ai_sector == division_policy:
            weight = interest.get_weight()
            
            multiplier = 1.5 if vote.vote_type == 'AYE' else 1.0
            
            conflict_score += (weight * multiplier)
            
    return min(conflict_score, 10.0)  # Cap at 10.0
