from datetime import timezone

from ..extensions import db
from ..models import AssignmentMessage, AssistanceRequest, Conversation, DirectMessage, HomeVisit, User, utcnow


def _as_naive_utc(dt):
    """SQLite does not reliably round-trip a DateTime(timezone=True)
    column's tzinfo across a session boundary — see the identical helper
    in volunteer_hours/service.py, which first uncovered this. Applied
    here for the same reason: subtracting two independently-loaded
    datetimes can otherwise raise "can't subtract offset-naive and
    offset-aware datetimes" depending on which one happened to keep its
    tzinfo."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo is not None else dt

MESSAGE_TEMPLATES = [
    {"key": "visit_reminder", "title": "Visit Reminder",
     "body": "Hi {name}, just a reminder about your upcoming home visit. Please let us know if you have any questions."},
    {"key": "assignment_confirmation", "title": "Assignment Confirmation",
     "body": "Hi {name}, thank you for accepting this assignment. We appreciate your commitment."},
    {"key": "follow_up_request", "title": "Follow-up Request",
     "body": "Hi {name}, could you share a quick update on how things went? Let us know if any follow-up is needed."},
    {"key": "training_reminder", "title": "Training Reminder",
     "body": "Hi {name}, a friendly reminder to complete your required training course when you get a chance."},
    {"key": "event_reminder", "title": "Event Reminder",
     "body": "Hi {name}, just a reminder about the upcoming event/activity. We look forward to seeing you there."},
    {"key": "general_check_in", "title": "General Check-in",
     "body": "Hi {name}, just checking in — how are things going? Let us know if you need any support."},
]


class MessagingError(Exception):
    """Raised for an invalid conversation participant/action; routes catch
    this and turn it into the app's standard 400 shape."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def can_message(actor_role, actor_id, recipient):
    """Server-side authorization for who may start a conversation with
    whom — the actual enforcement point, never trusted from the client.

    - A volunteer may only message admin/staff (never another volunteer
      — this app has no policy allowing volunteer-to-volunteer contact).
    - A family/caregiver account is restricted the same way a volunteer
      is: admin/staff only, never another family account, never a
      volunteer directly (see Phase 8 — "do not automatically allow
      Family <-> Volunteer unless organization policy explicitly
      requires it," which it doesn't here).
    - Admin/staff may message any volunteer or family account
      (deliberately not Verified-only / consent-gated here — starting a
      conversation isn't itself sensitive; what a family account can
      actually see through the family portal endpoints is where the
      real consent/relationship gate lives) or any other admin/staff
      member for internal coordination.
    - Nobody may message themselves."""
    if recipient is None or recipient.id == actor_id:
        return False
    if actor_role in ("volunteer", "family"):
        return recipient.role in ("admin", "staff")
    return recipient.role in ("admin", "staff", "volunteer", "family")


def list_recipients(actor_role, actor_id):
    """The bounded set of people `actor` is allowed to start a
    conversation with — never a general user directory. A volunteer or
    family account only ever sees admin/staff names; admin/staff see
    every volunteer/family account plus each other."""
    if actor_role in ("volunteer", "family"):
        people = User.query.filter(User.role.in_(("admin", "staff"))).order_by(User.name.asc()).all()
    else:
        people = User.query.filter(User.id != actor_id).order_by(User.name.asc()).all()
    return people


def get_or_create_conversation(user_a_id, user_b_id, elderly_member_id=None):
    """elderly_member_id is only ever set on a NEW conversation, from an
    already-authorized family request (see messaging/routes.py) — never
    trusted or re-applied to an existing conversation, so an existing
    thread's tagged member can't be changed by simply "starting" it
    again with a different member_id."""
    existing = Conversation.query.filter(
        db.or_(
            db.and_(Conversation.user_one_id == user_a_id, Conversation.user_two_id == user_b_id),
            db.and_(Conversation.user_one_id == user_b_id, Conversation.user_two_id == user_a_id),
        )
    ).first()
    if existing:
        return existing
    conversation = Conversation(user_one_id=user_a_id, user_two_id=user_b_id, elderly_member_id=elderly_member_id)
    db.session.add(conversation)
    db.session.flush()
    return conversation


def send_direct_message(conversation, sender_id, body):
    now = utcnow()
    message = DirectMessage(conversation_id=conversation.id, sender_id=sender_id, body=body, created_at=now)
    db.session.add(message)
    conversation.last_message_at = now
    # The sender has, by definition, "read" their own message — this
    # keeps their own unread count from counting a message they just sent.
    conversation.set_read_at_for(sender_id, now)
    db.session.flush()
    return message


def participant_conversation_or_none(conversation_id, user_id):
    """Scoped to the caller's own participation at the query level — a
    conversation that exists but isn't theirs looks identical to one that
    doesn't exist at all. Same "don't confirm existence of what you can't
    access" shape as notifications/routes.py's _own_notification_or_none,
    the direct defense against conversation-id enumeration/IDOR."""
    conversation = db.session.get(Conversation, conversation_id)
    if conversation is None or not conversation.is_participant(user_id):
        return None
    return conversation


