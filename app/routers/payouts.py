from fastapi import APIRouter

router = APIRouter(tags=["payouts"])


@router.get("/")
async def list_payouts():
    return {"message": "Payouts — coming in Phase 2"}
