from tests.conftest import UserSession

URL = "/api/v1/categories"


def test_default_categories_are_seeded(alice: UserSession) -> None:
    categories = alice.get(URL).json()
    assert len(categories) == 10
    assert all(c["is_default"] for c in categories)
    assert "Software & Subscriptions" in {c["name"] for c in categories}


def test_create_update_delete_category(alice: UserSession) -> None:
    created = alice.post(URL, json={"name": "Coworking", "color": "#123abc"})
    assert created.status_code == 201
    category_id = created.json()["id"]

    duplicate = alice.post(URL, json={"name": "coworking"})
    assert duplicate.status_code == 409

    updated = alice.patch(f"{URL}/{category_id}", json={"name": "Coworking Space"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Coworking Space"

    tx = alice.add_transaction(category_id=category_id)
    assert alice.delete(f"{URL}/{category_id}").status_code == 204
    after = alice.get(f"/api/v1/transactions/{tx['id']}").json()
    assert after["category"] is None  # transaction survives, becomes uncategorised


def test_invalid_color_rejected(alice: UserSession) -> None:
    assert alice.post(URL, json={"name": "X", "color": "red"}).status_code == 422


def test_categories_are_isolated_per_user(alice: UserSession, bob: UserSession) -> None:
    alice_cat = alice.post(URL, json={"name": "Alice only"}).json()
    assert "Alice only" not in bob.categories()
    assert bob.patch(f"{URL}/{alice_cat['id']}", json={"name": "Hacked"}).status_code == 404
    assert bob.delete(f"{URL}/{alice_cat['id']}").status_code == 404
