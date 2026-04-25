from fastapi import APIRouter

router = APIRouter(tags=["admin"])


@router.get("/")
async def admin_home():
    return {"message": "Admin dashboard — coming in Phase 1"}
