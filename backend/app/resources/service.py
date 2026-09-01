from ..documents.service import DocumentError, save_document  # noqa: F401 -- re-exported for routes.py
from ..extensions import db
from ..models import Activity, Document, Program


class ResourceError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


def resolve_owner(program_id, activity_id, uploaded_by_id):
    """A resource belongs to exactly one of: a specific Activity, a
    Program (not tied to one particular activity), or nothing in
    particular ("general" — owner_id falls back to the uploader, which
    is always a valid, non-null id, since owner_id is NOT NULL on
    Document). Reuses Document's existing owner_type/owner_id pointer —
    that field was deliberately designed in Phase 3 to support exactly
    this kind of future reuse without a schema change."""
    if program_id is not None and activity_id is not None:
        raise ResourceError("A resource can be tied to a program or an activity, not both")
    if activity_id is not None:
        if db.session.get(Activity, activity_id) is None:
            raise ResourceError("Activity not found")
        return "activity", activity_id
    if program_id is not None:
        if db.session.get(Program, program_id) is None:
            raise ResourceError("Program not found")
        return "program", program_id
    return "general", uploaded_by_id


def list_resources(role, program_id=None, activity_id=None, category=None):
    query = Document.query.filter(Document.visibility.isnot(None))
    if role not in ("admin", "staff"):
        query = query.filter(Document.visibility == "Volunteers")
    if program_id is not None:
        query = query.filter(Document.owner_type == "program", Document.owner_id == program_id)
    if activity_id is not None:
        query = query.filter(Document.owner_type == "activity", Document.owner_id == activity_id)
    if category:
        query = query.filter(Document.document_type == category)
    return query.order_by(Document.created_at.desc()).all()


def can_view_resource(document, role):
    if document.visibility is None:
        return False  # a volunteer-document row, never a resource
    if role in ("admin", "staff"):
        return True
    return document.visibility == "Volunteers"
