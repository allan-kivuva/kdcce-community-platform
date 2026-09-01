from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db, limiter
from ..models import Incident
from ..utils import get_or_404, validation_error_response
from . import briefing_service, insights_service, query_service, service, summary_service
from .intent_classifier import classify_admin_intent, classify_volunteer_intent
from .schemas import AIQuerySchema, TimelineSummarySchema

admin_bp = Blueprint("ai_admin", __name__, url_prefix="/api/ai/admin")
volunteer_bp = Blueprint("ai_volunteer", __name__, url_prefix="/api/ai/volunteer")
content_bp = Blueprint("ai_content", __name__, url_prefix="/api/ai")
insights_bp = Blueprint("ai_insights", __name__, url_prefix="/api/ai/insights")

query_schema = AIQuerySchema()
timeline_schema = TimelineSummarySchema()

MAX_CUSTOM_RANGE_DAYS = 365

# Maps an intent name to the deterministic handler + a short, safe
# label shown in the UI/audit log — the ONLY intents either query
# endpoint below will ever execute. An unmatched question never falls
# through to anything else.
ADMIN_INTENT_HANDLERS = {
    "VISITS_TODAY": lambda params: query_service.visits_today(),
    "UNASSIGNED_REQUESTS": lambda params: query_service.unassigned_requests(),
    "OVERDUE_CONCERNS": lambda params: query_service.overdue_concerns(**params),
    "VOLUNTEER_AVAILABILITY": lambda params: query_service.volunteer_availability(**params),
    "MEMBERS_WITHOUT_RECENT_VISITS": lambda params: query_service.members_without_recent_visits(**params),
    "PROGRAM_ATTENDANCE": lambda params: query_service.program_attendance(**params),
    "FINANCE_SUMMARY": lambda params: query_service.finance_summary(**params),
    "CAMPAIGNS_BELOW_THRESHOLD": lambda params: query_service.campaigns_below_threshold(**params),
    "INVENTORY_LOW_STOCK": lambda params: query_service.inventory_low_stock(),
    "VOLUNTEER_HOURS_LEADERBOARD": lambda params: query_service.volunteer_hours_leaderboard(**params),
    "OPERATIONAL_RISK_SUMMARY": lambda params: query_service.operational_risk_summary(),
}

VOLUNTEER_INTENT_HANDLERS = {
    "VOLUNTEER_MY_SCHEDULE": lambda user_id, params: query_service.volunteer_my_schedule(user_id),
    "VOLUNTEER_MY_HOURS": lambda user_id, params: query_service.volunteer_my_hours(user_id, **params),
    "VOLUNTEER_MY_TRAINING": lambda user_id, params: query_service.volunteer_my_training(user_id),
    "VOLUNTEER_MY_MESSAGES": lambda user_id, params: query_service.volunteer_my_messages(user_id),
}

SUPPORTED_ADMIN_EXAMPLES = [
    "How many visits are scheduled today?", "Show unassigned assistance requests.",
    "Which volunteers are available Saturday?", "Which elderly members have not received a home visit in 30 days?",
    "Show unresolved high-priority concerns.", "Which programs had the highest attendance this month?",
    "How much has the Feeding Program spent this month?", "Show campaigns below 50% of their goal.",
    "Which volunteers have the highest service hours this quarter?", "Summarize today's operational risks.",
]
SUPPORTED_VOLUNTEER_EXAMPLES = [
    "What's my schedule today?", "How many hours have I served?", "What training do I still need?", "Do I have unread messages?",
]


@admin_bp.post("/query")
@roles_required("admin", "staff")
@limiter.limit("30 per hour")
def admin_query():
    payload = request.get_json(silent=True) or {}
    try:
        data = query_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    identity = int(get_jwt_identity())
    intent, params = classify_admin_intent(data["question"])
    if intent is None:
        service.log_ai_usage(identity, "admin_query", query_category=None, success=False, error_message="unsupported_intent")
        db.session.commit()
        return jsonify(
            supported=False,
            message="I don't have a way to answer that yet. Try one of the supported questions below.",
            examples=SUPPORTED_ADMIN_EXAMPLES,
        ), 200

    handler = ADMIN_INTENT_HANDLERS[intent]
    result = handler(params)

    ai_text, ai_used = service.explain(
        {"intent": intent, "answer": result["answer"], "result_count": len(result["results"]) if isinstance(result["results"], list) else None},
        "Rephrase the deterministic answer below in one or two friendly, concise sentences for a staff member. Do not add any fact not present in the DATA.",
        result["answer"],
    )

    service.log_ai_usage(identity, "admin_query", query_category=intent, resource_ids=result["resource_ids"], ai_used=ai_used)
    db.session.commit()
    return jsonify(supported=True, intent=intent, answer=result["answer"], ai_explanation=ai_text, ai_used=ai_used, results=result["results"]), 200


