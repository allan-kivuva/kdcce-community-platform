# The canonical starter achievement-definition set. A single source of
# truth imported by two places that both need the exact same rows:
# - migrations/versions/e29a3d056e47_*.py, which inserts these into a
#   real (dev/prod) database as part of creating the achievements table.
# - tests/conftest.py, whose test database is built via db.create_all()
#   (schema only, no migrations ever run against it), so the migration's
#   own data-seed step never applies there — this file lets the test
#   fixture seed the identical rows a real `flask db upgrade` would have
#   produced, rather than tests silently running against an empty
#   achievements table that never matches reality.
DEFAULT_ACHIEVEMENTS = [
    dict(code="first_visit", name="First Visit", description="Completed your first home visit.", icon="Home", category="Visits", threshold_type="completed_visits", threshold_value=1),
    dict(code="ten_visits", name="10 Visits", description="Completed 10 home visits.", icon="Home", category="Visits", threshold_type="completed_visits", threshold_value=10),
    dict(code="twenty_five_visits", name="25 Visits", description="Completed 25 home visits.", icon="Home", category="Visits", threshold_type="completed_visits", threshold_value=25),
    dict(code="first_assistance", name="First Assistance", description="Completed your first assistance request.", icon="HandHeart", category="Assistance", threshold_type="completed_assistance", threshold_value=1),
    dict(code="ten_assistance", name="10 Assistance Requests", description="Completed 10 assistance requests.", icon="HandHeart", category="Assistance", threshold_type="completed_assistance", threshold_value=10),
    dict(code="hours_25", name="25 Service Hours", description="Logged 25 hours of service.", icon="Clock", category="Hours", threshold_type="service_minutes", threshold_value=1500),
    dict(code="hours_50", name="50 Service Hours", description="Logged 50 hours of service.", icon="Clock", category="Hours", threshold_type="service_minutes", threshold_value=3000),
    dict(code="hours_100", name="100 Service Hours", description="Logged 100 hours of service.", icon="Clock", category="Hours", threshold_type="service_minutes", threshold_value=6000),
    dict(code="training_complete", name="Training Complete", description="Completed your first training course.", icon="GraduationCap", category="Training", threshold_type="training_completed", threshold_value=1),
    dict(code="volunteer_of_the_month", name="Volunteer of the Month", description="Recognized by staff as Volunteer of the Month.", icon="Star", category="Recognition", threshold_type="manual", threshold_value=None),
    dict(code="outstanding_service", name="Outstanding Service", description="Recognized by staff for outstanding service.", icon="Award", category="Recognition", threshold_type="manual", threshold_value=None),
    dict(code="community_champion", name="Community Champion", description="Recognized by staff as a Community Champion.", icon="Trophy", category="Recognition", threshold_type="manual", threshold_value=None),
    dict(code="reliability_recognition", name="Reliability Recognition", description="Recognized by staff for consistent, reliable service.", icon="ShieldCheck", category="Recognition", threshold_type="manual", threshold_value=None),
]
