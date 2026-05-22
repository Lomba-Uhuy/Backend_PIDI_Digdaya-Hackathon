"""NIB verification via OSS RBA API.

OSS RBA (Online Single Submission, Risk-Based Approach) — PP No. 5/2021.
Endpoint: https://oss.go.id/api/v1/perizinan/nib/{nib}
"""
from __future__ import annotations

import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from etl_worker.celery_app import celery_app
from etl_worker.config import settings
from etl_worker.db.umkm_repo import update_umkm_verification_result

log = structlog.get_logger(__name__)


@celery_app.task(
    name="verification.verify_nib",
    bind=True,
    queue="external",
    max_retries=5,
    soft_time_limit=60,
)
def verify_nib(self, umkm_id: str, nib: str, user_id: str) -> dict:  # type: ignore[no-untyped-def]
    log.info("verification.nib.start", umkm_id=umkm_id, nib=nib, user_id=user_id)
    try:
        oss = _call_oss_rba(nib)
        score = _calculate_verification_score(oss)
        status = "VERIFIED" if oss.get("is_valid") else "FAILED"
        update_umkm_verification_result(
            umkm_id=umkm_id,
            oss_data=oss,
            verified_score=score,
            status=status,
        )
        log.info("verification.nib.done", umkm_id=umkm_id, score=score, status=status)
        return {"umkm_id": umkm_id, "score": score, "status": status}
    except Exception as exc:
        log.error("verification.nib.failed", umkm_id=umkm_id, exc=str(exc))
        raise self.retry(exc=exc, countdown=30)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _call_oss_rba(nib: str) -> dict:
    if not settings.oss_rba_api_key:
        log.warning("oss_rba.no_api_key.using_mock")
        return _mock_oss_response(nib)
    with httpx.Client(timeout=15.0) as client:
        r = client.get(
            f"{settings.oss_rba_base_url}/v1/perizinan/nib/{nib}",
            headers={"Authorization": f"Bearer {settings.oss_rba_api_key}"},
        )
        r.raise_for_status()
        return r.json()


def _mock_oss_response(nib: str) -> dict:
    """Deterministic mock so dev/demo flow works without API key."""
    return {
        "nib": nib,
        "is_valid": True,
        "business_name": f"Demo UMKM NIB-{nib[-4:]}",
        "kbli": "47752",
        "business_scale": "KECIL",
        "compliance_status": "COMPLIANT",
        "registered_date": "2022-01-15",
        "is_mock": True,
    }


def _calculate_verification_score(oss: dict) -> float:
    """
    Verified UMKM Profile Score (0.0 - 1.0):
      0.8+ → fully verified, medium-large export readiness
      0.6  → verified, small-scale ready
      0.4  → partial, needs more certifications
      <0.4 → failed / incomplete
    """
    score = 0.0
    if oss.get("is_valid"):
        score += 0.5
    compliance = oss.get("compliance_status", "")
    if compliance == "COMPLIANT":
        score += 0.3
    elif compliance == "CONDITIONAL":
        score += 0.15
    scale = oss.get("business_scale", "")
    bonus = {"MENENGAH": 0.2, "KECIL": 0.15, "MIKRO": 0.05}
    score += bonus.get(scale, 0.0)
    return min(1.0, round(score, 4))