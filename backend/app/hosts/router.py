from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User, HAHost
from app.auth.router import get_current_user
import httpx

router = APIRouter()

async def get_active_host(host_id: str, db: AsyncSession) -> HAHost:
    host = await db.get(HAHost, host_id)
    if not host or not host.active:
        raise HTTPException(404, "Host non trovato o non attivo")
    return host

@router.get("/{host_id}/states")
async def get_states(host_id: str, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.get(
            f"{host.base_url}/api/states",
            headers={"Authorization": f"Bearer {host.token}"}
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, "Errore comunicazione con HA")
    return resp.json()

@router.get("/{host_id}/states/{entity_id:path}")
async def get_state(host_id: str, entity_id: str,
                    db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.get(
            f"{host.base_url}/api/states/{entity_id}",
            headers={"Authorization": f"Bearer {host.token}"}
        )
    if resp.status_code == 404:
        raise HTTPException(404, f"Entità '{entity_id}' non trovata")
    return resp.json()

@router.post("/{host_id}/services/{domain}/{service}")
async def call_service(host_id: str, domain: str, service: str,
                       request: Request,
                       db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    body = await request.json() if await request.body() else {}
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.post(
            f"{host.base_url}/api/services/{domain}/{service}",
            headers={"Authorization": f"Bearer {host.token}",
                     "Content-Type": "application/json"},
            json=body
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(resp.status_code, "Errore chiamata servizio HA")
    return resp.json()

@router.get("/{host_id}/config")
async def get_ha_config(host_id: str, db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.get(
            f"{host.base_url}/api/config",
            headers={"Authorization": f"Bearer {host.token}"}
        )
    return resp.json()
