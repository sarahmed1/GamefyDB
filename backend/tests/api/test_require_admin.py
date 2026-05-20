def test_admin_can_access_admin_route(client):
    client.post("/api/auth/login", data={"username": "admin@gamefy.test", "password": "admin12345"})
    resp = client.get("/api/_admin_ping")
    assert resp.status_code == 200
    assert resp.json() == {"hello": "admin@gamefy.test"}


def test_viewer_is_forbidden_from_admin_route(client):
    client.post("/api/auth/login", data={"username": "viewer@gamefy.test", "password": "viewer12345"})
    resp = client.get("/api/_admin_ping")
    assert resp.status_code == 403


def test_unauthenticated_is_unauthorized_from_admin_route(client):
    resp = client.get("/api/_admin_ping")
    assert resp.status_code == 401
