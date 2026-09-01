from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from marshmallow import ValidationError

from ..auth.decorators import roles_required
from ..extensions import db
from ..models import Program, User
from ..utils import get_or_404, validation_error_response
from . import service
from .schemas import ProgramCreateSchema, ProgramUpdateSchema

bp = Blueprint("programs", __name__, url_prefix="/api/programs")

create_schema = ProgramCreateSchema()
update_schema = ProgramUpdateSchema()


def _coordinator_or_400(user_id):
    """A program coordinator is an internal management role — staff or
    admin only, same reasoning as HomeVisit.assigned_to_id being
    restricted to a legitimate assignee, just a narrower set here since
    coordinating a program (not just facilitating one activity) is
    staff-level responsibility."""
    user = db.session.get(User, user_id)
    if user is None or user.role not in ("admin", "staff"):
        return jsonify(error="Validation failed", details={"coordinator_id": ["Must be an existing staff or admin user"]}), 400
    return None


@bp.get("")
@jwt_required()
def list_programs():
    """Admin/staff manage every program regardless of status; a
    volunteer only ever sees Active ones — Draft/Paused/Completed/
    Archived are internal planning state, not something to RSVP to."""
    role = get_jwt().get("role")
    query = Program.query
    if role not in ("admin", "staff"):
        query = query.filter_by(status="Active", active=True)
    else:
        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status)
    programs = query.order_by(Program.created_at.desc()).all()
    return jsonify(programs=[p.to_dict(activity_count=service.activity_count(p.id)) for p in programs]), 200


@bp.post("")
@roles_required("admin", "staff")
def create_program():
    payload = request.get_json(silent=True) or {}
    try:
        data = create_schema.load(payload)
    except ValidationError as err:
        return validation_error_response(err)
    if not data.get("slug"):
        data["slug"] = None  # normalize "" to NULL — the unique constraint allows many NULLs, not many ""s

    if data.get("coordinator_id") is not None:
        invalid = _coordinator_or_400(data["coordinator_id"])
        if invalid:
            return invalid

    if data.get("slug"):
        if Program.query.filter_by(slug=data["slug"]).first():
            return jsonify(error="Validation failed", details={"slug": ["Already in use"]}), 400

    program = Program(**data)
    db.session.add(program)
    db.session.commit()
    return jsonify(program=program.to_dict(activity_count=0)), 201


@bp.get("/<int:program_id>")
@jwt_required()
def get_program(program_id):
    program = get_or_404(Program, program_id)
    role = get_jwt().get("role")
    if role not in ("admin", "staff") and (program.status != "Active" or not program.active):
        return jsonify(error="Forbidden"), 403
    return jsonify(program=program.to_dict(activity_count=service.activity_count(program.id))), 200


@bp.patch("/<int:program_id>")
@roles_required("admin", "staff")
def update_program(program_id):
    program = get_or_404(Program, program_id)
    payload = request.get_json(silent=True) or {}
    try:
        data = update_schema.load(payload, partial=True)
    except ValidationError as err:
        return validation_error_response(err)

    if "coordinator_id" in data and data["coordinator_id"] is not None:
        invalid = _coordinator_or_400(data["coordinator_id"])
        if invalid:
            return invalid

    if "slug" in data:
        if not data["slug"]:
            data["slug"] = None
        else:
            existing = Program.query.filter(Program.slug == data["slug"], Program.id != program.id).first()
            if existing:
                return jsonify(error="Validation failed", details={"slug": ["Already in use"]}), 400

    for field, value in data.items():
        setattr(program, field, value)
    db.session.commit()
    return jsonify(program=program.to_dict(activity_count=service.activity_count(program.id))), 200


@bp.get("/<int:program_id>/analytics")
@roles_required("admin", "staff")
def get_program_analytics(program_id):
    program = get_or_404(Program, program_id)
    return jsonify(analytics=service.program_analytics(program)), 200
