from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import ValidationError

from ..extensions import db, limiter
from ..models import User, VolunteerProfile
from .schemas import RegisterSchema, LoginSchema

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

register_schema = RegisterSchema()
login_schema = LoginSchema()


def _identity_claims(user):
    # Encoded straight into the JWT so every protected route can trust
    # req.user's role/id without a DB hit — but the id itself is what
    # `get_jwt_identity()` returns, never something the client supplies.
    return {"role": user.role}


@bp.post("/register")
@limiter.limit("10 per minute")
def register():
    payload = request.get_json(silent=True) or {}
    try:
        data = register_schema.load(payload)
    except ValidationError as err:
        return jsonify(error="Validation failed", details=err.messages), 400

    if User.query.filter_by(email=data["email"].lower()).first():
        return jsonify(error="An account with that email already exists"), 409

    user = User(name=data["name"].strip(), email=data["email"].lower(), role="volunteer")
    user.set_password(data["password"])
    db.session.add(user)
    db.session.flush()  # assigns user.id without committing yet
    # Public self-signup always makes a volunteer, so it always gets a
    # volunteer profile too (status Pending until staff verify it) —
    # see app/volunteers/.
    db.session.add(VolunteerProfile(user_id=user.id))
    db.session.commit()

    access_token = create_access_token(identity=str(user.id), additional_claims=_identity_claims(user))
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=_identity_claims(user))
    return jsonify(user=user.to_dict(), access_token=access_token, refresh_token=refresh_token), 201


@bp.post("/login")
@limiter.limit("10 per minute")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        data = login_schema.load(payload)
    except ValidationError as err:
        return jsonify(error="Validation failed", details=err.messages), 400

    user = User.query.filter_by(email=data["email"].lower()).first()
    if user is None or not user.check_password(data["password"]):
        return jsonify(error="Invalid email or password"), 401

    access_token = create_access_token(identity=str(user.id), additional_claims=_identity_claims(user))
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=_identity_claims(user))
    return jsonify(user=user.to_dict(), access_token=access_token, refresh_token=refresh_token), 200


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify(error="User not found"), 404
    access_token = create_access_token(identity=str(user.id), additional_claims=_identity_claims(user))
    return jsonify(access_token=access_token), 200


@bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify(error="User not found"), 404
    return jsonify(user=user.to_dict()), 200
