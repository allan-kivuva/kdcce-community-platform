"""Deterministic volunteer-matching scoring — no AI/ML, no randomness.
Every score is a pure function of the inputs below, so the same
(member, request_type, date) always ranks the same volunteers the same
way. Weights are small, code-defined constants (per the Phase 8 brief:
"start with code-defined weights... do not overengineer")."""

import math
from datetime import date as date_cls

from ..models import AssistanceRequest, HomeVisit, VolunteerAvailability, VolunteerProfile, VolunteerUnavailability

# Points awarded per factor — chosen so availability/skills dominate the
# ranking, distance and workload act as tie-breakers, matching the
# brief's own example weighting (availability, skills, distance, workload).
WEIGHT_AVAILABILITY = 30
WEIGHT_SKILLS = 25
WEIGHT_DISTANCE_MAX = 25
WEIGHT_WORKLOAD_MAX = 15
WEIGHT_PRIOR_RELATIONSHIP = 5

ACTIVE_STATUSES = ("Pending", "Assigned", "Accepted", "Started")


def _haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _is_available(profile, on_date):
    """Hard-ish signal, not a hard filter (an unavailability range IS a
    hard filter — see is_eligible below; a plain lack of a matching
    weekly-availability row is not, since not every volunteer has
    bothered to fill that in)."""
    if on_date is None:
        return None  # no date given — no availability signal either way
    day_name = on_date.strftime("%A")
    has_matching_slot = VolunteerAvailability.query.filter_by(
        volunteer_profile_id=profile.id, day_of_week=day_name,
    ).first() is not None
    return has_matching_slot


def _is_flagged_unavailable(profile, on_date):
    if on_date is None:
        return False
    return VolunteerUnavailability.query.filter(
        VolunteerUnavailability.volunteer_profile_id == profile.id,
        VolunteerUnavailability.start_date <= on_date,
        VolunteerUnavailability.end_date >= on_date,
    ).first() is not None


def _active_assignment_count(user_id):
    visits = HomeVisit.query.filter(HomeVisit.assigned_to_id == user_id, HomeVisit.status.in_(ACTIVE_STATUSES)).count()
    requests = AssistanceRequest.query.filter(
        AssistanceRequest.assigned_to_id == user_id, AssistanceRequest.status.in_(ACTIVE_STATUSES),
    ).count()
    return visits + requests


def _has_prior_relationship(user_id, elderly_member_id):
    prior_visit = HomeVisit.query.filter_by(assigned_to_id=user_id, elderly_member_id=elderly_member_id).first()
    if prior_visit is not None:
        return True
    prior_request = AssistanceRequest.query.filter_by(assigned_to_id=user_id, elderly_member_id=elderly_member_id).first()
    return prior_request is not None


def _skill_match(profile, keyword):
    if not keyword:
        return False
    keyword = keyword.lower()
    haystacks = (profile.skills or "", profile.areas_of_interest or "")
    return any(keyword in h.lower() for h in haystacks)


def is_eligible(profile, on_date):
    """Hard excludes — never scored, never returned at all. An
    unverified or date-flagged-unavailable volunteer simply doesn't
    appear in the results, matching the brief's explicit "unverified
    volunteer excluded" / "unavailable volunteer excluded" tests."""
    if profile.status != "Verified":
        return False
    if _is_flagged_unavailable(profile, on_date):
        return False
    return True


def score_volunteer(profile, elderly_member, on_date, keyword):
    reasons = []
    score = 0

    available = _is_available(profile, on_date)
    if available:
        score += WEIGHT_AVAILABILITY
        reasons.append("Available ✓")
    elif available is False:
        reasons.append("No matching weekly availability on file")
    # available is None (no date given) contributes nothing either way.

    skill_hit = _skill_match(profile, keyword)
    if skill_hit:
        score += WEIGHT_SKILLS
        reasons.append(f'"{keyword}" skill/interest ✓' if keyword else "Skill match ✓")

    distance_km = None
    if elderly_member.latitude is not None and elderly_member.longitude is not None and profile.latitude is not None and profile.longitude is not None:
        distance_km = round(_haversine_km(elderly_member.latitude, elderly_member.longitude, profile.latitude, profile.longitude), 1)
        # Linear falloff: 0km -> full points, 20km+ -> zero.
        distance_score = max(0, WEIGHT_DISTANCE_MAX * (1 - min(distance_km, 20) / 20))
        score += distance_score
        reasons.append(f"{distance_km} km away")
    else:
        reasons.append("Distance unknown (location not set)")

    workload = _active_assignment_count(profile.user_id)
    # Linear falloff: 0 active assignments -> full points, 6+ -> zero.
    workload_score = max(0, WEIGHT_WORKLOAD_MAX * (1 - min(workload, 6) / 6))
    score += workload_score
    reasons.append(f"{workload} active assignment(s)" + (" (low workload)" if workload <= 1 else " (higher workload)" if workload >= 4 else ""))

    prior = _has_prior_relationship(profile.user_id, elderly_member.id)
    if prior:
        score += WEIGHT_PRIOR_RELATIONSHIP
        reasons.append("Previously worked with this member")

    return {
        "volunteer_id": profile.user_id,
        "volunteer_profile_id": profile.id,
        "name": profile.user.name,
        "score": round(score, 1),
        "reasons": reasons,
        "availability_match": bool(available),
        "distance_km": distance_km,
        "workload": workload,
    }


def rank_volunteers(elderly_member, request_type=None, on_date=None):
    """The whole matching engine, top to bottom: eligible volunteers only,
    scored, sorted by score descending then volunteer_id ascending for a
    stable, fully deterministic tie-break — the same inputs always
    produce the exact same ordering."""
    if isinstance(on_date, str):
        on_date = date_cls.fromisoformat(on_date)

    profiles = VolunteerProfile.query.all()
    eligible = [p for p in profiles if is_eligible(p, on_date)]
    scored = [score_volunteer(p, elderly_member, on_date, request_type) for p in eligible]
    scored.sort(key=lambda r: (-r["score"], r["volunteer_id"]))
    return scored
