"""CSV import — untrusted input. Every file is: decoded strictly as
UTF-8 (rejecting anything else outright, rather than guessing an
encoding), parsed with the stdlib csv module (never eval'd/executed),
capped at MAX_ROWS data rows, and validated row-by-row through the
SAME marshmallow schema each entity's own create endpoint already
uses — so an imported row can never be more permissive than a row
entered by hand through the UI. Nothing is ever written to the
database on a preview call; a commit call re-parses and re-validates
the file from scratch (never trusts a client-echoed "already
validated" flag) and only inserts rows with zero validation errors,
skipping the rest."""

import csv
import io

from marshmallow import ValidationError

from ..elderly.routes import _make_member_id
from ..elderly.schemas import ElderlyMemberSchema
from ..extensions import db
from ..inventory.schemas import InventoryItemSchema
from ..models import OPA, ElderlyMember, InventoryItem, Program, User
from ..programs.schemas import ProgramCreateSchema

MAX_ROWS = 500
MAX_FILE_BYTES = 2 * 1024 * 1024
ENTITIES = ("elderly_members", "inventory_items", "programs")


class ImportError_(Exception):
    """Raised for a whole-file problem (bad encoding, too many rows, too
    large) — distinct from a per-row validation error, which is
    collected and returned instead of raised."""


