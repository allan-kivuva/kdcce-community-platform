"""Deterministic natural-language intent classification — regex/keyword
rules only, no AI/ML. This is Step 1+2 of the hybrid design the Phase 9
brief calls for ("classify user intent" then "convert intent to a safe
structured query"): a fixed, auditable set of patterns maps free text
to one of the allow-listed intents in query_service.py. An unmatched
question is reported as unsupported, never guessed at by querying
arbitrary tables or handing the raw question straight to an LLM with
database access."""

import re

DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_DAYS_PATTERN = re.compile(r"(\d{1,3})\s*days?", re.I)
_PERCENT_PATTERN = re.compile(r"(\d{1,3})\s*%|(\d{1,3})\s*percent", re.I)
_DAY_NAME_PATTERN = re.compile("|".join(DAY_NAMES), re.I)


def _extract_days(text, default=None):
    match = _DAYS_PATTERN.search(text)
    return int(match.group(1)) if match else default


def _extract_percent(text, default=None):
    match = _PERCENT_PATTERN.search(text)
    if not match:
        return default
    return int(match.group(1) or match.group(2))


def _extract_day_name(text):
    match = _DAY_NAME_PATTERN.search(text)
    if not match:
        return None
    return next(d for d in DAY_NAMES if d.lower() == match.group(0).lower())


def _extract_program_name(text):
    # "how much has the Feeding Program spent" -> "Feeding Program".
    # Only matches a run of Title-Case words immediately before
    # "Program" — NOT the whole sentence up to that point, since an
    # ordinary sentence like "How much has the Feeding Program spent"
    # also starts with a capital letter ("How"). Requiring every word in
    # the run to individually start with a capital breaks the match at
    # "much" (lowercase), so the engine correctly restarts at "Feeding".
    # Deliberately simple rather than a general NER — good enough for the
    # exact phrasing this feature supports; worst case it returns None
    # and finance_summary() just reports across all programs.
    match = re.search(r"\b((?:[A-Z][a-zA-Z&]*\s+){1,4}Program)\b", text)
    return match.group(1).strip() if match else None


# Ordered list of (compiled pattern, intent name, param extractor) — the
# FIRST match wins, so more specific patterns are listed first.
ADMIN_INTENT_RULES = [
    (re.compile(r"visit.*today|today.*visit", re.I), "VISITS_TODAY", lambda t: {}),
    (re.compile(r"unassigned.*request|request.*unassign", re.I), "UNASSIGNED_REQUESTS", lambda t: {}),
    (re.compile(r"high.?priority.*concern|concern.*high.?priority", re.I), "OVERDUE_CONCERNS", lambda t: {"min_days_open": 0, "high_priority_only": True}),
    (re.compile(r"overdue.*concern|concern.*overdue|unresolved.*concern", re.I), "OVERDUE_CONCERNS", lambda t: {"min_days_open": _extract_days(t, 3)}),
    (re.compile(r"available.*(saturday|sunday|monday|tuesday|wednesday|thursday|friday)|volunteers?.*free|free.*volunteers?", re.I), "VOLUNTEER_AVAILABILITY", lambda t: {"day_of_week": _extract_day_name(t)}),
    (re.compile(r"without.*visit|no.*visit.*\d|haven.?t.*(had|received).*visit", re.I), "MEMBERS_WITHOUT_RECENT_VISITS", lambda t: {"days": _extract_days(t, 30)}),
    (re.compile(r"highest attendance|program.*attendance|attendance.*program", re.I), "PROGRAM_ATTENDANCE", lambda t: {"period_days": _extract_days(t, 30)}),
    (re.compile(r"spent|expense|budget", re.I), "FINANCE_SUMMARY", lambda t: {"program_name": _extract_program_name(t), "period_days": _extract_days(t, 30)}),
    (re.compile(r"campaign.*(below|under)|below.*campaign", re.I), "CAMPAIGNS_BELOW_THRESHOLD", lambda t: {"percent": _extract_percent(t, 50)}),
    (re.compile(r"low.?stock|inventory.*low|running low", re.I), "INVENTORY_LOW_STOCK", lambda t: {}),
    (re.compile(r"(highest|most).*(service )?hours|hours.*(this|quarter|month)", re.I), "VOLUNTEER_HOURS_LEADERBOARD", lambda t: {"period_days": _extract_days(t, 90)}),
    (re.compile(r"operational risk|risks?\s+today|summarize.*today", re.I), "OPERATIONAL_RISK_SUMMARY", lambda t: {}),
]

VOLUNTEER_INTENT_RULES = [
    (re.compile(r"schedule|today", re.I), "VOLUNTEER_MY_SCHEDULE", lambda t: {}),
    (re.compile(r"how many hours|my hours|hours.*served|served.*hours", re.I), "VOLUNTEER_MY_HOURS", lambda t: {"period_days": _extract_days(t, 30)}),
    (re.compile(r"training", re.I), "VOLUNTEER_MY_TRAINING", lambda t: {}),
    (re.compile(r"message", re.I), "VOLUNTEER_MY_MESSAGES", lambda t: {}),
]


def classify(text, rules):
    """Returns (intent_name, params) or (None, {}) if nothing matched."""
    if not text or not text.strip():
        return None, {}
    for pattern, intent, extract_params in rules:
        if pattern.search(text):
            return intent, extract_params(text)
    return None, {}


def classify_admin_intent(text):
    return classify(text, ADMIN_INTENT_RULES)


def classify_volunteer_intent(text):
    return classify(text, VOLUNTEER_INTENT_RULES)
