from ..models import Activity, ActivityParticipant, ActivityVolunteer, utcnow


def activity_count(program_id):
    return Activity.query.filter_by(program_id=program_id).count()


def _activity_ids(program_id):
    return [row.id for row in Activity.query.filter_by(program_id=program_id).with_entities(Activity.id).all()]


def program_analytics(program):
    """Every number here is a real, derived query over this program's own
    Activities/ActivityParticipant/ActivityVolunteer rows — nothing
    fabricated, nothing estimated. Metrics that this app genuinely can't
    back with real data (e.g. volunteer hours attributable to a program —
    Phase 3's hours system is derived from HomeVisit/AssistanceRequest
    completions only, which have no relationship to Activity/Program at
    all) are simply not included here, rather than inventing a number."""
    activity_ids = _activity_ids(program.id)
    if not activity_ids:
        return {
            "activities_count": 0,
            "upcoming_activities": 0,
            "completed_activities": 0,
            "elderly_participants_served": 0,
            "repeat_participants": 0,
            "total_event_attendance": 0,
            "volunteer_participation": 0,
            "attendance_rate": None,
        }

    now = utcnow()
    activities_q = Activity.query.filter(Activity.id.in_(activity_ids))
    upcoming = activities_q.filter(Activity.scheduled_at > now, Activity.status != "Cancelled").count()
    completed = activities_q.filter(Activity.status == "Completed").count()

    participants = ActivityParticipant.query.filter(ActivityParticipant.activity_id.in_(activity_ids)).all()
    elderly_ids = {}
    for p in participants:
        elderly_ids.setdefault(p.elderly_member_id, 0)
        elderly_ids[p.elderly_member_id] += 1
    repeat_participants = sum(1 for count in elderly_ids.values() if count > 1)
    total_attendance = sum(1 for p in participants if p.status == "Attended")
    decided = [p for p in participants if p.status in ("Attended", "No-show")]
    attendance_rate = round((sum(1 for p in decided if p.status == "Attended") / len(decided)) * 100) if decided else None

    volunteer_rows = ActivityVolunteer.query.filter(
        ActivityVolunteer.activity_id.in_(activity_ids),
        ActivityVolunteer.status.notin_(("Cancelled", "Declined")),
    ).all()
    volunteer_participation = len({v.volunteer_id for v in volunteer_rows})

    return {
        "activities_count": len(activity_ids),
        "upcoming_activities": upcoming,
        "completed_activities": completed,
        "elderly_participants_served": len(elderly_ids),
        "repeat_participants": repeat_participants,
        "total_event_attendance": total_attendance,
        "volunteer_participation": volunteer_participation,
        "attendance_rate": attendance_rate,
    }