def _read_rows(file_storage):
    raw = file_storage.read()
    if len(raw) > MAX_FILE_BYTES:
        raise ImportError_(f"File is too large — the limit is {MAX_FILE_BYTES // (1024 * 1024)}MB.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportError_("File must be UTF-8 encoded CSV.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ImportError_("File has no header row.")
    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ImportError_(f"Too many rows — the limit is {MAX_ROWS} per import.")
    return rows


def _clean_row(row):
    """Empty-string CSV cells should mean "not provided", same as an
    omitted JSON field would for these schemas' load_default handling —
    which means dropping the key entirely, not mapping it to None. A
    field that's genuinely allow_none=True (e.g. date_of_birth) already
    has its own explicit load_default=None in the schema, so omitting
    an empty cell behaves identically for those; for a field that is
    NOT allow_none (e.g. InventoryItemSchema.category,
    ProgramCreateSchema.status), keeping the key with a None value
    would incorrectly fail validation instead of falling back to that
    field's load_default — see the Phase 8 report for how this was
    caught."""
    cleaned = {}
    for key, value in row.items():
        if isinstance(value, str) and value.strip() != "":
            cleaned[key] = value.strip()
    return cleaned


# ---------- elderly_members ----------

def _validate_elderly_row(row_number, raw_row):
    schema = ElderlyMemberSchema()
    data = _clean_row(raw_row)
    errors = {}
    try:
        loaded = schema.load(data)
    except ValidationError as err:
        errors.update(err.messages)
        loaded = None

    if loaded and loaded.get("opa_id") is not None and db.session.get(OPA, loaded["opa_id"]) is None:
        errors.setdefault("opa_id", []).append("OPA not found")

    is_duplicate = False
    if loaded and not errors:
        is_duplicate = ElderlyMember.query.filter_by(
            full_name=loaded["full_name"], date_of_birth=loaded.get("date_of_birth"),
        ).first() is not None

    return {"row_number": row_number, "data": data, "errors": errors, "is_duplicate": is_duplicate}


def _commit_elderly_row(validated, actor_id):
    data = ElderlyMemberSchema().load(validated["data"])
    member = ElderlyMember(**data, member_id="")
    db.session.add(member)
    db.session.flush()
    member.member_id = _make_member_id(member)
    return member


# ---------- inventory_items ----------

def _validate_inventory_row(row_number, raw_row):
    schema = InventoryItemSchema()
    data = _clean_row(raw_row)
    data.setdefault("category", "Other")
    data.setdefault("minimum_stock", "0")
    errors = {}
    try:
        loaded = schema.load(data)
    except ValidationError as err:
        errors.update(err.messages)
        loaded = None

    is_duplicate = False
    if loaded and not errors:
        is_duplicate = InventoryItem.query.filter_by(name=loaded["name"]).first() is not None

    return {"row_number": row_number, "data": data, "errors": errors, "is_duplicate": is_duplicate}


def _commit_inventory_row(validated, actor_id):
    data = InventoryItemSchema().load(validated["data"])
    item = InventoryItem(**data, current_stock=0)
    db.session.add(item)
    return item


# ---------- programs ----------

def _validate_program_row(row_number, raw_row):
    schema = ProgramCreateSchema()
    data = _clean_row(raw_row)
    errors = {}
    try:
        loaded = schema.load(data)
    except ValidationError as err:
        errors.update(err.messages)
        loaded = None

    # Same rule the real POST /api/programs enforces (see
    # programs/routes.py:_coordinator_or_400) — an imported row must
    # never be more permissive than one entered by hand.
    if loaded and loaded.get("coordinator_id") is not None:
        coordinator = db.session.get(User, loaded["coordinator_id"])
        if coordinator is None or coordinator.role not in ("admin", "staff"):
            errors.setdefault("coordinator_id", []).append("Must be an existing staff or admin user")

    is_duplicate = False
    if loaded and not errors:
        is_duplicate = Program.query.filter_by(name=loaded["name"]).first() is not None

    return {"row_number": row_number, "data": data, "errors": errors, "is_duplicate": is_duplicate}


def _commit_program_row(validated, actor_id):
    data = ProgramCreateSchema().load(validated["data"])
    program = Program(**data)
    db.session.add(program)
    return program


_VALIDATORS = {
    "elderly_members": _validate_elderly_row,
    "inventory_items": _validate_inventory_row,
    "programs": _validate_program_row,
}
_COMMITTERS = {
    "elderly_members": _commit_elderly_row,
    "inventory_items": _commit_inventory_row,
    "programs": _commit_program_row,
}


def preview(entity, file_storage):
    """Never writes to the database. Duplicates are flagged, not
    rejected — an admin may legitimately want to re-import an update
    later via a different flow; this phase only ever inserts."""
    rows = _read_rows(file_storage)
    validator = _VALIDATORS[entity]
    results = [validator(i + 2, row) for i, row in enumerate(rows)]  # +2: header is row 1, data starts at row 2
    valid_count = sum(1 for r in results if not r["errors"] and not r["is_duplicate"])
    error_count = sum(1 for r in results if r["errors"])
    duplicate_count = sum(1 for r in results if r["is_duplicate"] and not r["errors"])
    return {"rows": results, "total": len(results), "valid_count": valid_count, "error_count": error_count, "duplicate_count": duplicate_count}


def commit(entity, file_storage, actor_id):
    """Re-parses and re-validates from scratch — never trusts anything
    the client echoes back as "already checked". Inserts only rows with
    zero errors and no duplicate match; every skipped row is reported
    back with its reason, never silently dropped. Validated and
    committed one row at a time (with a flush after each insert) rather
    than as one pre-computed batch, so two duplicate rows within the
    SAME file are also caught — the second sees the first's flushed
    row, not just pre-existing database records."""
    rows = _read_rows(file_storage)
    validator = _VALIDATORS[entity]
    committer = _COMMITTERS[entity]

    created_count = 0
    skipped = []
    for i, raw_row in enumerate(rows):
        validated = validator(i + 2, raw_row)
        if validated["errors"]:
            skipped.append({"row_number": validated["row_number"], "reason": "validation_error", "errors": validated["errors"]})
            continue
        if validated["is_duplicate"]:
            skipped.append({"row_number": validated["row_number"], "reason": "duplicate"})
            continue
        committer(validated, actor_id)
        db.session.flush()
        created_count += 1

    return {"created_count": created_count, "skipped": skipped, "total": len(rows)}
