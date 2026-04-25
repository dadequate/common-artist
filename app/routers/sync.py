from fastapi import APIRouter

router = APIRouter(tags=["sync"])


@router.get("/status")
async def sync_status():
    return {"message": "POS sync — coming in Phase 2"}
