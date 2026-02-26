import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import './Admin.css'

export default function Admin() {
  const { user: currentUser } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState('pending')
  const [pending, setPending] = useState([])
  const [users, setUsers] = useState([])
  const [hosts, setHosts] = useState([])
  const [roles, setRoles] = useState([])
  const [userRoles, setUserRoles] = useState({}) // { userId: [{assignment_id, role_id, role_name}] }
  const [msg, setMsg] = useState('')

  const [newUser, setNewUser] = useState({ email:'', full_name:'', password:'', is_admin:false })
  const [newHost, setNewHost] = useState({ name:'', base_url:'', token:'', description:'' })
  const [newRole, setNewRole] = useState({ name:'', description:'' })
  const [resetPwd, setResetPwd] = useState({})
  const [assignRole, setAssignRole] = useState({})
  const [newPerm, setNewPerm] = useState({})

  const loadViews = async () => {
    const r = await api.get('/api/admin/views')
    setViews(r.data)
  }

  const createView = async e => {
    e.preventDefault()
    await api.post('/api/admin/views', newView)
    notify('Vista creata ✓')
    setNewView({role_id:'', host_id:'', title:''})
    loadViews()
  }

  const deleteView = async id => {
    if (!confirm('Eliminare la vista?')) return
    await api.delete(`/api/admin/views/${id}`)
    notify('Vista eliminata')
    loadViews()
  }

  const addWidget = async (viewId) => {
    const w = newWidget[viewId] || {}
    if (!w.entity_id) return
    await api.post(`/api/admin/views/${viewId}/widgets`, w)
    notify('Widget aggiunto ✓')
    setNewWidget({...newWidget, [viewId]: {}})
    loadViews()
  }

  const updateWidget = async (viewId, widgetId, data) => {
    await api.patch(`/api/admin/views/${viewId}/widgets/${widgetId}`, data)
    notify('Widget aggiornato ✓')
    setEditingWidget(null)
    loadViews()
  }

  const deleteWidget = async (viewId, widgetId) => {
    await api.delete(`/api/admin/views/${viewId}/widgets/${widgetId}`)
    loadViews()
  }

  const load = async () => {
    const [p, u, h, r] = await Promise.all([
      api.get('/api/admin/users/pending'),
      api.get('/api/admin/users'),
      api.get('/api/admin/hosts'),
      api.get('/api/admin/roles'),
    ])
    setPending(p.data); setUsers(u.data); setHosts(h.data); setRoles(r.data)
    // Carica ruoli per ogni utente
    const rolesMap = {}
    await Promise.all(u.data.map(async user => {
      const res = await api.get(`/api/admin/users/${user.id}/roles`)
      rolesMap[user.id] = res.data
    }))
    setUserRoles(rolesMap)
  }

  useEffect(() => { load() }, [])

  const notify = m => { setMsg(m); setTimeout(() => setMsg(''), 3000) }

  const approve  = async id => { await api.post(`/api/admin/users/${id}/approve`); notify('Utente approvato ✓'); load() }
  const revoke   = async id => { await api.post(`/api/admin/users/${id}/revoke`); notify('Utente revocato'); load() }
  const mkAdmin  = async id => { await api.post(`/api/admin/users/${id}/make-admin`); notify('Utente promosso admin ✓'); load() }
  const rmAdmin  = async id => { await api.post(`/api/admin/users/${id}/remove-admin`); notify('Privilegi admin revocati'); load() }
  const toggle2fa = async id => { const r = await api.post(`/api/admin/users/${id}/require-2fa`); notify(r.data.message); load() }

  const createUser = async e => {
    e.preventDefault()
    await api.post('/api/admin/users', newUser)
    notify(`Utente ${newUser.email} creato ✓`)
    setNewUser({ email:'', full_name:'', password:'', is_admin:false })
    load()
  }

  const doResetPwd = async (userId) => {
    const pwd = resetPwd[userId]
    if (!pwd) return
    await api.post(`/api/admin/users/${userId}/reset-password`, { new_password: pwd })
    notify('Password reimpostata ✓')
    setResetPwd({...resetPwd, [userId]: ''})
  }

  const doAssignRole = async (userId) => {
    const roleId = assignRole[userId]
    if (!roleId) return
    try {
      await api.post(`/api/admin/roles/${roleId}/assign/${userId}`)
      notify('Ruolo assegnato ✓')
      setAssignRole({...assignRole, [userId]: ''})
      load()
    } catch (e) {
      notify(e.response?.data?.detail || 'Errore assegnazione')
    }
  }

  const doRemoveRole = async (userId, roleId) => {
    await api.delete(`/api/admin/users/${userId}/roles/${roleId}`)
    notify('Ruolo rimosso')
    load()
  }

  const addHost = async e => {
    e.preventDefault()
    await api.post('/api/admin/hosts', newHost)
    notify(`Host '${newHost.name}' aggiunto ✓`)
    setNewHost({ name:'', base_url:'', token:'', description:'' })
    load()
  }

  const [editHost, setEditHost] = useState(null)
  const [editHostData, setEditHostData] = useState({})
  const updateHost = async id => {
    await api.patch(`/api/admin/hosts/${id}`, editHostData)
    notify('Host aggiornato ✓')
    setEditHost(null)
    setEditHostData({})
    load()
  }
  const toggleHost  = async id => { await api.patch(`/api/admin/hosts/${id}/toggle`); load() }
  const deleteHost  = async id => { if (!confirm('Eliminare?')) return; await api.delete(`/api/admin/hosts/${id}`); load() }

  const createRole = async e => {
    e.preventDefault()
    await api.post('/api/admin/roles', newRole)
    notify(`Ruolo '${newRole.name}' creato ✓`)
    setNewRole({ name:'', description:'' })
    load()
  }

  const toggleRole2fa = async (roleId) => {
    const r = await api.patch(`/api/admin/roles/${roleId}/require-2fa`)
    notify(r.data.message)
    load()
  }

  const addPerm = async (roleId) => {
    const p = newPerm[roleId] || {}
    if (!p.host_id) return
    await api.post(`/api/admin/roles/${roleId}/permissions`, {
      host_id: p.host_id,
      allowed_domains: p.domains?.length ? p.domains : null,
      allowed_entities: p.entities?.length ? p.entities : null,
    })
    notify('Permesso aggiunto ✓')
    setNewPerm({...newPerm, [roleId]: {}})
    load()
  }

  const delPerm = async (roleId, permId) => {
    await api.delete(`/api/admin/roles/${roleId}/permissions/${permId}`)
    notify('Permesso rimosso')
    load()
  }

  return (
    <div className="admin-layout">
      <div className="admin-header">
        <div className="admin-logo">
          <div className="logo-icon">⌂</div>
          <div className="logo-text">Home<span>Matrix</span> — Admin</div>
        </div>
        <button className="btn-back" onClick={() => navigate('/dashboard')}>← Dashboard</button>
      </div>

      {msg && <div className="admin-msg">{msg}</div>}

      <div className="admin-tabs">
        {[
          ['pending', `Richieste (${pending.length})`],
          ['users', 'Utenti'],
          ['create', 'Nuovo Utente'],
          ['hosts', 'Host HA'],
          ['roles', 'Ruoli & Permessi'],
          ['views', '🖥 Viste'],
        ].map(([t, label]) => (
          <div key={t} className={`admin-tab ${tab===t?'active':''}`} onClick={() => setTab(t)}>{label}</div>
        ))}
      </div>

      <div className="admin-content">

        {tab === 'pending' && (
          <div className="cards-grid">
            {pending.length === 0 && <div className="empty">Nessuna richiesta in attesa</div>}
            {pending.map(u => (
              <div key={u.id} className="user-card">
                <div className="user-avatar">{u.full_name[0]}</div>
                <div className="user-info">
                  <div className="user-name">{u.full_name}</div>
                  <div className="user-email">{u.email}</div>
                  {u.request_reason && <div className="user-reason">"{u.request_reason}"</div>}
                </div>
                <div className="user-actions">
                  <button className="btn-approve" onClick={() => approve(u.id)}>✓ Approva</button>
                  <button className="btn-deny" onClick={() => revoke(u.id)}>✕ Nega</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'users' && (
          <div className="cards-grid">
            {users.map(u => (
              <div key={u.id} className="user-card flexible">
                <div className="user-avatar">{u.full_name[0]}</div>
                <div className="user-info">
                  <div className="user-name">{u.full_name} {u.is_admin && <span className="badge-admin">admin</span>}</div>
                  <div className="user-email">{u.email}</div>
                  {/* Ruoli assegnati */}
                  <div className="user-roles">
                    {(userRoles[u.id] || []).map(r => (
                      <span key={r.role_id} className="role-chip">
                        {r.role_name}
                        <span className="role-chip-remove" onClick={() => doRemoveRole(u.id, r.role_id)}>✕</span>
                      </span>
                    ))}
                  </div>
                </div>
                <span className={`status-pill status-${u.status}`}>{u.status}</span>
                <div className="inline-actions">
                  {u.status === 'active' && !u.is_admin && (
                    <button className="btn-deny" onClick={() => revoke(u.id)}>Revoca</button>
                  )}
                  {u.status === 'revoked' && (
                    <button className="btn-approve" onClick={() => approve(u.id)}>Riattiva</button>
                  )}
                  {!u.is_admin && (
                    <button className="btn-toggle" onClick={() => mkAdmin(u.id)}>→ Admin</button>
                  )}
                  <button className={`btn-2fa btn-xs ${u.require_2fa ? 'active' : ''}`} onClick={() => toggle2fa(u.id)}>{u.require_2fa ? '🔐 2FA ON' : '🔓 2FA OFF'}</button>
                  {u.is_admin && String(u.id) !== String(currentUser?.id) && (
                    <button className="btn-deny btn-xs" onClick={() => rmAdmin(u.id)}>✕ Admin</button>
                  )}
                  <div className="assign-row">
                    <select className="select-sm"
                      value={assignRole[u.id] || ''}
                      onChange={e => setAssignRole({...assignRole, [u.id]: e.target.value})}>
                      <option value="">Assegna ruolo...</option>
                      {roles.filter(r => !(userRoles[u.id]||[]).find(ur => ur.role_id === r.id))
                        .map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                    <button className="btn-approve btn-xs" onClick={() => doAssignRole(u.id)}>+ Assegna</button>
                  </div>
                  <div className="assign-row">
                    <input className="input-sm" type="password" placeholder="Nuova password"
                      value={resetPwd[u.id] || ''}
                      onChange={e => setResetPwd({...resetPwd, [u.id]: e.target.value})} />
                    <button className="btn-toggle btn-xs" onClick={() => doResetPwd(u.id)}>Reset pwd</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'create' && (
          <form className="host-form" onSubmit={createUser}>
            <h3>Crea nuovo utente</h3>
            <div className="form-row">
              <div className="field"><label>Nome completo</label>
                <input value={newUser.full_name} onChange={e=>setNewUser({...newUser,full_name:e.target.value})} required placeholder="Mario Rossi" />
              </div>
              <div className="field"><label>Email</label>
                <input type="email" value={newUser.email} onChange={e=>setNewUser({...newUser,email:e.target.value})} required placeholder="mario@esempio.it" />
              </div>
            </div>
            <div className="form-row">
              <div className="field"><label>Password</label>
                <input type="password" value={newUser.password} onChange={e=>setNewUser({...newUser,password:e.target.value})} required placeholder="••••••••" />
              </div>
              <div className="field" style={{display:'flex',alignItems:'flex-end',paddingBottom:'4px'}}>
                <label style={{display:'flex',alignItems:'center',gap:'10px',cursor:'pointer'}}>
                  <input type="checkbox" checked={newUser.is_admin} onChange={e=>setNewUser({...newUser,is_admin:e.target.checked})} />
                  Utente amministratore
                </label>
              </div>
            </div>
            <button className="btn-primary" type="submit">+ Crea utente</button>
          </form>
        )}

        {tab === 'hosts' && (
          <>
            <form className="host-form" onSubmit={addHost}>
              <h3>Aggiungi Host Home Assistant</h3>
              <div className="form-row">
                <div className="field"><label>Nome</label><input value={newHost.name} onChange={e=>setNewHost({...newHost,name:e.target.value})} required placeholder="Casa Principale" /></div>
                <div className="field"><label>URL</label><input value={newHost.base_url} onChange={e=>setNewHost({...newHost,base_url:e.target.value})} required placeholder="https://ha.esempio.it" /></div>
              </div>
              <div className="field"><label>Long-lived Token HA</label><input value={newHost.token} onChange={e=>setNewHost({...newHost,token:e.target.value})} required placeholder="eyJhbGci..." /></div>
              <div className="field"><label>Descrizione</label><input value={newHost.description} onChange={e=>setNewHost({...newHost,description:e.target.value})} placeholder="Opzionale" /></div>
              <button className="btn-primary" type="submit">+ Aggiungi Host</button>
            </form>
            <div className="cards-grid" style={{marginTop:'24px'}}>
              {hosts.map(h => (
                <div key={h.id} className={`host-card ${h.active?'active':''}`}>
                  {editHost === h.id ? (
                    <div className="host-edit-form">
                      <div className="form-row">
                        <div className="field"><label>Nome</label><input defaultValue={h.name} onChange={e=>setEditHostData({...editHostData,name:e.target.value})} /></div>
                        <div className="field"><label>URL</label><input defaultValue={h.base_url} onChange={e=>setEditHostData({...editHostData,base_url:e.target.value})} /></div>
                      </div>
                      <div className="field"><label>Nuovo Token (lascia vuoto per non modificare)</label><input placeholder="eyJhbGci..." onChange={e=>setEditHostData({...editHostData,token:e.target.value})} /></div>
                      <div className="field"><label>Descrizione</label><input defaultValue={h.description} onChange={e=>setEditHostData({...editHostData,description:e.target.value})} /></div>
                      <div className="host-actions" style={{marginTop:'12px'}}>
                        <button className="btn-approve" onClick={() => updateHost(h.id)}>✓ Salva</button>
                        <button className="btn-toggle" onClick={() => { setEditHost(null); setEditHostData({}) }}>Annulla</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="host-icon">🏠</div>
                      <div className="host-info">
                        <div className="host-name">{h.name}</div>
                        <div className="host-url">{h.base_url}</div>
                        {h.description && <div className="host-desc">{h.description}</div>}
                      </div>
                      <div className="host-actions">
                        <span className={`status-pill ${h.active?'status-active':'status-revoked'}`}>{h.active?'attivo':'disattivo'}</span>
                        <button className="btn-toggle" onClick={() => { setEditHost(h.id); setEditHostData({}) }}>✎ Modifica</button>
                        <button className="btn-toggle" onClick={() => toggleHost(h.id)}>{h.active?'Disattiva':'Attiva'}</button>
                        <button className="btn-deny" onClick={() => deleteHost(h.id)}>Elimina</button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        {tab === 'views' && (
          <div className="views-admin">
            <form className="host-form" onSubmit={createView}>
              <h3>Crea nuova vista</h3>
              <div className="form-row">
                <div className="field"><label>Titolo</label>
                  <input value={newView.title} onChange={e=>setNewView({...newView,title:e.target.value})} required placeholder="es. Ingresso" />
                </div>
                <div className="field"><label>Ruolo</label>
                  <select value={newView.role_id} onChange={e=>setNewView({...newView,role_id:e.target.value})} required>
                    <option value="">Seleziona ruolo...</option>
                    {roles.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
                <div className="field"><label>Host HA</label>
                  <select value={newView.host_id} onChange={e=>setNewView({...newView,host_id:e.target.value})} required>
                    <option value="">Seleziona host...</option>
                    {hosts.map(h=><option key={h.id} value={h.id}>{h.name}</option>)}
                  </select>
                </div>
              </div>
              <button className="btn-primary" type="submit">+ Crea vista</button>
            </form>

            {views.map(view => (
              <div key={view.id} className="view-card">
                <div className="view-header">
                  <div>
                    <div className="view-title">{view.title}</div>
                    <div className="view-meta">
                      /view/{view.slug} · {roles.find(r=>r.id===view.role_id)?.name || view.role_id}
                    </div>
                  </div>
                  <div className="host-actions">
                    <a className="btn-toggle" href={`/view/${view.slug}`} target="_blank">↗ Apri</a>
                    <button className="btn-deny" onClick={()=>deleteView(view.id)}>Elimina</button>
                  </div>
                </div>

                <div className="widgets-list">
                  {view.widgets.map(w => (
                    <div key={w.id} className="widget-row">
                      {editingWidget?.widgetId === w.id ? (
                        <div className="widget-edit-row">
                          <input placeholder="Label" defaultValue={w.label || ''} onChange={e=>setEditingWidget({...editingWidget, label:e.target.value})} />
                          <input placeholder="Icona 🏠" defaultValue={w.icon || ''} onChange={e=>setEditingWidget({...editingWidget, icon:e.target.value})} style={{width:'80px'}} />
                          <input placeholder="Colore #hex" defaultValue={w.color || ''} onChange={e=>setEditingWidget({...editingWidget, color:e.target.value})} style={{width:'110px'}} />
                          <select defaultValue={w.size} onChange={e=>setEditingWidget({...editingWidget, size:e.target.value})}>
                            <option value="small">Piccolo</option>
                            <option value="medium">Medio</option>
                            <option value="large">Grande</option>
                          </select>
                          <button className="btn-approve btn-xs" onClick={()=>updateWidget(view.id, w.id, {label:editingWidget.label, icon:editingWidget.icon, color:editingWidget.color, size:editingWidget.size})}>✓</button>
                          <button className="btn-toggle btn-xs" onClick={()=>setEditingWidget(null)}>✕</button>
                        </div>
                      ) : (
                        <>
                          <span className="widget-icon">{w.icon || '▪'}</span>
                          <span className="widget-entity">{w.entity_id}</span>
                          <span className="widget-label">{w.label || '—'}</span>
                          <span className={`widget-size size-${w.size}`}>{w.size}</span>
                          {w.color && <span className="widget-color-dot" style={{background:w.color}} />}
                          <button className="btn-toggle btn-xs" onClick={()=>setEditingWidget({widgetId:w.id, label:w.label, icon:w.icon, color:w.color, size:w.size})}>✎</button>
                          <button className="btn-deny btn-xs" onClick={()=>deleteWidget(view.id, w.id)}>✕</button>
                        </>
                      )}
                    </div>
                  ))}
                </div>

                <div className="widget-add-row">
                  <input placeholder="entity_id (es. switch.luce_ingresso)"
                    value={newWidget[view.id]?.entity_id || ''}
                    onChange={e=>setNewWidget({...newWidget, [view.id]:{...newWidget[view.id], entity_id:e.target.value}})} />
                  <input placeholder="Label" style={{width:'140px'}}
                    value={newWidget[view.id]?.label || ''}
                    onChange={e=>setNewWidget({...newWidget, [view.id]:{...newWidget[view.id], label:e.target.value}})} />
                  <input placeholder="Icona" style={{width:'70px'}}
                    value={newWidget[view.id]?.icon || ''}
                    onChange={e=>setNewWidget({...newWidget, [view.id]:{...newWidget[view.id], icon:e.target.value}})} />
                  <input placeholder="#colore" style={{width:'100px'}}
                    value={newWidget[view.id]?.color || ''}
                    onChange={e=>setNewWidget({...newWidget, [view.id]:{...newWidget[view.id], color:e.target.value}})} />
                  <select value={newWidget[view.id]?.size || 'medium'}
                    onChange={e=>setNewWidget({...newWidget, [view.id]:{...newWidget[view.id], size:e.target.value}})}>
                    <option value="small">Piccolo</option>
                    <option value="medium">Medio</option>
                    <option value="large">Grande</option>
                  </select>
                  <button className="btn-approve btn-xs" onClick={()=>addWidget(view.id)}>+ Widget</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'roles' && (
          <>
            <form className="host-form" onSubmit={createRole} style={{marginBottom:'24px'}}>
              <h3>Crea nuovo ruolo</h3>
              <div className="form-row">
                <div className="field"><label>Nome ruolo</label>
                  <input value={newRole.name} onChange={e=>setNewRole({...newRole,name:e.target.value})} required placeholder="es. Famiglia" /></div>
                <div className="field"><label>Descrizione</label>
                  <input value={newRole.description} onChange={e=>setNewRole({...newRole,description:e.target.value})} placeholder="Opzionale" /></div>
              </div>
              <button className="btn-primary" type="submit">+ Crea ruolo</button>
            </form>

            {roles.map(role => (
              <RoleCard key={role.id} role={role} hosts={hosts}
                newPerm={newPerm[role.id] || {}}
                onPermChange={p => setNewPerm({...newPerm, [role.id]: p})}
                onAddPerm={() => addPerm(role.id)}
                onDelPerm={(permId) => delPerm(role.id, permId)} />
            ))}
          </>
        )}
      </div>
    </div>
  )
}

function RoleCard({ role, hosts, newPerm, onPermChange, onAddPerm, onDelPerm, onToggle2fa }) {
  const [haData, setHaData] = useState({ domains: [], entities: [] })
  const [loadingHa, setLoadingHa] = useState(false)
  const [domainSearch, setDomainSearch] = useState('')
  const [entitySearch, setEntitySearch] = useState('')

  const loadHaData = async (hostId) => {
    if (!hostId) return
    setLoadingHa(true)
    try {
      const res = await api.get(`/api/hosts/${hostId}/domains`)
      setHaData(res.data)
    } catch {}
    finally { setLoadingHa(false) }
  }

  const toggleDomain = (domain) => {
    const current = newPerm.domains || []
    const updated = current.includes(domain)
      ? current.filter(d => d !== domain)
      : [...current, domain]
    onPermChange({...newPerm, domains: updated})
  }

  const toggleEntity = (entity) => {
    const current = newPerm.entities || []
    const updated = current.includes(entity)
      ? current.filter(e => e !== entity)
      : [...current, entity]
    onPermChange({...newPerm, entities: updated})
  }

  const filteredDomains = haData.domains.filter(d => d.includes(domainSearch.toLowerCase()))
  const activeDomains = newPerm.domains || []
  const filteredEntities = haData.entities.filter(e => {
    const domain = e.split(".")[0]
    const matchesDomain = activeDomains.length === 0 || activeDomains.includes(domain)
    const matchesSearch = e.includes(entitySearch.toLowerCase())
    return matchesDomain && matchesSearch
  })

  return (
    <div className="role-card">
      <div className="role-header">
        <div>
          <div className="role-name">{role.name}</div>
          {role.description && <div className="role-desc">{role.description}</div>}
        </div>
      </div>

      {role.permissions.length > 0 && (
        <div className="perms-list">
          {role.permissions.map(p => {
            const host = hosts.find(h => h.id === p.host_id)
            return (
              <div key={p.id} className="perm-row">
                <span className="perm-host">🏠 {host?.name || p.host_id}</span>
                {p.allowed_domains && <span className="perm-tag">Domini: {p.allowed_domains.join(', ')}</span>}
                {p.allowed_entities && <span className="perm-tag">Entità: {p.allowed_entities.length} specifiche</span>}
                {!p.allowed_domains && !p.allowed_entities && <span className="perm-tag full">Accesso completo</span>}
                <button className="btn-deny btn-xs" onClick={() => onDelPerm(p.id)}>✕</button>
              </div>
            )
          })}
        </div>
      )}

      <div className="add-perm-section">
        <div className="add-perm-header">Aggiungi permesso</div>
        <div className="add-perm-row">
          <select className="select-sm" value={newPerm.host_id || ''}
            onChange={e => {
              onPermChange({...newPerm, host_id: e.target.value, domains:[], entities:[]})
              loadHaData(e.target.value)
            }}>
            <option value="">Seleziona host...</option>
            {hosts.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
          <button className="btn-approve btn-xs" onClick={onAddPerm}>+ Aggiungi permesso</button>
        </div>

        {newPerm.host_id && (
          <div className="perm-picker">
            {loadingHa && <div className="perm-loading">Caricamento entità da HA...</div>}

            {!loadingHa && haData.domains.length > 0 && (
              <div className="picker-col">
                <div className="picker-title">Domini <span className="picker-count">{(newPerm.domains||[]).length} selezionati</span></div>
                <input className="picker-search" placeholder="Cerca dominio..." value={domainSearch} onChange={e => setDomainSearch(e.target.value)} />
                <div className="picker-list">
                  {filteredDomains.map(d => (
                    <div key={d} className={`picker-item ${(newPerm.domains||[]).includes(d) ? 'selected' : ''}`}
                      onClick={() => toggleDomain(d)}>
                      <span className="picker-check">{(newPerm.domains||[]).includes(d) ? '✓' : ''}</span>
                      {d}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!loadingHa && haData.entities.length > 0 && (
              <div className="picker-col">
                <div className="picker-title">Entità specifiche <span className="picker-count">{(newPerm.entities||[]).length} selezionate</span></div>
                <input className="picker-search" placeholder="Cerca entity_id..." value={entitySearch} onChange={e => setEntitySearch(e.target.value)} />
                <div className="picker-list">
                  {filteredEntities.slice(0, 100).map(e => (
                    <div key={e} className={`picker-item ${(newPerm.entities||[]).includes(e) ? 'selected' : ''}`}
                      onClick={() => toggleEntity(e)}>
                      <span className="picker-check">{(newPerm.entities||[]).includes(e) ? '✓' : ''}</span>
                      {e}
                    </div>
                  ))}
                  {filteredEntities.length > 100 && <div className="picker-more">+{filteredEntities.length - 100} altri — affina la ricerca</div>}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
