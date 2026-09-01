from ..extensions import db
from ..models import (
    Achievement, AssistanceRequest, HomeVisit, TrainingProgress, VolunteerAchievement,
)
from ..notifications.service import notify
from ..volunteer_hours.service import automatic_minutes, approved_manual_minutes


def current_achievement_value(threshold_type, user_id, volunteer_profile_id):
    """The real, current count/total this volunteer has for one threshold
    type — always computed from already-committed rows, never estimated.
    "manual" has no computed value (see check_and_award) since it's never
    auto-awarded."""
    if threshold_type == "service_minutes":
        return automatic_minutes(user_id) + approved_manual_minutes(volunteer_profile_id)
    if threshold_type == "completed_visits":
        return HomeVisit.query.filter_by(assigned_to_id=user_id, status="Completed").count()
    if threshold_type == "completed_assistance":
        return AssistanceRequest.query.filter_by(assigned_to_id=user_id, status="Completed").count()
    if threshold_type == "completed_assignments":
        return (
            HomeVisit.query.filter_by(assigned_to_id=user_id, status="Completed").count()
            + AssistanceRequest.query.filter_by(assigned_to_id=user_id, status="Completed").count()
        )
    if threshold_type == "training_completed":
        return TrainingProgress.query.filter_by(volunteer_profile_id=volunteer_profile_id, status="Completed").count()
    return None


def check_and_award(user_id, volunteer_profile_id):
    """Evaluates every active, threshold-based (non-"manual") Achievement
    against this volunteer's real current numbers and awards any newly-
    qualified one. Idempotent by construction: an achievement already in
    VolunteerAchievement for this volunteer is skipped outright (never
    re-evaluated, let alone re-awarded), so calling this after every
    single relevant state change (a visit/request completing, a manual
    hours entry being approved, a course being completed) is always safe
    — running it twice, or twenty times, awards each qualifying
    achievement exactly once. Does not commit; caller's transaction does,
    same convention as notify().

    Returns the list of newly-awarded VolunteerAchievement rows (usually
    empty — most calls find nothing new to award)."""
    already_earned = {
        va.achievement_id
        for va in VolunteerAchievement.query.filter_by(volunteer_profile_id=volunteer_profile_id).all()
    }
    candidates = Achievement.query.filter(
        Achievement.active.is_(True), Achievement.threshold_type != "manual"
    ).all()

    awarded = []
    for achievement in candidates:
        if achievement.id in already_earned:
            continue
        value = current_achievement_value(achievement.threshold_type, user_id, volunteer_profile_id)
        if value is None or achievement.threshold_value is None:
            continue
        if value >= achievement.threshold_value:
            record = VolunteerAchievement(
                volunteer_profile_id=volunteer_profile_id, achievement_id=achievement.id, source="automatic",
            )
            db.session.add(record)
            db.session.flush()
            notify(
                # recipient is the volunteer's OWN user id, not the profile id
                user_id, "Achievement Awarded", f"You earned \"{achievement.name}\"!",
                achievement.description or f"You've unlocked the {achievement.name} achievement.",
                related_resource_type="achievement", related_resource_id=achievement.id,
            )
            awarded.append(record)
            already_earned.add(achievement.id)
    return awarded
