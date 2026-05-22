"""Per-request context middleware.

Internal trust contract: gateway injects x-user-id, x-tenant-id, x-request-id
on every authenticated request. We honor those headers and never accept user
identity from request body.
"""
from __future__ import annotations

import time
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from matching_service.core.logging import request_id_ctx, tenant_id_ctx, user_id_ctx

log = structlog.get_logger("matching.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or str(uuid4())
        uid = request.headers.get("x-user-id")
        tid = request.headers.get("x-tenant-id")
        r_token = request_id_ctx.set(rid)
        u_token = user_id_ctx.set(uid)
        t_token = tenant_id_ctx.set(tid)
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
            request_id_ctx.reset(r_token)
            user_id_ctx.reset(u_token)
            tenant_id_ctx.reset(t_token)