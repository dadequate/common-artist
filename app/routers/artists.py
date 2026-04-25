from fastapi import APIRouter

router = APIRouter(tags=["artists"])


@router.get("/")
async def list_artists():
    return {"message": "Artist management — coming in Phase 1"}
