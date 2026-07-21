from fastapi import APIRouter
from comms_service.api.v1 import consultation, generate_reply, intent, negotiations, simulate_buyer

api_v1_router = APIRouter()
api_v1_router.include_router(negotiations.router, prefix="/negotiations", tags=["Negotiations"])
api_v1_router.include_router(simulate_buyer.router, prefix="/negotiations", tags=["Negotiations"])
api_v1_router.include_router(consultation.router, tags=["AI Consultation"])
api_v1_router.include_router(generate_reply.router, tags=["Generate Reply"])
api_v1_router.include_router(intent.router, tags=["Intent Classification"])