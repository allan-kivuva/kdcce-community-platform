import csv
import io
from datetime import date

from flask import abort, jsonify, Response

from .extensions import db


def get_or_404(model, obj_id):
    obj = db.session.get(model, obj_id)
    if obj is None:
        abort(404, description=f"{model.__name__} not found")
    return obj


class ReportFilterError(Exception):
    """Raised by parse_date_range on a malformed date filter; routes catch
    this and turn it into the app's standard 400 validation shape."""

    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(message)


def parse_date_range(args):
    """Parse optional date_from/date_to=YYYY-MM-DD query params, shared by
    every report endpoint so the same "bad date" error shape and the
    from-must-not-be-after-to check aren't reimplemented per report."""
    parsed = {}
    for key in ("date_from", "date_to"):
        raw = args.get(key)
        if not raw:
            parsed[key] = None
            continue
        try:
            parsed[key] = date.fromisoformat(raw)
        except ValueError:
            raise ReportFilterError(key, "Must be YYYY-MM-DD")
    if parsed["date_from"] and parsed["date_to"] and parsed["date_from"] > parsed["date_to"]:
        raise ReportFilterError("date_to", "Must not be before date_from")
    return parsed["date_from"], parsed["date_to"]


def validation_error_response(err):
    return jsonify(error="Validation failed", details=err.messages), 400


_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize_csv_cell(value):
    """A cell whose text starts with =, +, -, or @ is interpreted as a
    formula by Excel/Sheets/LibreOffice when the file is opened — since
    several of this app's CSV exports include user-entered free text
    (names, notes, reasons, imported rows), prefixing a leading `'`
    neutralizes that without changing what a human sees (spreadsheet
    apps hide a leading apostrophe on a text cell). Only applied to
    strings; numbers/None/etc. pass through untouched."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def csv_response(filename, headers, rows):
    """Build a proper CSV download response. Python's csv module handles
    quoting/escaping (embedded commas, quotes, newlines) automatically;
    _sanitize_csv_cell additionally guards every exported cell (headers
    included, since a CSV import's own column headers are also
    attacker-controlled input) against spreadsheet formula injection."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([_sanitize_csv_cell(h) for h in headers])
    writer.writerows([_sanitize_csv_cell(cell) for cell in row] for row in rows)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
