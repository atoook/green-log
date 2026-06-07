from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings

router = APIRouter(tags=["warmup"])


@router.get("/warmup")
def warmup(
    settings: Annotated[Settings, Depends(get_settings)],
    warmup_key: Annotated[str | None, Header(alias="X-Warmup-Key")] = None,
) -> dict[str, str]:
    expected_key = settings.warmup_key_value
    if expected_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Warmup is not configured",
        )
    if warmup_key is None or not compare_digest(warmup_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return {"status": "ok"}
