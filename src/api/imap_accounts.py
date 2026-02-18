"""
Agent Optimus — IMAP/SMTP Accounts API (FASE 4C).
REST endpoints for managing universal email accounts.

Call path:
  POST   /api/v1/imap/accounts          → add_account (encrypted password)
  GET    /api/v1/imap/accounts          → list_accounts (no passwords)
  DELETE /api/v1/imap/accounts/{email}  → remove_account
  POST   /api/v1/imap/accounts/test     → test_connection
  GET    /api/v1/imap/providers         → list provider presets (for UI dropdown)
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.infra.auth_middleware import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/imap", tags=["imap"])


# ============================================
# Request / Response models
# ============================================

class AddAccountRequest(BaseModel):
    email: str
    password: str
    provider: str = "custom"
    imap_host: str = ""
    imap_port: int = 993
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""          # defaults to email if empty
    display_name: str = ""      # friendly label in UI


class TestConnectionRequest(BaseModel):
    email: str


# ============================================
# Endpoints
# ============================================

@router.get("/providers")
async def list_providers():
    """Return available provider presets for the UI dropdown."""
    from src.core.imap_service import PROVIDER_PRESETS
    return {
        k: {"label": v["label"], "imap_host": v["imap_host"], "imap_port": v["imap_port"],
            "smtp_host": v["smtp_host"], "smtp_port": v["smtp_port"]}
        for k, v in PROVIDER_PRESETS.items()
    }


@router.get("/accounts")
async def list_accounts(current_user: CurrentUser):
    """List all IMAP/SMTP accounts for the current user (no passwords)."""
    from src.core.imap_service import imap_service
    accounts = await imap_service.list_accounts(str(current_user.id))
    return {"accounts": accounts}


@router.post("/accounts")
async def add_account(req: AddAccountRequest, current_user: CurrentUser):
    """
    Add (or update) an IMAP/SMTP email account.
    Password is encrypted with Fernet before storage.
    """
    from src.core.imap_service import imap_service

    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=422, detail="Email inválido.")
    if not req.password:
        raise HTTPException(status_code=422, detail="Senha é obrigatória.")

    result = await imap_service.add_account(
        user_id=str(current_user.id),
        email=req.email,
        password=req.password,
        provider=req.provider,
        imap_host=req.imap_host,
        imap_port=req.imap_port,
        smtp_host=req.smtp_host,
        smtp_port=req.smtp_port,
        username=req.username,
        display_name=req.display_name,
    )

    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Erro ao adicionar conta."))

    return result


@router.delete("/accounts/{email:path}")
async def remove_account(email: str, current_user: CurrentUser):
    """Remove an IMAP/SMTP account."""
    from src.core.imap_service import imap_service
    ok = await imap_service.remove_account(str(current_user.id), email)
    if not ok:
        raise HTTPException(status_code=404, detail="Conta não encontrada ou erro ao remover.")
    return {"ok": True, "message": f"Conta {email} removida."}


@router.post("/accounts/test")
async def test_connection(req: TestConnectionRequest, current_user: CurrentUser):
    """Test IMAP connection for a configured account."""
    from src.core.imap_service import imap_service
    result = await imap_service.test_connection(str(current_user.id), req.email)
    return result
