"""Operations-map data — admin/staff only (enforced in routes.py), and
deliberately thin: only geocoded records ever appear (no address text,
just derived lat/lng), and only the fields the map popover actually
needs (name, record type, status, assigned volunteer, scheduled time)
— never health/vulnerability/financial/incident-investigation detail.
Program locations are NOT included: Program has no coordinate columns
(Phase 8's migration section only added them to ElderlyMember/
VolunteerProfile) and geocoding a plain location string with no
underlying member record wasn't part of this phase's scope — see the
Phase 8 report."""

from ..models import AssistanceRequest, ElderlyMember, HomeVisit, Incident, VolunteerProfile

LAYERS = ("elderly", "home_visits", "assistance", "incidents", "volunteers")


def _elderly_points(status=None):
    query = ElderlyMember.query.filter(ElderlyMember.latitude.isnot(None), ElderlyMember.longitude.isnot(None))
    if status:
        query = query.filter_by(status=status)
    return [
        {
            "id": m.id, "layer": "elderly", "record_type": "elderly_member", "name": m.full_name,
            "status": m.status, "assigned_to": None, "scheduled_at": None,
            "latitude": m.latitude, "longitude": m.longitude,
        }
        for m in query.all()
    ]


def _home_visit_points(status=None, date_from=None, date_to=None):
    query = (
        HomeVisit.query.join(ElderlyMember, HomeVisit.elderly_member_id == ElderlyMember.id)
        .filter(ElderlyMember.latitude.isnot(None), ElderlyMember.longitude.isnot(None))
    )
    if status:
        query = query.filter(HomeVisit.status == status)
    if date_from:
        query = query.filter(HomeVisit.scheduled_at >= date_from)
    if date_to:
        query = query.filter(HomeVisit.scheduled_at <= date_to)
    return [
        {
            "id": v.id, "layer": "home_visits", "record_type": "home_visit", "name": v.elderly_member.full_name,
            "status": v.status, "assigned_to": v.assigned_to.name if v.assigned_to else None,
            "scheduled_at": v.scheduled_at.isoformat() if v.scheduled_at else None,
            "latitude": v.elderly_member.latitude, "longitude": v.elderly_member.longitude,
        }
        for v in query.all()
    ]


def _assistance_points(status=None, date_from=None, date_to=None):
    query = (
        AssistanceRequest.query.join(ElderlyMember, AssistanceRequest.elderly_member_id == ElderlyMember.id)
        .filter(ElderlyMember.latitude.isnot(None), ElderlyMember.longitude.isnot(None))
    )
    if status:
        query = query.filter(AssistanceRequest.status == status)
    if date_from:
        query = query.filter(AssistanceRequest.scheduled_at >= date_from)
    if date_to:
        query = query.filter(AssistanceRequest.scheduled_at <= date_to)
    return [
        {
            "id": r.id, "layer": "assistance", "record_type": "assistance_request", "name": r.elderly_member.full_name,
            "status": r.status, "assigned_to": r.assigned_to.name if r.assigned_to else None,
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "latitude": r.elderly_member.latitude, "longitude": r.elderly_member.longitude,
        }
        for r in query.all()
    ]


def _incident_points(status=None):
    query = (
        Incident.query.join(ElderlyMember, Incident.elderly_member_id == ElderlyMember.id)
        .filter(ElderlyMember.latitude.isnot(None), ElderlyMember.longitude.isnot(None))
    )
    if status:
        query = query.filter(Incident.status == status)
    return [
        {
            "id": i.id, "layer": "incidents", "record_type": "incident", "name": i.elderly_member.full_name,
            "status": i.status, "assigned_to": i.assigned_to.name if i.assigned_to else None,
            "scheduled_at": None, "severity": i.severity,
            "latitude": i.elderly_member.latitude, "longitude": i.elderly_member.longitude,
        }
        for i in query.all()
    ]


def _volunteer_points():
    query = VolunteerProfile.query.filter(
        VolunteerProfile.latitude.isnot(None), VolunteerProfile.longitude.isnot(None), VolunteerProfile.status == "Verified",
    )
    return [
        {
            "id": p.user_id, "layer": "volunteers", "record_type": "volunteer", "name": p.user.name,
            "status": p.status, "assigned_to": None, "scheduled_at": None,
            "latitude": p.latitude, "longitude": p.longitude,
        }
        for p in query.all()
    ]


def get_map_points(layers, status=None, date_from=None, date_to=None):
    points = []
    if "elderly" in layers:
        points += _elderly_points(status)
    if "home_visits" in layers:
        points += _home_visit_points(status, date_from, date_to)
    if "assistance" in layers:
        points += _assistance_points(status, date_from, date_to)
    if "incidents" in layers:
        points += _incident_points(status)
    if "volunteers" in layers:
        points += _volunteer_points()
    return points
