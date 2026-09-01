import csv
import io
import json

from app.models import AuditLog, ElderlyMember, InventoryItem, Program

# Each entity's minimal CSV shape — deliberately using only the columns
# needed to exercise required fields plus the one used for duplicate
# detection (full_name for elderly_members, name for the other two).
MODEL_MAP = {"elderly_members": ElderlyMember, "inventory_items": InventoryItem, "programs": Program}
LIST_ENDPOINT = {"elderly_members": ("/api/elderly", "members"), "inventory_items": ("/api/inventory", "items"), "programs": ("/api/programs", "programs")}
HEADER = {"elderly_members": ["full_name", "gender"], "inventory_items": ["name", "unit"], "programs": ["name"]}


def _good_row(entity, label):
    if entity == "elderly_members":
        return [label, "Female"]
    if entity == "inventory_items":
        return [label, "kg"]
    return [label]


def _bad_row(entity):
    # Blank the entity's one required, non-defaulted text field.
    if entity == "elderly_members":
        return ["", "Female"]
    if entity == "inventory_items":
        return ["", "kg"]
    return [""]


def _csv_bytes(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def _upload(client, token, auth_header, entity, action, csv_bytes, filename="import.csv"):
    return client.post(
        f"/api/imports/{entity}/{action}",
        data={"file": (io.BytesIO(csv_bytes), filename)},
        content_type="multipart/form-data",
        headers=auth_header(token),
    )


ENTITIES = ("elderly_members", "inventory_items", "programs")


# ---------- Preview never writes ----------

def test_preview_valid_csv_reports_valid_count_and_writes_nothing(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for entity in ENTITIES:
        before = MODEL_MAP[entity].query.count()
        rows = [_good_row(entity, f"{entity} A"), _good_row(entity, f"{entity} B"), _good_row(entity, f"{entity} C")]
        resp = _upload(client, token, auth_header, entity, "preview", _csv_bytes(HEADER[entity], rows))
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body["valid_count"] == 3
        assert body["error_count"] == 0
        assert body["total"] == 3
        assert MODEL_MAP[entity].query.count() == before  # preview never writes


# ---------- Commit creates rows ----------

def test_commit_valid_csv_creates_rows(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for entity in ENTITIES:
        rows = [_good_row(entity, f"{entity} commit A"), _good_row(entity, f"{entity} commit B")]
        resp = _upload(client, token, auth_header, entity, "commit", _csv_bytes(HEADER[entity], rows))
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body["created_count"] == 2
        assert body["skipped"] == []

        endpoint, key = LIST_ENDPOINT[entity]
        listed = client.get(endpoint, headers=auth_header(token)).get_json()[key]
        names_field = "full_name" if entity == "elderly_members" else "name"
        names = {item[names_field] for item in listed}
        assert f"{entity} commit A" in names
        assert f"{entity} commit B" in names


# ---------- Malformed rows ----------

def test_preview_reports_row_level_errors_for_malformed_rows(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for entity in ENTITIES:
        rows = [_good_row(entity, f"{entity} good1"), _good_row(entity, f"{entity} good2"), _bad_row(entity)]
        resp = _upload(client, token, auth_header, entity, "preview", _csv_bytes(HEADER[entity], rows))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid_count"] == 2
        assert body["error_count"] == 1
        bad = [r for r in body["rows"] if r["errors"]]
        assert len(bad) == 1


def test_commit_creates_only_valid_rows_and_reports_skipped_validation_error(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for entity in ENTITIES:
        before = MODEL_MAP[entity].query.count()
        rows = [_good_row(entity, f"{entity} mixgood1"), _good_row(entity, f"{entity} mixgood2"), _bad_row(entity)]
        resp = _upload(client, token, auth_header, entity, "commit", _csv_bytes(HEADER[entity], rows))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["created_count"] == 2
        assert MODEL_MAP[entity].query.count() == before + 2
        assert len(body["skipped"]) == 1
        assert body["skipped"][0]["reason"] == "validation_error"
        assert body["skipped"][0]["row_number"] == 4  # header=1, rows start at 2


# ---------- Duplicate detection ----------

def test_second_commit_of_same_row_is_skipped_as_duplicate(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for entity in ENTITIES:
        before = MODEL_MAP[entity].query.count()
        row = _good_row(entity, f"{entity} dup subject")
        csv_bytes = _csv_bytes(HEADER[entity], [row])

        first = _upload(client, token, auth_header, entity, "commit", csv_bytes)
        assert first.get_json()["created_count"] == 1

        preview_again = _upload(client, token, auth_header, entity, "preview", csv_bytes)
        preview_body = preview_again.get_json()
        assert preview_body["valid_count"] == 0
        assert preview_body["duplicate_count"] == 1

        second = _upload(client, token, auth_header, entity, "commit", csv_bytes)
        second_body = second.get_json()
        assert second_body["created_count"] == 0
        assert len(second_body["skipped"]) == 1
        assert second_body["skipped"][0]["reason"] == "duplicate"

        # Only ONE row exists — the duplicate commit did not create a second.
        assert MODEL_MAP[entity].query.count() == before + 1


# ---------- MAX_ROWS enforcement ----------

def test_csv_exceeding_max_rows_is_rejected_before_any_row_processed(client, make_staff_user, auth_header, monkeypatch):
    monkeypatch.setattr("app.imports.service.MAX_ROWS", 3)
    _, token = make_staff_user("admin")
    entity = "elderly_members"
    before = ElderlyMember.query.count()
    rows = [_good_row(entity, f"Overflow {i}") for i in range(4)]  # 4 > MAX_ROWS(3)
    csv_bytes = _csv_bytes(HEADER[entity], rows)

    preview_resp = _upload(client, token, auth_header, entity, "preview", csv_bytes)
    assert preview_resp.status_code == 400
    assert ElderlyMember.query.count() == before

    commit_resp = _upload(client, token, auth_header, entity, "commit", csv_bytes)
    assert commit_resp.status_code == 400
    assert ElderlyMember.query.count() == before


# ---------- Access control ----------

def test_volunteer_forbidden_on_preview_and_commit(client, make_user, auth_header):
    _, access_token, _ = make_user()
    for entity in ENTITIES:
        csv_bytes = _csv_bytes(HEADER[entity], [_good_row(entity, "x")])
        preview_resp = _upload(client, access_token, auth_header, entity, "preview", csv_bytes)
        assert preview_resp.status_code == 403
        commit_resp = _upload(client, access_token, auth_header, entity, "commit", csv_bytes)
        assert commit_resp.status_code == 403


def test_unauthenticated_gets_401(client):
    for entity in ENTITIES:
        csv_bytes = _csv_bytes(HEADER[entity], [_good_row(entity, "x")])
        preview_resp = client.post(
            f"/api/imports/{entity}/preview", data={"file": (io.BytesIO(csv_bytes), "f.csv")}, content_type="multipart/form-data",
        )
        assert preview_resp.status_code == 401
        commit_resp = client.post(
            f"/api/imports/{entity}/commit", data={"file": (io.BytesIO(csv_bytes), "f.csv")}, content_type="multipart/form-data",
        )
        assert commit_resp.status_code == 401


# ---------- Formula injection is an export-time concern, not import-time ----------

def test_formula_like_text_is_imported_as_plain_text_unchanged(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    formula_name = "=SUM(A1:A9)"

    for entity in ENTITIES:
        row = _good_row(entity, formula_name)
        resp = _upload(client, token, auth_header, entity, "commit", _csv_bytes(HEADER[entity], [row]))
        assert resp.status_code == 200
        assert resp.get_json()["created_count"] == 1

        endpoint, key = LIST_ENDPOINT[entity]
        listed = client.get(endpoint, headers=auth_header(token)).get_json()[key]
        names_field = "full_name" if entity == "elderly_members" else "name"
        matches = [item for item in listed if item[names_field] == formula_name]
        assert len(matches) == 1  # stored verbatim, no leading apostrophe, no rejection


# ---------- Audit logging ----------

def test_commit_creates_exactly_one_audit_log_row_without_pii(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    for entity in ENTITIES:
        secret_name = f"{entity} audit subject should not leak"
        rows = [_good_row(entity, secret_name), _good_row(entity, f"{entity} audit subject 2")]
        resp = _upload(client, token, auth_header, entity, "commit", _csv_bytes(HEADER[entity], rows), filename="myimport.csv")
        created_count = resp.get_json()["created_count"]
        assert created_count == 2

        logs = AuditLog.query.filter_by(resource_type=entity, action="import").all()
        assert len(logs) == 1
        after = json.loads(logs[0].after)
        assert after["created_count"] == created_count
        assert after["filename"] == "myimport.csv"
        assert "skipped_count" in after
        assert "total" in after
        # No raw file content or PII beyond filename/counts.
        assert secret_name not in json.dumps(after)
        assert set(after.keys()) == {"filename", "created_count", "skipped_count", "total"}


def test_blank_cell_in_a_column_that_has_a_schema_default_still_falls_back_to_it(client, make_staff_user, auth_header):
    """Regression test: _clean_row used to map a blank cell to an
    explicit None rather than omitting the key, so a CSV that includes
    (say) an inventory item's "category" column but leaves individual
    cells blank would fail validation ("Field may not be null") instead
    of falling back to the schema's own default — even though a column
    that's absent from the header entirely already worked correctly."""
    _, token = make_staff_user("admin")

    inventory_csv = _csv_bytes(
        ["name", "unit", "category", "minimum_stock"],
        [["Blank Category Item", "kg", "", ""]],
    )
    resp = _upload(client, token, auth_header, "inventory_items", "commit", inventory_csv)
    body = resp.get_json()
    assert body["created_count"] == 1, body
    item = InventoryItem.query.filter_by(name="Blank Category Item").first()
    assert item.category == "Other"
    assert float(item.minimum_stock) == 0

    programs_csv = _csv_bytes(["name", "status"], [["Blank Status Program", ""]])
    resp2 = _upload(client, token, auth_header, "programs", "commit", programs_csv)
    body2 = resp2.get_json()
    assert body2["created_count"] == 1, body2
    program = Program.query.filter_by(name="Blank Status Program").first()
    assert program.status == "Draft"
