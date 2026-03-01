import re, uuid, json as _json
import httpx
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db import get_db
from app.models import User, CustomView, ViewWidget, HAHost, RolePermission, UserRole
from app.auth.router import get_current_user, require_admin
from app.hosts.router import decrypt

router = APIRouter()

def make_slug(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')

async def get_user_role_ids(user: User, db: AsyncSession) -> list:
    result = await db.execute(select(UserRole).where(UserRole.user_id == user.id))
    return [str(ur.role_id) for ur in result.scalars().all()]

class ViewCreate(BaseModel):
    role_id: str
    title: str
    slug: Optional[str] = None
    order: int = 0

class ViewUpdate(BaseModel):
    title: Optional[str] = None

class WidgetCreate(BaseModel):
    entity_id: str
    label: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    bg_color: Optional[str] = None
    size: str = "medium"
    order: int = 0

class WidgetUpdate(BaseModel):
    label: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    bg_color: Optional[str] = None
    size: Optional[str] = None
    order: Optional[int] = None

@router.get("/admin/views")
async def list_views(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    result = await db.execute(select(CustomView).options(selectinload(CustomView.widgets)).order_by(CustomView.order))
    views = result.scalars().all()
    out = []
    for v in views:
        widgets = [{"id": str(w.id), "entity_id": w.entity_id, "label": w.label,
                    "icon": w.icon, "color": w.color, "bg_color": w.bg_color, "size": w.size, "order": w.order}
                   for w in sorted(v.widgets, key=lambda x: x.order)]
        out.append({"id": str(v.id), "role_id": str(v.role_id),
                    "title": v.title, "slug": v.slug, "order": v.order,
                    "created_at": v.created_at, "widgets": widgets})
    return out

@router.post("/admin/views", status_code=201)
async def create_view(data: ViewCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    slug = data.slug or make_slug(data.title)
    existing = await db.execute(select(CustomView).where(CustomView.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"
    view = CustomView(role_id=data.role_id, title=data.title, slug=slug, order=data.order)
    db.add(view)
    await db.commit()
    return {"id": str(view.id), "slug": view.slug}

@router.patch("/admin/views/{view_id}")
async def update_view(view_id: str, data: ViewUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    if data.title is not None: view.title = data.title
    await db.commit()
    return {"message": "Vista aggiornata"}

@router.delete("/admin/views/{view_id}")
async def delete_view(view_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    await db.delete(view)
    await db.commit()
    return {"message": "Vista eliminata"}

@router.get("/admin/views/{view_id}/entities")
async def get_view_entities(view_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    perm_result = await db.execute(select(RolePermission).where(RolePermission.role_id == view.role_id))
    perms = perm_result.scalars().all()
    host_ids = list(set(str(p.host_id) for p in perms))
    allowed_domains, allowed_entities = [], []
    for p in perms:
        if p.allowed_domains:
            try: allowed_domains += _json.loads(p.allowed_domains)
            except: allowed_domains += [d.strip() for d in p.allowed_domains.split(",") if d.strip()]
        if p.allowed_entities:
            try: allowed_entities += _json.loads(p.allowed_entities)
            except: allowed_entities += [e.strip() for e in p.allowed_entities.split(",") if e.strip()]
    def is_allowed(s):
        eid = s["entity_id"]
        domain = eid.split(".")[0]
        if eid in allowed_entities: return True
        if domain in allowed_domains: return True
        return not allowed_domains and not allowed_entities
    all_entities = []
    async with httpx.AsyncClient(verify=False, timeout=15) as client:
        for hid in host_ids:
            host = await db.get(HAHost, hid)
            if not host or not host.active: continue
            try:
                resp = await client.get(f"{host.base_url}/api/states",
                                        headers={"Authorization": f"Bearer {decrypt(host.token)}"})
                if resp.status_code != 200: continue
                states = resp.json()
                all_entities += [{"entity_id": s["entity_id"],
                                   "friendly_name": s.get("attributes", {}).get("friendly_name", s["entity_id"])}
                                  for s in states if is_allowed(s)]
            except: continue
    seen, unique = set(), []
    for e in sorted(all_entities, key=lambda x: x["entity_id"]):
        if e["entity_id"] not in seen:
            seen.add(e["entity_id"])
            unique.append(e)
    return {"entities": unique}

@router.post("/admin/views/{view_id}/widgets", status_code=201)
async def add_widget(view_id: str, data: WidgetCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    from sqlalchemy import func
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    max_order = await db.scalar(select(func.max(ViewWidget.order)).where(ViewWidget.view_id == view.id))
    next_order = (max_order or -1) + 1
    widget = ViewWidget(view_id=view.id, entity_id=data.entity_id, label=data.label,
                        icon=data.icon, color=data.color, bg_color=data.bg_color, size=data.size, order=next_order)
    db.add(widget)
    await db.commit()
    return {"id": str(widget.id), "message": "Widget aggiunto"}

@router.patch("/admin/views/{view_id}/widgets/{widget_id}")
async def update_widget(view_id: str, widget_id: str, data: WidgetUpdate,
                        db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    widget = await db.get(ViewWidget, widget_id)
    if not widget: raise HTTPException(404, "Widget non trovato")
    if data.label is not None: widget.label = data.label
    if data.icon is not None: widget.icon = data.icon
    if data.color is not None: widget.color = data.color
    if data.bg_color is not None: widget.bg_color = data.bg_color
    if data.size is not None: widget.size = data.size
    if data.order is not None: widget.order = data.order
    await db.commit()
    return {"message": "Widget aggiornato"}

@router.delete("/admin/views/{view_id}/widgets/{widget_id}")
async def delete_widget(view_id: str, widget_id: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    widget = await db.get(ViewWidget, widget_id)
    if not widget: raise HTTPException(404, "Widget non trovato")
    await db.delete(widget)
    await db.commit()
    return {"message": "Widget eliminato"}

@router.get("/views/my")
async def get_my_views(current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    role_ids = await get_user_role_ids(current, db)
    if current.is_admin:
        result = await db.execute(select(CustomView).order_by(CustomView.order))
    else:
        result = await db.execute(select(CustomView).where(CustomView.role_id.in_(role_ids)).order_by(CustomView.order))
    views = result.scalars().all()
    return [{"id": str(v.id), "title": v.title, "slug": v.slug, "order": v.order} for v in views]

@router.get("/views/{slug}/states")
async def get_view_states(slug: str, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CustomView).options(selectinload(CustomView.widgets)).where(CustomView.slug == slug))
    view = result.scalar_one_or_none()
    if not view: raise HTTPException(404, "Vista non trovata")
    perm_result = await db.execute(select(RolePermission).where(RolePermission.role_id == view.role_id))
    perms = perm_result.scalars().all()
    host_ids = list(set(str(p.host_id) for p in perms))
    hosts = []
    for hid in host_ids:
        h = await db.get(HAHost, hid)
        if h and h.active: hosts.append(h)
    if not hosts: raise HTTPException(404, "Nessun host attivo per questo ruolo")
    widgets = sorted(view.widgets, key=lambda x: x.order)
    states = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for w in widgets:
            eid = w.entity_id
            for host in hosts:
                try:
                    resp = await client.get(f"{host.base_url}/api/states/{eid}",
                                            headers={"Authorization": f"Bearer {decrypt(host.token)}"})
                    if resp.status_code == 200:
                        d = resp.json()
                        states[eid] = {"state": d.get("state"), "attributes": d.get("attributes", {})}
                        break
                except: continue
    return {"view": {"id": str(view.id), "title": view.title, "slug": view.slug,
                     "widgets": [{"id": str(w.id), "entity_id": w.entity_id, "label": w.label,
                                  "icon": w.icon, "color": w.color, "bg_color": w.bg_color,
                                  "size": w.size, "order": w.order} for w in widgets]},
            "states": states}

@router.post("/views/{slug}/control")
async def control_entity(slug: str, payload: dict, current: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entity_id = payload.get("entity_id")
    service = payload.get("service")
    data = payload.get("data", {})
    result = await db.execute(select(CustomView).where(CustomView.slug == slug))
    view = result.scalar_one_or_none()
    if not view: raise HTTPException(404, "Vista non trovata")
    perm_result = await db.execute(select(RolePermission).where(RolePermission.role_id == view.role_id))
    perms = perm_result.scalars().all()
    host_ids = list(set(str(p.host_id) for p in perms))
    domain = entity_id.split(".")[0]
    async with httpx.AsyncClient(timeout=5) as client:
        for hid in host_ids:
            host = await db.get(HAHost, hid)
            if not host or not host.active: continue
            try:
                check = await client.get(f"{host.base_url}/api/states/{entity_id}",
                                         headers={"Authorization": f"Bearer {decrypt(host.token)}"})
                if check.status_code != 200: continue
                resp = await client.post(f"{host.base_url}/api/services/{domain}/{service}",
                                         headers={"Authorization": f"Bearer {decrypt(host.token)}"},
                                         json={"entity_id": entity_id, **data})
                return {"ok": True, "status": resp.status_code}
            except: continue
    raise HTTPException(500, "Impossibile controllare l'entita")
