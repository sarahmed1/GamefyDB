def test_facts_cash_returns_paged_rows(cached_app):
    r = cached_app.get("/api/facts/cash?page=1&size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 6
    assert len(body["items"]) == 6
    assert body["items"][0]["tx_id"] == 1


def test_facts_cash_paging(cached_app):
    r = cached_app.get("/api/facts/cash?page=2&size=2")
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2
    assert body["size"] == 2
    assert body["total"] == 6
    assert len(body["items"]) == 2
    assert body["items"][0]["tx_id"] == 3


def test_facts_cash_date_filter(cached_app):
    r = cached_app.get("/api/facts/cash?from=2026-05-11&to=2026-05-11T23:59:59")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {3, 4}


def test_facts_cash_terminal_filter(cached_app):
    r = cached_app.get("/api/facts/cash?terminal_id=1")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {1, 4}


def test_facts_cash_cashier_filter(cached_app):
    r = cached_app.get("/api/facts/cash?cashier_id=2")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {2, 4, 6}


def test_facts_cash_method_filter(cached_app):
    r = cached_app.get("/api/facts/cash?payment=Credit%20Card")
    assert r.status_code == 200
    items = r.json()["items"]
    assert {it["tx_id"] for it in items} == {3, 6}


def test_facts_cash_unauth(client):
    from fastapi.testclient import TestClient
    from backend.apps.api.main import app
    with TestClient(app) as c:
        r = c.get("/api/facts/cash")
        assert r.status_code == 401


def test_facts_sessions_returns_paged_rows(cached_app):
    r = cached_app.get("/api/facts/sessions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    types = {it["session_type"] for it in body["items"]}
    assert types == {"Walk-in", "Member"}


def test_facts_sessions_member_filter(cached_app):
    r = cached_app.get("/api/facts/sessions?session_type=Member")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["member_id"] == 1001


def test_facts_stock_returns_404(cached_app):
    r = cached_app.get("/api/facts/stock")
    assert r.status_code == 404


def test_facts_members_returns_404(cached_app):
    r = cached_app.get("/api/facts/members")
    assert r.status_code == 404




