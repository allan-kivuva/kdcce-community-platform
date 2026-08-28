import os
import uuid

from flask import current_app

from ..extensions import db
from ..models import AssignmentAttachment, AssignmentChecklistItem, AssignmentMessage, AssignmentReview, utcnow

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB — the actual application-level limit;
# config.py's MAX_CONTENT_LENGTH is a slightly higher hard backstop enforced
# before the request body is even parsed.


class AttachmentError(Exception):
    """Raised on a rejected upload (missing, wrong type, or too large).
    Routes catch this and turn it into the app's standard 400 shape, same
    pattern as ReportFilterError in utils.py."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _sniff_image_type(header):
    """Identify the file from its own bytes, never from the client's
    filename or Content-Type header — both are attacker-controlled and
    trivially spoofable. Only the three formats this app accepts."""
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None, None


def _upload_dir():
    # Under instance/, never app/static/ — nothing serves this path
    # publicly. Same instance-folder convention already used for the
    # SQLite file (see create_app's os.makedirs(app.instance_path, ...)).
    path = os.path.join(current_app.instance_path, "uploads", "assignment_photos")
    os.makedirs(path, exist_ok=True)
    return path


def _file_path(storage_key):
    return os.path.join(_upload_dir(), storage_key)


def save_photo(assignment_type, assignment_id, uploaded_by_id, file_storage):
    """The single chokepoint every assignment-photo upload route calls.
    Validates the file's actual content, writes it to disk under a
    server-generated name (never the client's filename), and creates (or
    replaces — at most one photo per assignment) the AssignmentAttachment
    row. Does not commit; the caller's route does, same as every other
    write in this app."""
    if file_storage is None or not file_storage.filename:
        raise AttachmentError("No file provided")

    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    mime_type, extension = _sniff_image_type(header)
    if mime_type is None:
        raise AttachmentError("File must be a JPEG, PNG, or WebP image")

    data = file_storage.stream.read(MAX_PHOTO_SIZE + 1)
    if len(data) > MAX_PHOTO_SIZE:
        raise AttachmentError("File exceeds the 5MB limit")

    existing = AssignmentAttachment.query.filter_by(assignment_type=assignment_type, assignment_id=assignment_id).first()
    if existing is not None:
        _delete_file_if_present(existing.storage_key)
        db.session.delete(existing)
        db.session.flush()

    storage_key = f"{uuid.uuid4().hex}.{extension}"
    with open(_file_path(storage_key), "wb") as f:
        f.write(data)

    attachment = AssignmentAttachment(
        assignment_type=assignment_type,
        assignment_id=assignment_id,
        uploaded_by_id=uploaded_by_id,
        storage_key=storage_key,
        original_filename=file_storage.filename[:255],
        mime_type=mime_type,
        file_size=len(data),
    )
    db.session.add(attachment)
    db.session.flush()
    return attachment


def get_attachment(assignment_type, assignment_id):
    return AssignmentAttachment.query.filter_by(assignment_type=assignment_type, assignment_id=assignment_id).first()


def attachment_file_path(attachment):
    return _file_path(attachment.storage_key)


def _delete_file_if_present(storage_key):
    path = _file_path(storage_key)
    if os.path.exists(path):
        os.remove(path)


# ---------- Private assignment messages ----------
# Deliberately NOT the Phase 7D Inbox (InboxMessage) — that's a shared,
# ownerless mailbox for anonymous public contact-form submissions, with no
# sender, no thread, and no link to any resource. This is the opposite: a
# private, per-assignment, two-way thread between exactly one volunteer and
# staff. Reusing InboxMessage would mean bolting an unrelated shape onto a
# table already doing its own job.

def list_messages(assignment_type, assignment_id):
    return (
        AssignmentMessage.query.filter_by(assignment_type=assignment_type, assignment_id=assignment_id)
        .order_by(AssignmentMessage.created_at.asc())
        .all()
    )


def send_message(assignment_type, assignment_id, sender_id, body):
    message = AssignmentMessage(assignment_type=assignment_type, assignment_id=assignment_id, sender_id=sender_id, body=body)
    db.session.add(message)
    db.session.flush()
    return message


# ---------- Admin review (star rating + comment) ----------
# At most one review per assignment — same "create or replace" behavior
# as the photo above, not a review history.

def get_review(assignment_type, assignment_id):
    return AssignmentReview.query.filter_by(assignment_type=assignment_type, assignment_id=assignment_id).first()


def submit_review(assignment_type, assignment_id, reviewed_by_id, rating, comment):
    review = get_review(assignment_type, assignment_id)
    if review is None:
        review = AssignmentReview(assignment_type=assignment_type, assignment_id=assignment_id, reviewed_by_id=reviewed_by_id)
        db.session.add(review)
    review.rating = rating
    review.comment = comment
    review.reviewed_by_id = reviewed_by_id
    db.session.flush()
    return review


# ---------- Assignment checklist ----------
# Fixed, code-defined item sets — not user-editable, and deliberately only
# defined for assignment types where a checklist makes sense (home visits).
# An assistance_request has no entry here on purpose: "do not create
# unnecessary checklists for every assignment type."

CHECKLIST_DEFINITIONS = {
    "home_visit": (
        ("wellbeing", "Checked general wellbeing"),
        ("basic_needs", "Confirmed basic needs"),
        ("concerns", "Discussed concerns"),
        ("follow_up_check", "Checked whether follow-up is required"),
        ("visit_notes", "Completed visit notes"),
    ),
}


class ChecklistError(Exception):
    """Raised for an assignment type with no checklist, or an unknown item
    key — routes catch this and turn it into the app's standard 400 shape."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def get_checklist(assignment_type, assignment_id):
    """Always returns the full, fixed item list for this assignment type —
    merging any existing rows over the code-defined defaults — never just
    whatever happens to have a DB row yet."""
    definition = CHECKLIST_DEFINITIONS.get(assignment_type)
    if definition is None:
        return []
    existing = {
        row.item_key: row
        for row in AssignmentChecklistItem.query.filter_by(assignment_type=assignment_type, assignment_id=assignment_id).all()
    }
    items = []
    for key, label in definition:
        row = existing.get(key)
        items.append({
            "item_key": key,
            "label": label,
            "checked": row.checked if row else False,
            "checked_at": row.checked_at.isoformat() if row and row.checked_at else None,
            "checked_by": row.checked_by.name if row and row.checked_by else None,
        })
    return items


def set_checklist_item(assignment_type, assignment_id, item_key, checked, checked_by_id):
    definition = CHECKLIST_DEFINITIONS.get(assignment_type)
    if definition is None:
        raise ChecklistError("This assignment type has no checklist")
    if item_key not in dict(definition):
        raise ChecklistError("Unknown checklist item")

    row = AssignmentChecklistItem.query.filter_by(
        assignment_type=assignment_type, assignment_id=assignment_id, item_key=item_key
    ).first()
    if row is None:
        row = AssignmentChecklistItem(assignment_type=assignment_type, assignment_id=assignment_id, item_key=item_key)
        db.session.add(row)
    row.checked = checked
    row.checked_at = utcnow() if checked else None
    row.checked_by_id = checked_by_id if checked else None
    db.session.flush()
    return row
