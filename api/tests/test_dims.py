def test_dim_cashier_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/cashier")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    names = {item["cashier_name"] for item in data["items"]}
    assert names == {"taktek", "youssef"}


def test_dim_terminal_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/terminal")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    types = {item["terminal_type"] for item in data["items"]}
    assert types == {"Standard PC", "PlayStation"}


def test_dim_item_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/item")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["item"] == "Coke"
    assert items[0]["unit_price"] == 3.0


def test_dim_member_returns_full_table(cached_app):
    r = cached_app.get("/api/dims/member")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "amine"
    assert items[0]["total_tnd"] == 62.0


def test_dim_unknown_returns_404(cached_app):
    r = cached_app.get("/api/dims/widgets")
    assert r.status_code == 404


def test_dim_endpoint_requires_auth(client):
    # `client` (without `cached_app`) is still authenticated via the seeded
    # admin cookie; we want to verify unauth → 401. Use a fresh TestClient.
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as c:
        r = c.get("/api/dims/cashier")
        assert r.status_code == 401
