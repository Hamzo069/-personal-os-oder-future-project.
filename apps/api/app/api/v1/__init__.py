from fastapi import APIRouter

from app.api.v1 import ai, auth, categories, insights, receipts, transactions, users

router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(categories.router)
router.include_router(transactions.router)
router.include_router(receipts.router)
router.include_router(insights.router)
router.include_router(ai.router)
