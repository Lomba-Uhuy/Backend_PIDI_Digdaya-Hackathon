"""Request context middleware."""
from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from comms_service.core.logging import request_id_ctx, tenant_id_ctx, user_id_ctx

log = structlog.get_logger("comms.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or str(uuid4())
        uid = request.headers.get("x-user-id")
        tid = request.headers.get("x-tenant-id")
        r_t = request_id_ctx.set(rid)
        u_t = user_id_ctx.set(uid)
        t_t = tenant_id_ctx.set(tid)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            log.exception(
                "request.failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            raise
        else:
            response.headers["x-request-id"] = rid
            log.info(
                "request.completed",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            return response
        finally:
            request_id_ctx.reset(r_t)
            user_id_ctx.reset(u_t)
            tenant_id_ctx.reset(t_t)