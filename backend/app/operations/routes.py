from flask import Blueprint, jsonify, request

from ..auth.decorators import roles_required
from ..utils import ReportFilterError, parse_date_range
from . import service

bp = Blueprint("operations", __name__, url_prefix="/api/operations")


@bp.get("/map")
@roles_required("admin", "staff")
def operations_map():
    """Admin/staff only — never reachable by volunteer or family accounts
    (see roles_required above; also explicitly tested). Returns only
    geocoded points and only the fields a map popover needs — see
    operations/service.py's module docstring for exactly what's
    deliberately excluded."""
    requested_layers = request.args.get("layers")
    layers = [l.strip() for l in requested_layers.split(",")] if requested_layers else list(service.LAYERS)
    unknown = [l for l in layers if l not in service.LAYERS]
    if unknown:
        return jsonify(error="Validation failed", details={"layers": [f"Unknown layer(s): {', '.join(unknown)}"]}), 400

    status = request.args.get("status")
    try:
        date_from, date_to = parse_date_range(request.args)
    except ReportFilterError as err:
        return jsonify(error="Validation failed", details={err.field: [err.message]}), 400

    points = service.get_map_points(layers, status=status, date_from=date_from, date_to=date_to)
    return jsonify(points=points, layers=layers), 200
