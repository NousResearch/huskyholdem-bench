from fastapi import APIRouter

router = APIRouter(prefix="/utils", tags=["utils"])

@router.get("/ping")
async def ping():
    return {"ping": "pong"}

@router.get("/health")
async def health():
    return {"status": "ok"}