from app.core.config import get_settings
from fastapi import APIRouter

router = APIRouter(tags=["system"])
router_prefix_setting = "admin_api_prefix"


@router.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }
