from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional
import httpx, re
from app.db import get_db
from app.models import User, CustomView, ViewWidget, UserRole, HAHost
from app.auth.router import get_current_user, require_admin
from app.crypto import decrypt

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
    host_id: str
    title: str
    order: int = 0

class ViewUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None

class WidgetCreate(BaseModel):
    entity_id: str
    label: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    size: str = "medium"
    order: int = 0

class WidgetUpdate(BaseModel):
    label: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    order: Optional[int] = None

@router.get("/admin/views")
async def list_views(db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    result = await db.execute(select(CustomView).options(selectinload(CustomView.widgets)).order_by(CustomView.order))
    views = result.scalars().all()
    out = []
    for v in views:
        widgets = [{"id": str(w.id), "entity_id": w.entity_id, "label": w.label,
                    "icon": w.icon, "color": w.color, "size": w.size, "order": w.order}
                   for w in v.widgets]
        out.append({"id": str(v.id), "role_id": str(v.role_id), "host_id": str(v.host_id),
                    "title": v.title, "slug": v.slug, "order": v.order,
                    "created_at": v.created_at, "widgets": widgets})
    return out

@router.post("/admin/views", status_code=201)
async def create_view(data: ViewCreate, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    import uuid
    slug = make_slug(data.title)
    existing = await db.execute(select(CustomView).where(CustomView.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"
    view = CustomView(role_id=data.role_id, host_id=data.host_id,
                      title=data.title, slug=slug, order=data.order)
    db.add(view)
    await db.commit()
    return {"id": str(view.id), "slug": view.slug, "message": "Vista creata"}

@router.patch("/admin/views/{view_id}")
async def update_view(view_id: str, data: ViewUpdate, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    if data.title is not None: view.title = data.title
    if data.order is not None: view.order = data.order
    await db.commit()
    return {"message": "Vista aggiornata"}

@router.delete("/admin/views/{view_id}")
async def delete_view(view_id: str, db: AsyncSession = Depends(get_db),
                      admin: User = Depends(require_admin)):
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    await db.delete(view)
    await db.commit()
    return {"message": "Vista eliminata"}

@router.post("/admin/views/{view_id}/widgets", status_code=201)
async def add_widget(view_id: str, data: WidgetCreate, db: AsyncSession = Depends(get_db),
                     admin: User = Depends(require_admin)):
    view = await db.get(CustomView, view_id)
    if not view: raise HTTPException(404, "Vista non trovata")
    widget = ViewWidget(view_id=view.id, entity_id=data.entity_id, label=data.label,
                        icon=data.icon, color=data.color, size=data.size, order=data.order)
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
    if data.size is not None: widget.size = data.size
    if data.order is not None: widget.order = data.order
    await db.commit()
    return {"message": "Widget aggiornato"}

@router.delete("/admin/views/{view_id}/widgets/{widget_id}")
async def delete_widget(view_id: str, widget_id: str, db: AsyncSession = Depends(get_db),
                        admin: User = Depends(require_admin)):
    widget = await db.get(ViewWidget, widget_id)
    if not widget: raise HTTPException(404, "Widget non trovato")
    await db.delete(widget)
    await db.commit()
    return {"message": "Widget eliminato"}

@router.get("/views/my")
async def get_my_views(db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    role_ids = await get_user_role_ids(user, db)
    if not role_ids:
        return []
    result = await db.execute(
        select(CustomView).options(selectinload(CustomView.widgets)).where(CustomView.role_id.in_(role_ids)).order_by(CustomView.order))
    views = result.scalars().all()
    return [{"id": str(v.id), "title": v.title, "slug": v.slug, "order": v.order} for v in views]

@router.get("/views/{slug}")
async def get_view(slug: str, db: AsyncSession = Depends(get_db),
                   user: User = Depends(get_current_user)):
    result = await db.execute(select(CustomView).options(selectinload(CustomView.widgets)).where(CustomView.slug == slug))
    view = result.scalar_one_or_none()
    if not view: raise HTTPException(404, "Vista non trovata")
    role_ids = await get_user_role_ids(user, db)
    if not user.is_admin and str(view.role_id) not in role_ids:
        raise HTTPException(403, "Accesso negato")
    host = await db.get(HAHost, view.host_id)
    if not host: raise HTTPException(404, "Host non trovato")
    entity_ids = [w.entity_id for w in view.widgets]
    states = {}
    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        for eid in entity_ids:
            try:
                resp = await client.get(
                    f"{host.base_url}/api/states/{eid}",
                    headers={"Authorization": f"Bearer {decrypt(host.token)}"})
                if resp.status_code == 200:
                    states[eid] = resp.json()
            except: pass
    widgets = [{"id": str(w.id), "entity_id": w.entity_id,
                "label": w.label or states.get(w.entity_id, {}).get("attributes", {}).get("friendly_name", w.entity_id),
                "icon": w.icon, "color": w.color, "size": w.size, "order": w.order,
                "state": states.get(w.entity_id, {}).get("state", "unavailable"),
                "attributes": states.get(w.entity_id, {}).get("attributes", {})}
               for w in view.widgets]
    return {"id": str(view.id), "title": view.title, "slug": view.slug,
            "host_id": str(view.host_id), "widgets": widgets}
