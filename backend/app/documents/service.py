import os
import uuid

from flask import current_app

from ..extensions import db
from ..models import Document, utcnow

# Same 5MB ceiling as assignment photos (assignments/service.py) for
# images; a document may also be a PDF, which gets its own, slightly
# higher ceiling (agreements/certificates scanned as PDF commonly run
# larger than a single photo) — still well under config.py's
# MAX_CONTENT_LENGTH hard backstop either way.
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_PDF_SIZE = 10 * 1024 * 1024


class DocumentError(Exception):
    """Same role as AttachmentError in assignments/service.py — routes
    catch this and turn it into the app's standard 400 shape."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _sniff_file_type(header):
    """Identical technique to assignments/service.py's _sniff_image_type
    — identify the file from its own bytes, never the client's filename
    or Content-Type, both trivially spoofable — extended to also accept
    PDF (%PDF magic bytes), since agreements/certificates are commonly
    PDFs, not photos."""
    if header[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg", MAX_IMAGE_SIZE
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png", MAX_IMAGE_SIZE
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp", "webp", MAX_IMAGE_SIZE
    if header[:4] == b"%PDF":
        return "application/pdf", "pdf", MAX_PDF_SIZE
    return None, None, None


def _upload_dir():
    # Same instance/ convention as assignment photos — never app/static/.
    path = os.path.join(current_app.instance_path, "uploads", "documents")
    os.makedirs(path, exist_ok=True)
    return path


def _file_path(storage_key):
    return os.path.join(_upload_dir(), storage_key)


def save_document(
    owner_type, owner_id, uploaded_by_id, file_storage, document_type, title,
    issue_date=None, expiry_date=None, description=None, visibility=None, auto_verified=False,
):
    """Validates and stores a new document — unlike assignment photos,
    multiple documents can exist per owner (a volunteer has many
    documents), so this always creates a new row rather than
    replacing an existing one. Does not commit; caller's route does.

    `description`/`visibility`/`auto_verified` exist for the Phase 5
    resource library (see resources/service.py), which reuses this exact
    function and the Document table rather than a second file-storage
    system — a volunteer's own document upload never passes them.
    `auto_verified=True` skips the Pending-review workflow: a resource
    uploaded by admin/staff is already authoritative the moment it's
    uploaded, there is no separate reviewer step the way an ID/
    certificate a volunteer submits needs one."""
    if file_storage is None or not file_storage.filename:
        raise DocumentError("No file provided")

    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    mime_type, extension, size_limit = _sniff_file_type(header)
    if mime_type is None:
        raise DocumentError("File must be a JPEG, PNG, WebP image, or PDF")

    data = file_storage.stream.read(size_limit + 1)
    if len(data) > size_limit:
        raise DocumentError(f"File exceeds the {size_limit // (1024 * 1024)}MB limit")

    storage_key = f"{uuid.uuid4().hex}.{extension}"
    with open(_file_path(storage_key), "wb") as f:
        f.write(data)

    document = Document(
        owner_type=owner_type,
        owner_id=owner_id,
        uploaded_by_id=uploaded_by_id,
        document_type=document_type,
        title=title,
        description=description,
        visibility=visibility,
        storage_key=storage_key,
        original_filename=file_storage.filename[:255],
        mime_type=mime_type,
        size_bytes=len(data),
        issue_date=issue_date,
        expiry_date=expiry_date,
        status="Verified" if auto_verified else "Pending",
        reviewed_by_id=uploaded_by_id if auto_verified else None,
        reviewed_at=utcnow() if auto_verified else None,
    )
    db.session.add(document)
    db.session.flush()
    return document


def document_file_path(document):
    return _file_path(document.storage_key)


def delete_document_file(document):
    path = _file_path(document.storage_key)
    if os.path.exists(path):
        os.remove(path)
