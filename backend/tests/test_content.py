import pytest


# ---------- Blog ----------

def test_public_blog_only_returns_published(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/blog", json={"title": "Published post", "status": "Published"}, headers=auth_header(token))
    client.post("/api/admin/blog", json={"title": "Draft post", "status": "Draft"}, headers=auth_header(token))

    resp = client.get("/api/blog")
    assert resp.status_code == 200
    titles = [p["title"] for p in resp.get_json()["posts"]]
    assert titles == ["Published post"]


def test_admin_blog_list_includes_drafts(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/blog", json={"title": "Draft post", "status": "Draft"}, headers=auth_header(token))

    resp = client.get("/api/admin/blog", headers=auth_header(token))
    assert resp.status_code == 200
    assert len(resp.get_json()["posts"]) == 1


def test_volunteer_cannot_create_blog_post(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/admin/blog", json={"title": "Sneaky"}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_see_admin_blog_list(client):
    resp = client.get("/api/admin/blog")
    assert resp.status_code == 401


def test_blog_create_rejects_empty_title(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/blog", json={"title": ""}, headers=auth_header(token))
    assert resp.status_code == 400


def test_blog_create_rejects_invalid_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/blog", json={"title": "X", "status": "Archived"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_blog_update_and_delete(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    post = client.post("/api/admin/blog", json={"title": "Original"}, headers=auth_header(token)).get_json()["post"]

    patched = client.patch(
        f"/api/admin/blog/{post['id']}", json={"title": "Updated", "status": "Published"}, headers=auth_header(token)
    )
    assert patched.status_code == 200
    assert patched.get_json()["post"]["title"] == "Updated"

    deleted = client.delete(f"/api/admin/blog/{post['id']}", headers=auth_header(token))
    assert deleted.status_code == 204
    assert client.get("/api/admin/blog", headers=auth_header(token)).get_json()["posts"] == []


# ---------- Gallery ----------

def test_public_can_read_gallery(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/gallery", json={"url": "/images/example.jpg"}, headers=auth_header(token))
    resp = client.get("/api/gallery")
    assert resp.status_code == 200
    assert len(resp.get_json()["images"]) == 1


def test_volunteer_cannot_add_gallery_image(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/admin/gallery", json={"url": "/images/x.jpg"}, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_gallery_create_rejects_missing_url(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/gallery", json={}, headers=auth_header(token))
    assert resp.status_code == 400


def test_gallery_delete(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    image = client.post("/api/admin/gallery", json={"url": "/images/x.jpg"}, headers=auth_header(token)).get_json()["image"]
    resp = client.delete(f"/api/admin/gallery/{image['id']}", headers=auth_header(token))
    assert resp.status_code == 204


# ---------- Crafts ----------

VALID_CRAFT = {"title": "Beaded Bracelet", "category": "Beadwork", "maker": "Mary A.", "price": 850}


def test_public_can_read_crafts(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/crafts", json=VALID_CRAFT, headers=auth_header(token))
    resp = client.get("/api/crafts")
    assert resp.status_code == 200
    assert resp.get_json()["crafts"][0]["title"] == "Beaded Bracelet"


def test_volunteer_cannot_create_craft(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/admin/crafts", json=VALID_CRAFT, headers=auth_header(access_token))
    assert resp.status_code == 403


@pytest.mark.parametrize("price", [0, -10])
def test_craft_rejects_non_positive_price(client, make_staff_user, auth_header, price):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/crafts", json={**VALID_CRAFT, "price": price}, headers=auth_header(token))
    assert resp.status_code == 400


def test_craft_rejects_invalid_category(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    resp = client.post("/api/admin/crafts", json={**VALID_CRAFT, "category": "Pottery"}, headers=auth_header(token))
    assert resp.status_code == 400


def test_craft_update_status(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    craft = client.post("/api/admin/crafts", json=VALID_CRAFT, headers=auth_header(token)).get_json()["craft"]
    resp = client.patch(f"/api/admin/crafts/{craft['id']}", json={"status": "Sold"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["craft"]["status"] == "Sold"


# ---------- Team ----------

VALID_MEMBER = {"name": "Derrick Ayieko", "role": "Program Coordinator", "image": "/images/team-derrick.jpg"}


def test_public_can_read_team(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    client.post("/api/admin/team", json=VALID_MEMBER, headers=auth_header(token))
    resp = client.get("/api/team")
    assert resp.status_code == 200
    assert resp.get_json()["team"][0]["name"] == "Derrick Ayieko"


def test_volunteer_cannot_create_team_member(client, make_user, auth_header):
    _, access_token, _ = make_user()
    resp = client.post("/api/admin/team", json=VALID_MEMBER, headers=auth_header(access_token))
    assert resp.status_code == 403


def test_team_create_rejects_missing_image(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    payload = {k: v for k, v in VALID_MEMBER.items() if k != "image"}
    resp = client.post("/api/admin/team", json=payload, headers=auth_header(token))
    assert resp.status_code == 400


def test_team_update_and_delete(client, make_staff_user, auth_header):
    _, token = make_staff_user("admin")
    member = client.post("/api/admin/team", json=VALID_MEMBER, headers=auth_header(token)).get_json()["member"]

    patched = client.patch(f"/api/admin/team/{member['id']}", json={"role": "Treasurer"}, headers=auth_header(token))
    assert patched.status_code == 200
    assert patched.get_json()["member"]["role"] == "Treasurer"

    deleted = client.delete(f"/api/admin/team/{member['id']}", headers=auth_header(token))
    assert deleted.status_code == 204
