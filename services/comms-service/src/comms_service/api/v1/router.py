from fastapi import APIRouter
from comms_service.api.v1 import negotiations

api_v1_router = APIRouter()
api_v1_router.include_router(negotiations.router, prefix="/negotiations", tags=["Negotiations"])