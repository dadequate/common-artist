from fastapi import APIRouter

router = APIRouter(tags=["portal"])


@router.get("/")
async def portal_home():
    return {"message": "Artist portal — coming in Phase 3"}
