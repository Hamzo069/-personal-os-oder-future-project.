from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Response, UploadFile, status

from app.api.deps import AIDep, CurrentUser, DBDep, SettingsDep, StorageDep, limit_ai
from app.core.errors import ConflictError, ValidationError
from app.models import Receipt, ReceiptStatus
from app.schemas.receipt import ReceiptConfirm, ReceiptRead, ReceiptWithTransaction
from app.services import receipt_service

router = APIRouter(prefix="/receipts", tags=["receipts"])


class ReceiptReadWithSuggestion(ReceiptRead):
    suggested_category_id: str | None = None


def _to_read(db: DBDep, user_id: str, receipt: Receipt) -> ReceiptReadWithSuggestion:
    data = ReceiptReadWithSuggestion.model_validate(receipt)
    data.suggested_category_id = receipt_service.suggested_category_id(
        db, user_id, receipt.extracted
    )
    return data


@router.post(
    "",
    response_model=ReceiptReadWithSuggestion,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_ai)],
)
async def upload_receipt(
    background: BackgroundTasks,
    user: CurrentUser,
    db: DBDep,
    storage: StorageDep,
    settings: SettingsDep,
    provider: AIDep,
    file: Annotated[UploadFile, File(description="JPEG, PNG, WebP or PDF, max 10 MB")],
) -> ReceiptReadWithSuggestion:
    # Read at most limit+1 bytes so an oversized upload cannot exhaust memory.
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise ValidationError(f"File exceeds the {settings.max_upload_mb} MB upload limit")
    receipt = receipt_service.store_upload(
        db, storage, settings, user, filename=file.filename or "receipt", data=data
    )
    background.add_task(receipt_service.run_extraction, receipt.id, provider, storage)
    return _to_read(db, user.id, receipt)


@router.get("", response_model=list[ReceiptReadWithSuggestion])
def list_receipts(
    user: CurrentUser,
    db: DBDep,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[ReceiptReadWithSuggestion]:
    if status_filter and status_filter not in ReceiptStatus.ALL:
        raise ValidationError(f"Unknown status '{status_filter}'")
    receipts = receipt_service.list_receipts(db, user.id, status=status_filter)
    return [_to_read(db, user.id, r) for r in receipts]


@router.get("/{receipt_id}", response_model=ReceiptReadWithSuggestion)
def get_receipt(receipt_id: str, user: CurrentUser, db: DBDep) -> ReceiptReadWithSuggestion:
    return _to_read(db, user.id, receipt_service.get_receipt(db, user.id, receipt_id))


@router.get("/{receipt_id}/file")
def get_receipt_file(
    receipt_id: str, user: CurrentUser, db: DBDep, storage: StorageDep
) -> Response:
    receipt = receipt_service.get_receipt(db, user.id, receipt_id)
    return Response(
        content=storage.read(receipt.storage_path),
        media_type=receipt.media_type,
        headers={
            # User-supplied files are never rendered in the API origin: the SPA fetches
            # them with the Bearer token and shows them from a blob URL.
            "Content-Disposition": f'attachment; filename="{receipt.id}"',
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.post(
    "/{receipt_id}/extract",
    response_model=ReceiptReadWithSuggestion,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_ai)],
)
def retry_extraction(
    receipt_id: str,
    background: BackgroundTasks,
    user: CurrentUser,
    db: DBDep,
    storage: StorageDep,
    provider: AIDep,
) -> ReceiptReadWithSuggestion:
    receipt = receipt_service.get_receipt(db, user.id, receipt_id)
    if receipt.status == ReceiptStatus.CONFIRMED:
        raise ConflictError("Receipt was already confirmed")
    if receipt.status == ReceiptStatus.PROCESSING:
        raise ConflictError("Extraction is already running")
    background.add_task(receipt_service.run_extraction, receipt.id, provider, storage)
    return _to_read(db, user.id, receipt)


@router.post("/{receipt_id}/confirm", response_model=ReceiptWithTransaction)
def confirm_receipt(
    receipt_id: str, payload: ReceiptConfirm, user: CurrentUser, db: DBDep
) -> ReceiptWithTransaction:
    tx = receipt_service.confirm_receipt(db, user.id, receipt_id, payload)
    receipt = receipt_service.get_receipt(db, user.id, receipt_id)
    return ReceiptWithTransaction(receipt=ReceiptRead.model_validate(receipt), transaction_id=tx.id)


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(receipt_id: str, user: CurrentUser, db: DBDep, storage: StorageDep) -> None:
    receipt_service.delete_receipt(db, storage, user.id, receipt_id)