@admin_bp.get("/briefing")
@roles_required("admin", "staff")
@limiter.limit("30 per hour")
def admin_briefing():
    identity = int(get_jwt_identity())
    facts, deterministic_text = briefing_service.admin_daily_briefing()

    ai_text, ai_used = service.summarize(
        facts,
        "Write a warm, concise daily briefing for an admin/staff member from the facts below, organized under TODAY, "
        "NEEDS ATTENTION, and RECENT ACTIVITY headings, matching the structure of the data. If NEEDS ATTENTION has "
        "nothing in it, say so plainly rather than inventing an issue.",
        deterministic_text,
        max_tokens=600,
    )

    service.log_ai_usage(identity, "admin_briefing", ai_used=ai_used)
    db.session.commit()
    return jsonify(facts=facts, briefing_text=ai_text, ai_used=ai_used), 200


@volunteer_bp.post("/query")
@roles_required("volunteer")
@limiter.limit("30 per hour")
def volunteer_query():
    payload = request.get_json(silent=True) or {}
    try:
        data = query_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    identity = int(get_jwt_identity())
    intent, params = classify_volunteer_intent(data["question"])
    if intent is None:
        service.log_ai_usage(identity, "volunteer_query", success=False, error_message="unsupported_intent")
        db.session.commit()
        return jsonify(
            supported=False,
            message="I don't have a way to answer that yet. Try one of the supported questions below.",
            examples=SUPPORTED_VOLUNTEER_EXAMPLES,
        ), 200

    # The volunteer intent map ONLY ever contains self-scoped handlers —
    # there is no code path from a volunteer's question to any other
    # volunteer's or any admin-only data, regardless of what the
    # question text says (see VOLUNTEER_INTENT_HANDLERS above).
    handler = VOLUNTEER_INTENT_HANDLERS[intent]
    result = handler(identity, params)

    ai_text, ai_used = service.explain(
        {"intent": intent, "answer": result["answer"]},
        "Rephrase the deterministic answer below in one friendly sentence for the volunteer who asked. Do not add any fact not present in the DATA.",
        result["answer"],
    )

    service.log_ai_usage(identity, "volunteer_query", query_category=intent, resource_ids=result["resource_ids"], ai_used=ai_used)
    db.session.commit()
    return jsonify(supported=True, intent=intent, answer=result["answer"], ai_explanation=ai_text, ai_used=ai_used, results=result["results"]), 200


@volunteer_bp.get("/briefing")
@roles_required("volunteer")
@limiter.limit("30 per hour")
def volunteer_briefing():
    identity = int(get_jwt_identity())
    facts, deterministic_text = briefing_service.volunteer_daily_briefing(identity)

    ai_text, ai_used = service.summarize(
        facts,
        "Write a warm, personal, concise daily briefing for this volunteer from the facts below, under TODAY, "
        "YOUR IMPACT, and NEXT MILESTONE headings. Address them by first name.",
        deterministic_text,
        max_tokens=400,
    )

    service.log_ai_usage(identity, "volunteer_briefing", ai_used=ai_used)
    db.session.commit()
    return jsonify(facts=facts, briefing_text=ai_text, ai_used=ai_used), 200


@content_bp.post("/concerns/<int:incident_id>/summary")
@roles_required("admin", "staff")
@limiter.limit("30 per hour")
def concern_summary(incident_id):
    incident = get_or_404(Incident, incident_id)
    identity = int(get_jwt_identity())
    facts, resource_ids = summary_service.gather_concern_facts(incident)
    fallback = summary_service.render_concern_summary_fallback(facts)

    ai_text, ai_used = service.summarize(
        facts,
        "Summarize this safeguarding concern in 2-4 sentences: what was reported, what follow-up has happened, and "
        "its current status. State only what the DATA shows; if something is unclear or missing, say so rather than "
        "guessing. Never suggest changing the concern's status, priority, or assignment.",
        fallback,
        max_tokens=350,
    )

    service.log_ai_usage(identity, "concern_summary", query_category="CONCERN_SUMMARY", resource_ids=resource_ids, ai_used=ai_used)
    db.session.commit()
    return jsonify(
        incident_id=incident.id, summary=ai_text, ai_used=ai_used, ai_generated=True,
        source_resource_ids=resource_ids, human_review_required=True,
    ), 200