def _conversation_order_key(conversation):
    return conversation.last_message_at or conversation.created_at


def list_conversations_for_user(user_id):
    conversations = Conversation.query.filter(
        db.or_(Conversation.user_one_id == user_id, Conversation.user_two_id == user_id)
    ).all()
    conversations.sort(key=_conversation_order_key, reverse=True)

    result = []
    for c in conversations:
        other = c.other_user(user_id)
        read_at = c.read_at_for(user_id)
        last = DirectMessage.query.filter_by(conversation_id=c.id).order_by(DirectMessage.created_at.desc()).first()
        unread = 0
        if last is not None:
            unread_q = DirectMessage.query.filter(DirectMessage.conversation_id == c.id, DirectMessage.sender_id != user_id)
            if read_at is not None:
                unread_q = unread_q.filter(DirectMessage.created_at > read_at)
            unread = unread_q.count()
        result.append({
            "id": c.id,
            "other_user": {"id": other.id, "name": other.name, "role": other.role},
            "last_message": last.to_dict() if last else None,
            "unread_count": unread,
            "updated_at": _conversation_order_key(c).isoformat(),
        })
    return result


def unread_message_count(user_id):
    """One cheap total for a nav badge — not the per-conversation detail
    list_conversations_for_user builds; a user with many conversations
    shouldn't pay for a full list scan just to render a badge number."""
    total = 0
    conversations = Conversation.query.filter(
        db.or_(Conversation.user_one_id == user_id, Conversation.user_two_id == user_id)
    ).all()
    for c in conversations:
        read_at = c.read_at_for(user_id)
        q = DirectMessage.query.filter(DirectMessage.conversation_id == c.id, DirectMessage.sender_id != user_id)
        if read_at is not None:
            q = q.filter(DirectMessage.created_at > read_at)
        total += q.count()
    return total


def list_unresolved_conversations():
    """A conversation is unresolved if its latest message was sent by the
    volunteer participant and no admin/staff reply has followed yet.
    Only meaningful for conversations that actually pair a volunteer with
    an admin/staff member (the only paths this feature targets) — a
    staff-to-staff conversation is never "unresolved" in this sense.
    Derived entirely from existing rows, nothing stored."""
    conversations = Conversation.query.filter(Conversation.last_message_at.isnot(None)).all()
    now = utcnow()
    unresolved = []
    for c in conversations:
        u1, u2 = c.user_one, c.user_two
        if u1.role == "volunteer" and u2.role in ("admin", "staff"):
            volunteer, staff = u1, u2
        elif u2.role == "volunteer" and u1.role in ("admin", "staff"):
            volunteer, staff = u2, u1
        else:
            continue
        last = DirectMessage.query.filter_by(conversation_id=c.id).order_by(DirectMessage.created_at.desc()).first()
        if last is not None and last.sender_id == volunteer.id:
            waiting_hours = (_as_naive_utc(now) - _as_naive_utc(last.created_at)).total_seconds() / 3600
            unresolved.append({
                "conversation_id": c.id,
                "volunteer": {"id": volunteer.id, "name": volunteer.name},
                "staff": {"id": staff.id, "name": staff.name},
                "last_message": last.to_dict(),
                "waiting_hours": round(waiting_hours, 1),
            })
    unresolved.sort(key=lambda x: x["last_message"]["created_at"])
    return unresolved


_ASSIGNMENT_MODELS = {"home_visit": HomeVisit, "assistance_request": AssistanceRequest}


def list_assignment_conversations():
    """Read-only summary of every assignment-scoped thread that has at
    least one message, for the admin/staff "Modern Inbox" to surface
    alongside direct conversations — without touching AssignmentMessage's
    own access rules or storage at all. Each assignment still has at most
    one thread (assignment_type, assignment_id), same as today; this just
    lists them instead of requiring staff to open each visit/request one
    at a time to discover which ones have messages."""
    rows = (
        db.session.query(
            AssignmentMessage.assignment_type,
            AssignmentMessage.assignment_id,
            db.func.max(AssignmentMessage.created_at).label("last_at"),
        )
        .group_by(AssignmentMessage.assignment_type, AssignmentMessage.assignment_id)
        .all()
    )
    result = []
    for assignment_type, assignment_id, last_at in rows:
        model = _ASSIGNMENT_MODELS.get(assignment_type)
        if model is None:
            continue
        assignment = db.session.get(model, assignment_id)
        if assignment is None:
            continue
        last_message = (
            AssignmentMessage.query.filter_by(assignment_type=assignment_type, assignment_id=assignment_id)
            .order_by(AssignmentMessage.created_at.desc())
            .first()
        )
        result.append({
            "kind": assignment_type,
            "id": assignment.id,
            "elderly_member_name": assignment.elderly_member.full_name,
            "assigned_to": assignment.assigned_to.name if assignment.assigned_to else None,
            "status": assignment.status,
            "last_message": last_message.to_dict() if last_message else None,
            "updated_at": last_at.isoformat(),
        })
    result.sort(key=lambda x: x["updated_at"], reverse=True)
    return result
