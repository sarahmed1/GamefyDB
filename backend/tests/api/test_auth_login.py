def test_login_sets_cookie_and_me_returns_user(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@gamefy.test", "password": "admin12345"},
    )
    assert resp.status_code == 204, resp.text
    assert "gamefydb_session" in client.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "admin@gamefy.test"
    assert body["role"] == "admin"


def test_login_with_wrong_password_returns_400(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@gamefy.test", "password": "wrong-password"},
    )
    assert resp.status_code == 400


def test_me_without_cookie_returns_401(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
