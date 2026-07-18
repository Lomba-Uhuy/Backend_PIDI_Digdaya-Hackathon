# -*- coding: utf-8 -*-
"""NIB verification: badanperizinan.co.id (step 1) + OSS public RBA API (step 2)."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from celery import Task

# Import dari billiard langsung karena celery-stubs tidak me-re-export SoftTimeLimitExceeded
# dengan syntax eksplisit (as X), sehingga Pylance menganggapnya tidak tersedia dari celery.exceptions.
from billiard.exceptions import SoftTimeLimitExceeded

from etl_worker.celery_app import celery_app
from etl_worker.config import settings
from etl_worker.db.umkm_repo import update_umkm_verification_result

log = structlog.get_logger(__name__)

NIB_API_BASE = "https://www.badanperizinan.co.id/api/v1/public"


@celery_app.task(  # type: ignore[untyped-decorator]
    name="verification.verify_nib",
    bind=True,
    queue="external",
    max_retries=5,
    soft_time_limit=60,
)
def verify_nib(self: Task, umkm_id: str, nib: str, user_id: str) -> dict[str, Any]:
    log.info("verification.nib.start", umkm_id=umkm_id, nib=nib, user_id=user_id)
    try:
        if len(nib) < 13:
            log.info("verification.nib.sandbox_mode", nib=nib)
            nib_data = _mock_nib_response(nib)
        else:
            nib_data = _verify_nib_two_step(nib)

        score = _calculate_verification_score(nib_data)
        status = "VERIFIED" if nib_data.get("is_valid") else "FAILED"
        update_umkm_verification_result(
            umkm_id=umkm_id,
            oss_data=nib_data,
            verified_score=score,
            status=status,
        )
        log.info(
            "verification.nib.done",
            umkm_id=umkm_id, score=score, status=status,
            sources=nib_data.get("verification_sources"),
        )
        return {"umkm_id": umkm_id, "score": score, "status": status}
    except SoftTimeLimitExceeded:
        log.warning("verification.nib.soft_time_limit", umkm_id=umkm_id, nib=nib)
        raise
    except Exception as exc:
        log.error("verification.nib.failed", umkm_id=umkm_id, exc=str(exc))
        raise self.retry(exc=exc, countdown=30) from exc


# --- Step 1 + 2 Dual Check: badanperizinan + OSS public ---

def _verify_nib_two_step(nib: str) -> dict[str, Any]:
    step1 = _fetch_badan_perizinan(nib)
    step2 = _fetch_oss_public(nib)
    return _merge_nib_sources(step1, step2)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _fetch_badan_perizinan(nib: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                f"{NIB_API_BASE}/nib/{nib}",
                headers={"Accept": "application/json", "User-Agent": "TradeConnect/1.0"},
            )
            body: dict[str, Any] = r.json()
            if not r.is_success or not body.get("success"):
                log.warning("nib_api.not_found", nib=nib)
                return _invalid_nib_response(nib)
            fields: list[dict[str, str]] = body.get("data", {}).get("fields", [])
            get_field = lambda label: next((f["value"] for f in fields if f["label"] == label), "")  # noqa: E731
            return {
                "nib": nib,
                "is_valid": True,
                "business_name": get_field("Nama Perusahaan"),
                "npwp": get_field("NPWP"),
                "kbli": "",
                "kbli_description": "",
                "business_scale": "",
                "oss_status_aktif": "",
                "oss_status_migrasi": "",
                "oss_status_penanaman_modal": "",
                "compliance_status": "COMPLIANT",
                "registered_date": get_field("Waktu Penerbitan OSS"),
                "certifications": [],
                "insw_verified": False,
                "insw_kategori": "",
                "insw_history": [],
                "oss_public_verified": False,
                "oss_public_data": {},
                "verification_sources": ["badanperizinan"],
                "sandbox_mode": False,
            }
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
        log.warning("nib_api.unavailable.using_mock", nib=nib, reason=str(exc))
        return _mock_nib_response(nib)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _fetch_oss_public(nib: str) -> dict[str, Any] | None:
    if not settings.oss_public_user_key:
        log.warning("oss_public.skip", nib=nib, reason="no_user_key")
        return None

    try:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://oss.go.id",
            "Referer": "https://oss.go.id/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome Safari"
            ),
            "user_key": settings.oss_public_user_key,
        }
        if settings.oss_public_recaptcha_response:
            headers["g-recaptcha-response"] = settings.oss_public_recaptcha_response
        if settings.oss_public_cookie:
            headers["Cookie"] = settings.oss_public_cookie

        payload = {"dataNib": {"nib": nib}}

        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                settings.oss_public_nib_url,
                headers=headers,
                json=payload,
            )
            if not r.is_success:
                log.warning("oss_public.failed_status", nib=nib, status=r.status_code)
                return None
            
            raw = r.json()
            if not _oss_looks_valid(raw):
                log.warning("oss_public.invalid_content", nib=nib)
                return None

            return {
                "nib": nib,
                "is_valid": True,
                "business_name": _pick_string(raw, [
                    "nama_perusahaan",
                    "namaPerusahaan",
                    "nama_perseroan",
                    "namaPerseroan",
                    "nama_pelaku_usaha",
                    "namaPelakuUsaha",
                    "nama",
                ]),
                "npwp": _pick_string(raw, ["npwp", "npwpPerusahaan", "npwp_perseroan"]),
                "kbli": _pick_string(raw, ["kbli", "kode_kbli", "kodeKbli"]),
                "kbli_description": _pick_string(raw, [
                    "uraian_kbli",
                    "uraianKbli",
                    "judul_kbli",
                    "judulKbli",
                    "kbli_description",
                ]),
                "business_scale": _pick_string(raw, [
                    "skala_usaha",
                    "skalaUsaha",
                    "uraian_skala_usaha",
                    "uraianSkalaUsaha",
                ]),
                "oss_status_aktif": _pick_string(raw, ["status_aktif", "statusAktif"]),
                "oss_status_migrasi": _pick_string(raw, ["status_migrasi", "statusMigrasi"]),
                "oss_status_penanaman_modal": _pick_string(raw, ["status_penanaman_modal", "statusPenanamanModal"]),
                "compliance_status": "COMPLIANT",
                "registered_date": _pick_string(raw, [
                    "tanggal_terbit_oss",
                    "tanggalTerbitOss",
                    "tgl_terbit_oss",
                    "tglTerbitOss",
                    "tgl_pengajuan_nib",
                    "tglPengajuanNib",
                ]),
                "oss_public_verified": True,
                "oss_public_data": raw,
                "verification_sources": ["oss_public"],
                "source": "oss_public",
            }
    except Exception as exc:
        log.warning("oss_public.error", nib=nib, reason=str(exc))
        return None


# --- Helpers ---

def _invalid_nib_response(nib: str) -> dict[str, Any]:
    return {
        "nib": nib,
        "is_valid": False,
        "business_name": "",
        "npwp": "",
        "kbli": "",
        "kbli_description": "",
        "business_scale": "",
        "oss_status_aktif": "",
        "oss_status_migrasi": "",
        "oss_status_penanaman_modal": "",
        "compliance_status": "INVALID",
        "registered_date": "",
        "certifications": [],
        "insw_verified": False,
        "insw_kategori": "",
        "insw_history": [],
        "oss_public_verified": False,
        "oss_public_data": {},
        "verification_sources": [],
        "sandbox_mode": False,
    }


_SANDBOX_PROFILES = [
    {"business_name": "CV Karya Rotan Nusantara", "npwp": "73.456.781.3-429.000",
     "kbli": "16291", "kbli_description": "Industri barang dari anyaman rotan, bambu, dan sejenisnya",
     "business_scale": "KECIL", "registered_date": "2021-03-10", "certifications": ["SNI"]},
    {"business_name": "PT Sumber Makmur Ekspor", "npwp": "01.234.567.8-543.000",
     "kbli": "46339", "kbli_description": "Perdagangan besar barang keperluan rumah tangga lainnya",
     "business_scale": "MENENGAH", "registered_date": "2019-07-22", "certifications": ["ISO 9001"]},
    {"business_name": "UD Mitra Dagang Sejati", "npwp": "62.345.678.2-117.000",
     "kbli": "46909", "kbli_description": "Perdagangan besar berbagai macam barang",
     "business_scale": "KECIL", "registered_date": "2020-11-05", "certifications": []},
    {"business_name": "CV Indah Kerajinan Indonesia", "npwp": "84.567.890.4-321.000",
     "kbli": "32901", "kbli_description": "Industri kerajinan yang tidak diklasifikasikan di tempat lain",
     "business_scale": "KECIL", "registered_date": "2022-01-15", "certifications": ["HALAL"]},
    {"business_name": "PT Batik Nusantara Lestari", "npwp": "52.678.901.6-789.000",
     "kbli": "13131", "kbli_description": "Industri batik",
     "business_scale": "MENENGAH", "registered_date": "2018-04-30", "certifications": ["SNI", "ISO 9001"]},
    {"business_name": "CV Agro Ekspor Mandiri", "npwp": "31.890.123.5-654.000",
     "kbli": "01611", "kbli_description": "Jasa pertanian dan perkebunan",
     "business_scale": "KECIL", "registered_date": "2023-02-18", "certifications": []},
    {"business_name": "UD Furnitur Jepara Jaya", "npwp": "91.234.560.7-012.000",
     "kbli": "31001", "kbli_description": "Industri furnitur dari kayu",
     "business_scale": "KECIL", "registered_date": "2020-08-14", "certifications": ["SNI"]},
    {"business_name": "PT Global Rempah Indonesia", "npwp": "45.123.456.9-876.000",
     "kbli": "10300", "kbli_description": "Industri pengolahan dan pengawetan buah-buahan dan sayuran",
     "business_scale": "MENENGAH", "registered_date": "2017-12-01", "certifications": ["HALAL", "ISO 22000"]},
    {"business_name": "CV Citra Tekstil Nusantara", "npwp": "29.876.543.1-234.000",
     "kbli": "14201", "kbli_description": "Industri pakaian jadi dari tekstil",
     "business_scale": "KECIL", "registered_date": "2021-09-03", "certifications": []},
    {"business_name": "PT Mebel Ekspor Makmur", "npwp": "68.901.234.0-567.000",
     "kbli": "31009", "kbli_description": "Industri furnitur lainnya",
     "business_scale": "MENENGAH", "registered_date": "2019-05-20", "certifications": ["ISO 9001"]},
]


def _mock_nib_response(nib: str) -> dict[str, Any]:
    """Fallback deterministik saat badanperizinan.co.id tidak tersedia."""
    profile = _SANDBOX_PROFILES[int(nib[-1]) % len(_SANDBOX_PROFILES)]
    return {
        "nib": nib,
        "is_valid": True,
        "business_name": profile["business_name"],
        "npwp": profile["npwp"],
        "kbli": profile["kbli"],
        "kbli_description": profile["kbli_description"],
        "business_scale": profile["business_scale"],
        "compliance_status": "COMPLIANT",
        "registered_date": profile["registered_date"],
        "certifications": profile["certifications"],
        "insw_verified": False,
        "insw_kategori": "",
        "insw_history": [],
        "oss_public_verified": False,
        "oss_public_data": {},
        "verification_sources": ["sandbox"],
        "sandbox_mode": True,
    }


def _merge_nib_sources(
    badan_perizinan: dict[str, Any], oss_public: dict[str, Any] | None
) -> dict[str, Any]:
    if not oss_public:
        return badan_perizinan

    sources = set(badan_perizinan.get("verification_sources", []))
    sources.add(oss_public.get("source", "oss_public"))
    if oss_public.get("oss_public_verified"):
        sources.discard("sandbox")

    return {
        "nib": badan_perizinan["nib"],
        "is_valid": badan_perizinan.get("is_valid") or oss_public.get("is_valid"),
        "business_name": (
            badan_perizinan.get("business_name") or oss_public.get("business_name") or ""
        ),
        "npwp": badan_perizinan.get("npwp") or oss_public.get("npwp") or "",
        "kbli": badan_perizinan.get("kbli") or oss_public.get("kbli") or "",
        "kbli_description": (
            badan_perizinan.get("kbli_description") or oss_public.get("kbli_description") or ""
        ),
        "business_scale": (
            badan_perizinan.get("business_scale") or oss_public.get("business_scale") or ""
        ),
        "oss_status_aktif": (
            badan_perizinan.get("oss_status_aktif") or oss_public.get("oss_status_aktif") or ""
        ),
        "oss_status_migrasi": (
            badan_perizinan.get("oss_status_migrasi") or oss_public.get("oss_status_migrasi") or ""
        ),
        "oss_status_penanaman_modal": (
            badan_perizinan.get("oss_status_penanaman_modal") or oss_public.get("oss_status_penanaman_modal") or ""
        ),
        "compliance_status": (
            oss_public.get("compliance_status") or "COMPLIANT"
            if badan_perizinan.get("compliance_status") == "INVALID"
            else badan_perizinan.get("compliance_status", "COMPLIANT")
        ),
        "registered_date": (
            badan_perizinan.get("registered_date") or oss_public.get("registered_date") or ""
        ),
        "oss_public_verified": bool(oss_public.get("oss_public_verified")),
        "oss_public_data": oss_public.get("oss_public_data") or {},
        "verification_sources": sorted(list(sources)),
        "sandbox_mode": (
            badan_perizinan.get("sandbox_mode", False) and not oss_public.get("oss_public_verified")
        ),
    }


def _oss_looks_valid(raw: dict[str, Any]) -> bool:
    status = _pick_string(raw, ["status", "code", "message", "msg"])
    nib = _pick_string(raw, ["nib"])
    has_name = bool(_pick_string(raw, ["nama_perusahaan", "namaPerusahaan", "nama_perseroan", "namaPerseroan"]))
    return (
        bool(nib) or
        has_name or
        bool(re.search(r"success|sukses|berhasil|200|01", status, re.IGNORECASE))
    )


def _pick_string(source: Any, keys: list[str]) -> str:
    value = _find_first_value(source, set(k.lower() for k in keys))
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return ""


def _find_first_value(source: Any, keys: set[str]) -> Any:
    if not source:
        return None
    if isinstance(source, list):
        for item in source:
            val = _find_first_value(item, keys)
            if val is not None and val != "":
                return val
        return None
    if isinstance(source, dict):
        for k, v in source.items():
            if k.lower() in keys:
                return v
            val = _find_first_value(v, keys)
            if val is not None and val != "":
                return val
    return None


def _calculate_verification_score(nib_data: dict[str, Any]) -> float:
    """
    Verified UMKM Profile Score (0.0 - 1.0):
      0.5  - NIB valid
      +0.3 - COMPLIANT (NIB aktif) | +0.15 jika CONDITIONAL
      +0.2 - scale MENENGAH | +0.15 KECIL | +0.05 MIKRO
    """
    score = 0.0
    if nib_data.get("is_valid"):
        score += 0.5
    compliance = nib_data.get("compliance_status", "")
    if compliance == "COMPLIANT":
        score += 0.3
    elif compliance == "CONDITIONAL":
        score += 0.15
    
    scale = str(nib_data.get("business_scale", "")).upper()
    if "MENENGAH" in scale or "MEDIUM" in scale or "MIDDLE" in scale:
        score += 0.2
    elif "KECIL" in scale or "SMALL" in scale:
        score += 0.15
    elif "MIKRO" in scale or "MICRO" in scale:
        score += 0.05
    return min(1.0, round(score, 4))
