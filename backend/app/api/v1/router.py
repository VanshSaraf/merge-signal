from fastapi import APIRouter

from app.api.v1.pull_requests import router as pull_requests_router

router = APIRouter(prefix="/api/v1")
router.include_router(pull_requests_router)
