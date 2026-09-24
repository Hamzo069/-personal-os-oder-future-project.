import datetime as dt

from app.ai.schemas import QueryPlan
from app.services.ai_service import _validate_plan

from tests.conftest import MINIMAL_PNG, UserSession

SUMMARY = "/api/v1/insights/summary"
QUERY = "/api/v1/ai/query"
USAGE = "/api/v1/ai/usage"


def _seed(alice: UserSession) -> dict[str, str]:
    cats = alice.categories()
    alice.add_transaction(date="2026-07-05", merchant="Bahn", amount="49.00",
                          category_id=cats["Travel & Transport"])  # fmt: skip
    alice.add_transaction(date="2026-08-03", merchant="Adobe", amount="23.79", vat_amount="3.80",
                          category_id=cats["Software & Subscriptions"])  # fmt: skip
    alice.add_transaction(date="2026-08-20", merchant="Rewe", amount="12.30",
                          category_id=cats["Food & Drinks"])  # fmt: skip
    alice.add_transaction(date="2026-09-01", merchant="Adobe", amount="23.79", vat_amount="3.80",
                          category_id=cats["Software & Subscriptions"])  # fmt: skip
    return cats


def test_summary_aggregates(alice: UserSession) -> None:
    _seed(alice)
    alice.post("/api/v1/receipts", files={"file": ("r.png", MINIMAL_PNG, "image/png")})

    response = alice.get(SUMMARY, params={"date_from": "2026-08-01", "date_to": "2026-09-30"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == "59.88"
    assert body["count"] == 3
    assert body["vat_total"] == "7.60"
    assert body["average"] == "19.96"
    assert body["previous_period_total"] == "49.00"  # July, same length period before
    assert body["change_percent"] == 22.2
    assert body["receipts_pending_review"] == 1

    by_cat = {c["category_name"]: c for c in body["by_category"]}
    assert by_cat["Software & Subscriptions"]["total"] == "47.58"
    assert by_cat["Software & Subscriptions"]["count"] == 2
    assert [m["month"] for m in body["by_month"]] == ["2026-08", "2026-09"]
    assert body["by_month"][0]["total"] == "36.09"
    assert body["top_merchants"][0]["merchant"] == "Adobe"


def test_summary_validates_period(alice: UserSession) -> None:
    bad = alice.get(SUMMARY, params={"date_from": "2026-09-30", "date_to": "2026-09-01"})
    assert bad.status_code == 422
    default = alice.get(SUMMARY)
    assert default.status_code == 200
    assert len(default.json()["by_month"]) >= 6


def test_natural_language_query_with_mock_provider(alice: UserSession) -> None:
    cats = _seed(alice)
    response = alice.post(QUERY, json={"question": "How much did I spend on Software in August?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plan"]["intent"] == "sum"
    assert body["plan"]["categories"] == ["Software & Subscriptions"]
    assert body["plan"]["date_from"] == "2026-08-01"
    assert body["result"]["total"] == "23.79"
    assert "23.79 EUR" in body["answer"]

    count = alice.post(QUERY, json={"question": "How many expenses do I have?"}).json()
    assert count["plan"]["intent"] == "count"
    assert count["result"]["count"] == 4

    grouped = alice.post(QUERY, json={"question": "Show spending by category"}).json()
    assert grouped["plan"]["intent"] == "by_category"
    assert grouped["result"]["groups"][0]["label"] == "Travel & Transport"  # 49.00 is the max

    listed = alice.post(QUERY, json={"question": "List my expenses at Adobe"}).json()
    assert listed["plan"]["intent"] == "list"
    assert len(listed["result"]["items"]) == 4  # mock does not extract merchants

    assert alice.post(QUERY, json={"question": "hi"}).status_code == 422
    assert cats  # seeded


def test_usage_is_recorded(alice: UserSession) -> None:
    alice.post(QUERY, json={"question": "How much this month?"})
    alice.post("/api/v1/receipts", files={"file": ("r.png", MINIMAL_PNG, "image/png")})
    usage = alice.get(USAGE).json()
    assert usage["calls"] == 2
    assert usage["by_kind"] == {"query_plan": 1, "receipt_extraction": 1}


def test_validate_plan_sanitises_model_output() -> None:
    plan = QueryPlan(
        intent="sum",
        date_from="2026-09-30",
        date_to="2026-09-01",
        categories=["software & subscriptions", "Nonexistent"],
        merchant_contains="  Adobe  ",
        min_amount=None,
        max_amount=None,
        explanation="x",
    )
    cleaned = _validate_plan(plan, {"software & subscriptions": "Software & Subscriptions"})
    assert cleaned.date_from == "2026-09-01" and cleaned.date_to == "2026-09-30"
    assert cleaned.categories == ["Software & Subscriptions"]
    assert cleaned.merchant_contains == "Adobe"

    invalid_date = _validate_plan(plan.model_copy(update={"date_from": "yesterday"}), {})
    assert invalid_date.date_from is None
    assert dt.date.fromisoformat(invalid_date.date_to or "2026-09-01")
