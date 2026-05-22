"""Aggregate v1 routers."""
from fastapi import APIRouter

from matching_service.api.v1 import hs_classifier, matching

api_v1_router = APIRouter()
api_v1_router.include_router(matching.router, tags=["Matching"])
api_v1_router.include_router(hs_classifier.router, prefix="/hs-classifier", tags=["HS Classifier"])