@content_bp.post("/elderly/<int:member_id>/timeline-summary")
@roles_required("admin", "staff")
@limiter.limit("30 per hour")
def timeline_summary(member_id):
    from ..models import ElderlyMember

    member = get_or_404(ElderlyMember, member_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = timeline_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)

    if data["since"] and data["until"]:
        if data["until"] < data["since"]:
            return jsonify(error="Validation failed", details={"until": ["Must not be before since"]}), 400
        if (data["until"] - data["since"]) > timedelta(days=MAX_CUSTOM_RANGE_DAYS):
            return jsonify(error="Validation failed", details={"until": [f"Custom range cannot exceed {MAX_CUSTOM_RANGE_DAYS} days"]}), 400
        facts, resource_ids = summary_service.gather_timeline_facts(member, since=data["since"].isoformat(), until=data["until"].isoformat())
    else:
        facts, resource_ids = summary_service.gather_timeline_facts(member, days=data["days"])

    fallback = summary_service.render_timeline_summary_fallback(facts)
    identity = int(get_jwt_identity())

    ai_text, ai_used = service.summarize(
        facts,
        "Write one short, readable paragraph summarizing this member's recorded activity over the given period, "
        "from the event counts and events in the DATA. Do not mention any date, count, or event not present there.",
        fallback,
        max_tokens=300,
    )

    service.log_ai_usage(identity, "timeline_summary", query_category="TIMELINE_SUMMARY", resource_ids=resource_ids, ai_used=ai_used)
    db.session.commit()
    return jsonify(member_id=member.id, summary=ai_text, ai_used=ai_used, ai_generated=True, since=facts["since"], until=facts["until"]), 200


@insights_bp.get("/workload")
@roles_required("admin", "staff")
def workload_insights_route():
    identity = int(get_jwt_identity())
    data = insights_service.workload_insights()

    ai_text, ai_used = service.explain(
        data, "Explain these workload findings in 1-3 sentences, plainly, without recommending any specific action.",
        _workload_fallback_text(data),
    )

    service.log_ai_usage(identity, "workload_insights", ai_used=ai_used)
    db.session.commit()
    return jsonify(data=data, explanation=ai_text, ai_used=ai_used), 200


def _workload_fallback_text(data):
    parts = []
    if data["overloaded_volunteers"]:
        parts.append(f"{len(data['overloaded_volunteers'])} volunteer(s) carry more than twice the median active workload")
    if data["idle_volunteers"]:
        parts.append(f"{len(data['idle_volunteers'])} verified volunteer(s) currently have no active assignments")
    if data["understaffed_programs"]:
        parts.append(f"{len(data['understaffed_programs'])} upcoming program(s) are understaffed")
    return ("; ".join(parts) + ".") if parts else "No notable workload issues right now."


@insights_bp.get("/trends")
@roles_required("admin", "staff")
def trends_route():
    identity = int(get_jwt_identity())
    period_days = request.args.get("period_days", 30, type=int)
    period_days = min(max(period_days, 7), 90)
    data = insights_service.operational_trends(period_days=period_days)

    ai_text, ai_used = service.explain(
        data, "Explain the most notable of these period-over-period trends in 1-3 sentences, citing the real percentage change. "
        "Do not invent a trend for a metric that barely moved.",
        _trends_fallback_text(data),
    )

    service.log_ai_usage(identity, "trend_insights", ai_used=ai_used)
    db.session.commit()
    return jsonify(data=data, explanation=ai_text, ai_used=ai_used), 200


def _trends_fallback_text(data):
    parts = []
    for label, key in (("Assistance requests", "assistance_requests"), ("Visit completions", "visit_completions"), ("Concerns", "concerns")):
        trend = data[key]
        if trend["direction"] != "flat":
            parts.append(f"{label} {'rose' if trend['direction'] == 'up' else 'fell'} {abs(trend['pct_change'])}% vs the previous period")
    return ("; ".join(parts) + ".") if parts else "No notable change compared with the previous period."


@insights_bp.get("/recommendations")
@roles_required("admin", "staff")
def recommendations_route():
    identity = int(get_jwt_identity())
    data = insights_service.smart_recommendations()

    resource_ids = [r["resource_id"] for r in data["recommendations"] if r.get("resource_id") is not None]
    service.log_ai_usage(identity, "smart_recommendations", resource_ids=resource_ids)
    db.session.commit()
    return jsonify(data=data), 200


@admin_bp.get("/status")
@roles_required("admin", "staff")
def ai_status():
    return jsonify(ai_enabled=service.is_enabled()), 200
