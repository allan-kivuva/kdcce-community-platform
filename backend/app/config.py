import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'kdcce.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Hard backstop enforced by Werkzeug before the request body is even
    # parsed — every upload endpoint separately validates its own real
    # limit at the application level (assignment photos: 5MB; volunteer
    # documents: 5MB images / 10MB PDFs, see documents/service.py); this
    # just stops an oversized body from ever reaching that code. Sized
    # slightly above the largest of those (10MB PDFs) for multipart
    # framing/other form fields overhead — must stay >= the largest
    # per-endpoint limit, or that endpoint's own validation error (a
    # proper 400 with a clear message) never gets a chance to run,
    # replaced by Werkzeug's generic 413 instead.
    MAX_CONTENT_LENGTH = 11 * 1024 * 1024

    # Pluggable geocoding provider (see app/geocoding/service.py) — "offline"
    # (the default) is a deterministic, non-real placeholder that needs no
    # API key and makes no network call, since this deployment doesn't have
    # a paid geocoding vendor configured. Swapping in a real provider later
    # is a matter of adding a new branch in geocode_address() and setting
    # this to its name — never hardwired, and never called automatically
    # (geocoding is always an explicit admin action, see geocoding/routes.py).
    GEOCODING_PROVIDER = os.environ.get("GEOCODING_PROVIDER", "offline")

    # Phase 9: AI is opt-in and OFF by default — this deployment has no AI
    # provider key configured, and every AI-touching feature is designed to
    # degrade to a deterministic, template-based response when it's off
    # (see app/ai/service.py). AI_ENABLED must be explicitly set to "true"
    # AND a real provider key must be present for any actual model call to
    # ever happen; the app must never depend on either being true to
    # function. The key itself is read from the environment only, at
    # request time inside the provider — never logged, never returned to
    # the frontend, never stored in this config object as a class
    # attribute (so it can't accidentally end up in a stack trace/repr).
    AI_ENABLED = os.environ.get("AI_ENABLED", "false").lower() == "true"
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "none")
    AI_MODEL = os.environ.get("AI_MODEL", "claude-haiku-4-5")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-jwt-secret-at-least-32-bytes-long"
    AI_ENABLED = False
