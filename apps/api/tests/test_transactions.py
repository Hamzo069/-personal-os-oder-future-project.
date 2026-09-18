from tests.conftest import UserSession

URL = "/api/v1/transactions"


def test_create_and_get_transaction(alice: UserSession) -> None:
    cats = alice.categories()
    tx = alice.add_transaction(
        merchant="Hetzner", amount="4.51", vat_rate="19", vat_amount="0.72",
        category_id=cats["Software & Subscriptions"], description="Cloud server",
    )  # fmt: skip
    assert tx["amount"] == "4.51"
    assert tx["category"]["name"] == "Software & Subscriptions"
    assert tx["source"] == "manual"
    fetched = alice.get(f"{URL}/{tx['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["merchant"] == "Hetzner"


def test_validation_errors(alice: UserSession, bob: UserSession) -> None:
    base = {"date": "2026-09-01", "merchant": "X", "currency": "EUR"}
    assert alice.post(URL, json={**base, "amount": "0"}).status_code == 422
    assert alice.post(URL, json={**base, "amount": "-5"}).status_code == 422
    assert alice.post(URL, json={**base, "amount": "1.999"}).status_code == 422
    assert alice.post(URL, json={**base, "amount": "1", "date": "not-a-date"}).status_code == 422
    bob_cat = next(iter(bob.categories().values()))
    foreign = alice.post(URL, json={**base, "amount": "1", "category_id": bob_cat})
    assert foreign.status_code == 404  # cannot attach another user's category


def test_list_filters_pagination_and_sorting(alice: UserSession) -> None:
    cats = alice.categories()
    alice.add_transaction(date="2026-07-15", merchant="Bahn", amount="49.00",
                          category_id=cats["Travel & Transport"])  # fmt: skip
    alice.add_transaction(date="2026-08-03", merchant="Adobe", amount="23.79",
                          category_id=cats["Software & Subscriptions"])  # fmt: skip
    alice.add_transaction(date="2026-08-20", merchant="Rewe", amount="12.30",
                          category_id=cats["Food & Drinks"], notes="team lunch")  # fmt: skip
    alice.add_transaction(date="2026-09-01", merchant="Adobe", amount="23.79",
                          category_id=cats["Software & Subscriptions"])  # fmt: skip

    everything = alice.get(URL).json()
    assert everything["total"] == 4
    assert [t["date"] for t in everything["items"]] == [
        "2026-09-01", "2026-08-20", "2026-08-03", "2026-07-15"
    ]  # fmt: skip

    august = alice.get(URL, params={"date_from": "2026-08-01", "date_to": "2026-08-31"}).json()
    assert august["total"] == 2

    software = alice.get(URL, params={"category_id": cats["Software & Subscriptions"]}).json()
    assert software["total"] == 2

    search = alice.get(URL, params={"q": "lunch"}).json()
    assert search["total"] == 1 and search["items"][0]["merchant"] == "Rewe"

    expensive = alice.get(URL, params={"min_amount": "20", "max_amount": "30"}).json()
    assert expensive["total"] == 2

    paged = alice.get(URL, params={"page": 2, "page_size": 3}).json()
    assert paged["total"] == 4 and len(paged["items"]) == 1

    by_amount = alice.get(URL, params={"sort": "amount_desc"}).json()
    assert by_amount["items"][0]["merchant"] == "Bahn"

    assert alice.get(URL, params={"page_size": 1000}).status_code == 422


def test_update_and_delete(alice: UserSession) -> None:
    tx = alice.add_transaction()
    updated = alice.patch(f"{URL}/{tx['id']}", json={"amount": "25.00", "notes": "edited"})
    assert updated.status_code == 200
    assert updated.json()["amount"] == "25.00"
    assert updated.json()["notes"] == "edited"
    assert updated.json()["merchant"] == "Test Merchant"  # untouched fields stay

    assert alice.delete(f"{URL}/{tx['id']}").status_code == 204
    assert alice.get(f"{URL}/{tx['id']}").status_code == 404


def test_transactions_are_isolated_per_user(alice: UserSession, bob: UserSession) -> None:
    tx = alice.add_transaction()
    assert bob.get(URL).json()["total"] == 0
    assert bob.get(f"{URL}/{tx['id']}").status_code == 404
    assert bob.patch(f"{URL}/{tx['id']}", json={"amount": "1.00"}).status_code == 404
    assert bob.delete(f"{URL}/{tx['id']}").status_code == 404


def test_csv_export(alice: UserSession) -> None:
    cats = alice.categories()
    alice.add_transaction(date="2026-08-03", merchant="Adobe; Inc", amount="23.79",
                          vat_rate="19", category_id=cats["Software & Subscriptions"])  # fmt: skip
    response = alice.get(f"{URL}/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    text = response.text.lstrip("﻿")
    lines = text.strip().split("\n")
    assert lines[0].startswith("date;merchant;description;amount")
    assert lines[1].startswith(
        '2026-08-03;"Adobe; Inc";;23.79;EUR;19.00;3.80;Software & Subscriptions'
    )


def test_vat_amount_is_derived_from_rate_when_missing(alice: UserSession) -> None:
    tx = alice.add_transaction(amount="119.00", vat_rate="19")
    assert tx["vat_amount"] == "19.00"
    explicit = alice.add_transaction(amount="10.00", vat_rate="7", vat_amount="0.50")
    assert explicit["vat_amount"] == "0.50"  # explicit values are never overridden
    no_rate = alice.add_transaction(amount="10.00")
    assert no_rate["vat_amount"] is None

    updated = alice.patch(f"{URL}/{tx['id']}", json={"vat_rate": "7"}).json()
    assert updated["vat_amount"] == "7.79"  # 119 - 119/1.07


def test_csv_export_neutralises_formula_cells(alice: UserSession) -> None:
    alice.add_transaction(merchant='=HYPERLINK("http://evil")', notes="+1", description="@cmd")
    text = alice.get(f"{URL}/export").text
    assert "'=HYPERLINK" in text
    assert ";'@cmd;" in text
    assert ";'+1" in text
