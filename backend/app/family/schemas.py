"""Explicit, field-level-safe serializers for the family portal — never
the admin `to_dict()` on any of these models. Each function is an
allowlist: only the fields listed here are ever visible to a family
account, deliberately excluding staff notes, health/vulnerability
details, incident/concern data, medication, financial data, volunteer
private data, and audit logs, per the Phase 8 brief."""

from marshmallow import Schema, fields, validate


class FamilyAccessCreateSchema(Schema):
    user_id = fields.Integer(required=True)
    elderly_member_id = fields.Integer(required=True)
    relationship = fields.String(required=True, validate=validate.Length(min=1, max=60))


def family_member_summary(member, relationship_label=None):
    data = {
        "id": member.id,
        "member_id": member.member_id,
        "full_name": member.full_name,
        "status": member.status,
    }
    if relationship_label is not None:
        data["relationship"] = relationship_label
    return data


def family_visit_summary(visit):
    return {
        "id": visit.id,
        "status": visit.status,
        "scheduled_at": visit.scheduled_at.isoformat() if visit.scheduled_at else None,
        "completed_at": visit.completed_at.isoformat() if visit.completed_at else None,
        "assigned_volunteer_name": visit.assigned_to.name if visit.assigned_to else None,
    }


def family_activity_summary(participant):
    activity = participant.activity
    return {
        "id": participant.id,
        "activity_id": activity.id,
        "title": activity.title,
        "activity_type": activity.activity_type,
        "location": activity.location,
        "scheduled_at": activity.scheduled_at.isoformat() if activity.scheduled_at else None,
        "status": participant.status,
    }


def family_meal_attendance_summary(attendance):
    meal = attendance.meal
    return {
        "id": attendance.id,
        "meal_id": meal.id,
        "meal_date": meal.meal_date.isoformat(),
        "meal_type": meal.meal_type,
    }
