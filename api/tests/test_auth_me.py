def test_logout_clears_cookie(client):
    client.post("/api/auth/login", data={"username": "viewer@gamefy.test", "password": "viewer12345"})
    assert client.get("/api/auth/me").status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204

    # After logout, the cookie should be cleared/invalidated.
    me_after = client.get("/api/auth/me")
    assert me_after.status_code == 401
