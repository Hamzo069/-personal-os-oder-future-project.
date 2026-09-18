from pathlib import Path

from app.core.config import get_settings

from tests.conftest import MINIMAL_PDF, MINIMAL_PNG, UserSession

URL = "/api/v1/receipts"


def _upload(user: UserSession, data: bytes = MINIMAL_PNG, filename: str = "receipt.png"):  # type: ignore[no-untyped-def]
    return user.post(URL, files={"file": (filename, data, "application/octet-stream")})


def test_upload_runs_mock_extraction(alice: UserSession) -> None:
    response = _upload(alice)
    assert response.status_code == 202
    receipt_id = response.json()["id"]

    # The TestClient runs background tasks before returning, so extraction is done.
    receipt = alice.get(f"{URL}/{receipt_id}").json()
    assert receipt["status"] == "extracted"
    assert receipt["media_type"] == "image/png"
    assert receipt["extracted"]["merchant"] == "Demo Store"
    assert receipt["extracted"]["currency"] == "EUR"
    assert receipt["confidence"] == 0.5
    assert receipt["suggested_category_id"] in alice.categories().values()

    listed = alice.get(URL, params={"status": "extracted"}).json()
    assert [r["id"] for r in listed] == [receipt_id]
    assert alice.get(URL, params={"status": "bogus"}).status_code == 422


def test_pdf_upload_is_detected_by_magic_bytes(alice: UserSession) -> None:
    response = _upload(alice, MINIMAL_PDF, "invoice.bin")
    assert response.status_code == 202
    assert response.json()["media_type"] == "application/pdf"


def test_rejects_unsupported_and_oversized_files(alice: UserSession) -> None:
    text = _upload(alice, b"hello world", "notes.txt")
    assert text.status_code == 422
    assert "Unsupported" in text.json()["error"]["message"]

    fake = _upload(alice, b"GIF89a" + b"\x00" * 10, "receipt.png")  # extension lies
    assert fake.status_code == 422

    too_big = _upload(alice, MINIMAL_PNG + b"\x00" * (1024 * 1024), "big.png")
    assert too_big.status_code == 422
    assert "limit" in too_big.json()["error"]["message"]

    assert _upload(alice, b"", "empty.png").status_code == 422


def test_file_download_and_delete(alice: UserSession) -> None:
    receipt_id = _upload(alice).json()["id"]
    file_response = alice.get(f"{URL}/{receipt_id}/file")
    assert file_response.status_code == 200
    assert file_response.headers["content-type"] == "image/png"
    assert file_response.content == MINIMAL_PNG

    upload_dir = Path(get_settings().upload_dir)
    stored = list(upload_dir.rglob("*.png"))
    assert len(stored) == 1

    assert alice.delete(f"{URL}/{receipt_id}").status_code == 204
    assert alice.get(f"{URL}/{receipt_id}").status_code == 404
    assert list(upload_dir.rglob("*.png")) == []


def test_confirm_creates_transaction_and_learns_category(alice: UserSession) -> None:
    cats = alice.categories()
    receipt_id = _upload(alice).json()["id"]
    payload = {
        "date": "2026-09-12",
        "merchant": "Bäckerei Müller",
        "amount": "4.80",
        "currency": "EUR",
        "vat_rate": "7",
        "category_id": cats["Food & Drinks"],
    }
    confirmed = alice.post(f"{URL}/{receipt_id}/confirm", json=payload)
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["receipt"]["status"] == "confirmed"

    tx = alice.get(f"/api/v1/transactions/{body['transaction_id']}").json()
    assert tx["source"] == "receipt"
    assert tx["receipt_id"] == receipt_id
    assert tx["merchant"] == "Bäckerei Müller"

    # Confirming twice is a conflict.
    assert alice.post(f"{URL}/{receipt_id}/confirm", json=payload).status_code == 409

    # The learned merchant -> category mapping is passed to the provider as a hint.
    second = alice.get(f"{URL}/{_upload(alice).json()['id']}").json()
    assert second["extracted"]["merchant"] == "Bäckerei Müller"
    assert second["extracted"]["category"] == "Food & Drinks"
    assert second["suggested_category_id"] == cats["Food & Drinks"]


def test_confirm_rejects_foreign_category(alice: UserSession, bob: UserSession) -> None:
    receipt_id = _upload(alice).json()["id"]
    bob_cat = next(iter(bob.categories().values()))
    response = alice.post(
        f"{URL}/{receipt_id}/confirm",
        json={"date": "2026-09-12", "merchant": "X", "amount": "1.00", "category_id": bob_cat},
    )
    assert response.status_code == 404


def test_retry_extraction(alice: UserSession) -> None:
    receipt_id = _upload(alice).json()["id"]
    response = alice.post(f"{URL}/{receipt_id}/extract")
    assert response.status_code == 202
    assert alice.get(f"{URL}/{receipt_id}").json()["status"] == "extracted"


def test_receipts_are_isolated_per_user(alice: UserSession, bob: UserSession) -> None:
    receipt_id = _upload(alice).json()["id"]
    assert bob.get(URL).json() == []
    assert bob.get(f"{URL}/{receipt_id}").status_code == 404
    assert bob.get(f"{URL}/{receipt_id}/file").status_code == 404
    assert bob.delete(f"{URL}/{receipt_id}").status_code == 404


def test_ai_rate_limit_applies_to_uploads(alice: UserSession) -> None:
    from app.api import deps

    deps.ai_limiter.limit = 2
    try:
        codes = [_upload(alice).status_code for _ in range(3)]
    finally:
        deps.ai_limiter.limit = 30
    assert codes == [202, 202, 429]
