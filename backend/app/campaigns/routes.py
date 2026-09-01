from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from ..audit.service import log_action
from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Campaign, Program
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import CampaignCreateSchema, CampaignUpdateSchema

# Same public/admin split as blog/gallery/team: GET /api/campaigns is the
# public, unauthenticated listing (only what's meant to be public);
# everything else lives under /api/admin/campaigns.
bp = Blueprint("campaigns", __name__)
admin_bp = Blueprint("admin_campaigns", __name__, url_prefix="/api/admin/campaigns")

create_schema = CampaignCreateSchema()
update_schema = CampaignUpdateSchema()

_SNAPSHOT_FIELDS = ("name", "goal_amount", "program_id", "start_date", "end_date", "status", "public_visible")


def _snapshot(campaign):
    snapshot = {}
    for field in _SNAPSHOT_FIELDS:
        value = getattr(campaign, field)
        if field == "goal_amount":
            value = float(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        snapshot[field] = value
    return snapshot


def _program_or_400(program_id):
    if db.session.get(Program, program_id) is None:
        return jsonify(error="Validation failed", details={"program_id": ["Program not found"]}), 400
    return None


@bp.get("/api/campaigns")
def list_public_campaigns():
    """Public, unauthenticated — only public_visible campaigns in a
    public-appropriate status (Active/Completed). Draft/Paused/Archived
    never appear here even if public_visible was mistakenly left on."""
    campaigns = (
        Campaign.query.filter(Campaign.public_visible.is_(True), Campaign.status.in_(service.PUBLIC_STATUSES))
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return jsonify(campaigns=[c.public_dict(progress=service.campaign_progress(c)) for c in campaigns]), 200


@admin_bp.get("")
@roles_required("admin", "staff")
def list_campaigns():
    query = Campaign.query
    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)
    program_id = request.args.get("program_id", type=int)
    if program_id is not None:
        query = query.filter_by(program_id=program_id)
    campaigns = query.order_by(Campaign.created_at.desc()).all()
    return jsonify(campaigns=[c.to_dict(progress=service.campaign_progress(c, recent_limit=0)) for c in campaigns]), 200


@admin_bp.post("")
@roles_required("admin", "staff")
def create_campaign():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    if data.get("program_id") is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid
    if data.get("slug") and Campaign.query.filter_by(slug=data["slug"]).first():
        return jsonify(error="Validation failed", details={"slug": ["Already in use"]}), 400
    if not data.get("slug"):
        data["slug"] = None

    campaign = Campaign(**data, created_by_id=int(get_jwt_identity()))
    db.session.add(campaign)
    db.session.flush()
    log_action(int(get_jwt_identity()), "create", "campaign", campaign.id, after=_snapshot(campaign))
    db.session.commit()
    return jsonify(campaign=campaign.to_dict(progress=service.campaign_progress(campaign))), 201


@admin_bp.get("/<int:campaign_id>")
@roles_required("admin", "staff")
def get_campaign(campaign_id):
    campaign = get_or_404(Campaign, campaign_id)
    return jsonify(campaign=campaign.to_dict(progress=service.campaign_progress(campaign))), 200


@admin_bp.patch("/<int:campaign_id>")
@roles_required("admin", "staff")
def update_campaign(campaign_id):
    campaign = get_or_404(Campaign, campaign_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)
    if "program_id" in data and data["program_id"] is not None:
        invalid = _program_or_400(data["program_id"])
        if invalid:
            return invalid
    if "slug" in data:
        if not data["slug"]:
            data["slug"] = None
        elif Campaign.query.filter(Campaign.slug == data["slug"], Campaign.id != campaign.id).first():
            return jsonify(error="Validation failed", details={"slug": ["Already in use"]}), 400

    before = _snapshot(campaign)
    for field, value in data.items():
        setattr(campaign, field, value)
    db.session.flush()
    action = "status_change" if "status" in data else "update"
    log_action(int(get_jwt_identity()), action, "campaign", campaign.id, before=before, after=_snapshot(campaign))
    db.session.commit()
    return jsonify(campaign=campaign.to_dict(progress=service.campaign_progress(campaign))), 200


@admin_bp.post("/<int:campaign_id>/link-donations")
@roles_required("admin", "staff")
def link_donations(campaign_id):
    campaign = get_or_404(Campaign, campaign_id)
    linked = service.link_matching_donations(campaign)
    if linked:
        log_action(int(get_jwt_identity()), "link_donations", "campaign", campaign.id, after={"linked_count": linked})
    db.session.commit()
    return jsonify(linked_count=linked), 200
