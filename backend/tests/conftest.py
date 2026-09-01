import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.achievements.seed_data import DEFAULT_ACHIEVEMENTS
from app.config import TestConfig
from app.extensions import db as _db
from app.models import Achievement, User


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        _db.create_all()
        # db.create_all() builds schema only, never runs migrations — so
        # the achievement-definition seed step that lives in this
        # feature's own migration (e29a3d056e47) never applies to this
        # in-memory test database. Seed the identical rows here from the
        # same DEFAULT_ACHIEVEMENTS source, so tests exercise achievements
        # against the same starter set a real `flask db upgrade` produces.
        for row in DEFAULT_ACHIEVEMENTS:
            _db.session.add(Achievement(**row, active=True))
        _db.session.commit()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(client):
    """Register a user via the real endpoint and return (user_dict, access_token, refresh_token)."""

    def _make(name="Volunteer One", email="v1@example.com", password="hunter22"):
        resp = client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )
        body = resp.get_json()
        return body["user"], body["access_token"], body["refresh_token"]

    return _make


@pytest.fixture()
def make_staff_user(app):
    """Create a user with an elevated role directly in the DB — there is no
    public endpoint for this on purpose (only volunteer self-signup is
    public), so tests seed it directly and mint a token the same way the
    real login flow would encode it."""

    def _make(role, name="Staffer", email=None):
        email = email or f"{role}@example.com"
        user = User(name=name, email=email, role=role)
        user.set_password("hunter22")
        _db.session.add(user)
        _db.session.commit()
        with app.app_context():
            token = create_access_token(identity=str(user.id), additional_claims={"role": role})
        return user.to_dict(), token

    return _make


@pytest.fixture()
def auth_header():
    def _header(token):
        return {"Authorization": f"Bearer {token}"}

    return _header
