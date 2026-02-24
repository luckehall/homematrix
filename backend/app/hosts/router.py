from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User, HAHost, UserRole, RolePermission
from app.auth.router import get_current_user
import httpx, json

router = APIRouter()

async def get_active_host(host_id: str, db: AsyncSession) -> HAHost:
    host = await db.get(HAHost, host_id)
    if not host or not host.active:
        raise HTTPException(404, "Host non trovato o non attivo")
    return host

async def get_user_permissions(user: User, host_id: str, db: AsyncSession):
    """Restituisce (allowed_domains, allowed_entities) per l'utente su questo host.
       None = nessun filtro (accesso totale). Admin = sempre accesso totale."""
    if user.is_admin:
        return None, None
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user.id))
    user_roles = result.scalars().all()
    if not user_roles:
        raise HTTPException(403, "Nessun ruolo assegnato")
    domains, entities = set(), set()
    has_host = False
    for ur in user_roles:
        perm_result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == ur.role_id,
                RolePermission.host_id == host_id))
        perms = perm_result.scalars().all()
        for p in perms:
            has_host = True
            if p.allowed_domains:
                domains.update(json.loads(p.allowed_domains))
            if p.allowed_entities:
                entities.update(json.loads(p.allowed_entities))
    if not has_host:
        raise HTTPException(403, "Accesso a questo host non autorizzato")
    return list(domains) if domains else None, list(entities) if entities else None

def filter_states(states: list, allowed_domains, allowed_entities) -> list:
    if allowed_domains is None and allowed_entities is None:
        return states
    result = []
    for s in states:
        domain = s.get("entity_id", "").split(".")[0]
        entity_id = s.get("entity_id", "")
        if allowed_entities and entity_id in allowed_entities:
            result.append(s)
        elif allowed_domains and domain in allowed_domains:
            result.append(s)
    return result

@router.get("/{host_id}/states")
async def get_states(host_id: str, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    allowed_domains, allowed_entities = await get_user_permissions(user, host_id, db)
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.get(f"{host.base_url}/api/states",
                                headers={"Authorization": f"Bearer {host.token}"})
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, "Errore comunicazione con HA")
    states = resp.json()
    return filter_states(states, allowed_domains, allowed_entities)

@router.get("/{host_id}/states/{entity_id:path}")
async def get_state(host_id: str, entity_id: str,
                    db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    allowed_domains, allowed_entities = await get_user_permissions(user, host_id, db)
    domain = entity_id.split(".")[0]
    if allowed_entities and entity_id not in allowed_entities:
        if not allowed_domains or domain not in allowed_domains:
            raise HTTPException(403, "Entità non autorizzata")
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.get(f"{host.base_url}/api/states/{entity_id}",
                                headers={"Authorization": f"Bearer {host.token}"})
    if resp.status_code == 404:
        raise HTTPException(404, f"Entità '{entity_id}' non trovata")
    return resp.json()

@router.post("/{host_id}/services/{domain}/{service}")
async def call_service(host_id: str, domain: str, service: str,
                       request: Request,
                       db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    allowed_domains, allowed_entities = await get_user_permissions(user, host_id, db)
    if allowed_domains and domain not in allowed_domains:
        raise HTTPException(403, f"Dominio '{domain}' non autorizzato")
    body = await request.json() if await request.body() else {}
    if allowed_entities and body.get("entity_id") and body["entity_id"] not in allowed_entities:
        raise HTTPException(403, "Entità non autorizzata")
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.post(
            f"{host.base_url}/api/services/{domain}/{service}",
            headers={"Authorization": f"Bearer {host.token}",
                     "Content-Type": "application/json"},
            json=body)
    if resp.status_code not in (200, 201):
        raise HTTPException(resp.status_code, "Errore chiamata servizio HA")
    return resp.json()

@router.get("/{host_id}/config")
async def get_ha_config(host_id: str, db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    async with httpx.AsyncClient(verify=True, timeout=10) as client:
        resp = await client.get(f"{host.base_url}/api/config",
                                headers={"Authorization": f"Bearer {host.token}"})
    return resp.json()

@router.get("/{host_id}/domains")
async def get_domains(host_id: str, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    host = await get_active_host(host_id, db)
    async with httpx.AsyncClient(verify=True, timeout=15) as client:
        resp = await client.get(f"{host.base_url}/api/states",
                                headers={"Authorization": f"Bearer {host.token}"})
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, "Errore comunicazione con HA")
    states = resp.json()
    domains = sorted(set(s["entity_id"].split(".")[0] for s in states))
    entities = sorted(s["entity_id"] for s in states)
    return {"domains": domains, "entities": entities}

@router.get("/")
async def get_my_hosts(db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Restituisce gli host accessibili all'utente corrente."""
    if user.is_admin:
        result = await db.execute(select(HAHost).where(HAHost.active == True))
        hosts = result.scalars().all()
    else:
        result = await db.execute(
            select(UserRole).where(UserRole.user_id == user.id))
        user_roles = result.scalars().all()
        host_ids = set()
        for ur in user_roles:
            perm_result = await db.execute(
                select(RolePermission).where(RolePermission.role_id == ur.role_id))
            perms = perm_result.scalars().all()
            for p in perms:
                host_ids.add(str(p.host_id))
        if not host_ids:
            return []
        result = await db.execute(
            select(HAHost).where(HAHost.active == True))
        hosts = [h for h in result.scalars().all() if str(h.id) in host_ids]
    return [{"id": str(h.id), "name": h.name, "description": h.description} for h in hosts]
