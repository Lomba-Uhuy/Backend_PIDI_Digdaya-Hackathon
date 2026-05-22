"""Internal-service request context — read trusted headers from gateway."""
from __future__ import annotations

from typing import Annotated

from fastapi import Header

from matching_service.core.exceptions import AuthenticationError


async def get_user_id(
    x_user_id: Annotated[str | None, Header(alias="x-user-id")] = None,
) -> str:
    if not x_user_id:
        raise AuthenticationError("Missing x-user-id header (gateway must inject this)")
    return x_user_id


UserId = Annotated[str, ...]