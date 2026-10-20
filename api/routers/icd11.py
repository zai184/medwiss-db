"""ICD-11 token proxy for the embedded ECT browser."""

from fastapi import APIRouter

from api.config import settings
from api.services.icd11 import ICD11Client

router = APIRouter(tags=["icd11"])


@router.get("/icd11/token")
async def get_icd11_token(
) -> dict[str, str | None]:
    """Return an OAuth2 token for the WHO ICD-11 ECT browser.

    The ECT calls this via its ``getNewTokenFunction`` callback.
    """
    client = ICD11Client(
        client_id=settings.icd11_client_id,
        client_secret=settings.icd11_client_secret,
    )
    if not client.is_configured:
        return {"error": "ICD-11 API not configured", "token": None}

    token = await client._ensure_token()  # noqa: SLF001
    return {"token": token}
