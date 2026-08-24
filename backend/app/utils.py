import csv
import io

from flask import abort, jsonify, Response

from .extensions import db


def get_or_404(model, obj_id):
    obj = db.session.get(model, obj_id)
    if obj is None:
        abort(404, description=f"{model.__name__} not found")
    return obj


def validation_error_response(err):
    return jsonify(error="Validation failed", details=err.messages), 400


def csv_response(filename, headers, rows):
    """Build a proper CSV download response. Python's csv module handles
    quoting/escaping (embedded commas, quotes, newlines) automatically."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
