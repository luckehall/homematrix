import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import './Admin.css'

export default function Admin() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('pending')
  const [pending, setPending] = useState([])
  const [users, setUsers] = useState([])
  const [hosts, setHosts] = useState([])
  const [newHost, setNewHost] = useState({ name:'', base_url:'', token:'', description:'' })
  const [msg, setMsg] = useState('')

  const load = async () => {
    const [p, u, h] = await Promise.all([
      api.get('/api/admin/users/pending'),
      api.get('/api/admin/users'),
      api.get('/api/admin/hosts'),
    ])
    setPending(p.data)
    setUsers(u.data)
    setHosts(h.data)
  }

  useEffect(() => { load() }, [])

  const approve = async id => {
    await api.post(`/api/admin/users/${id}/approve`)
    setMsg('Utente approvato ✓')
    load()
  }

  const revoke = async id => {
    await api.post(`/api/admin/users/${id}/revoke`)
    setMsg('Utente revocato')
    load()
  }

  const addHost = async e => {
    e.preventDefault()
    await api.post('/api/admin/hosts', newHost)
    setMsg(`Host '${newHost.name}' aggiunto ✓`)
    setNewHost({ name:'', base_url:'', token:'', description:'' })
    load()
  }

  const toggleHost = async id => {
    await api.patch(`/api/admin/hosts/${id}/toggle`)
    load()
  }

  const deleteHost = async id => {
    if (!confirm('Eliminare questo host?')) return
    await api.delete(`/api/admin/hosts/${id}`)
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

      {msg && <div className="admin-msg" onClick={() => setMsg('')}>{msg} ✕</div>}

      <div className="admin-tabs">
        {['pending','users','hosts'].map(t => (
          <div key={t} className={`admin-tab ${tab===t?'active':''}`} onClick={() => setTab(t)}>
            {t === 'pending' ? `Richieste (${pending.length})` : t === 'users' ? 'Utenti' : 'Host HA'}
          </div>
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
              <div key={u.id} className="user-card">
                <div className="user-avatar">{u.full_name[0]}</div>
                <div className="user-info">
                  <div className="user-name">{u.full_name} {u.is_admin && <span className="badge-admin">admin</span>}</div>
                  <div className="user-email">{u.email}</div>
                </div>
                <span className={`status-pill status-${u.status}`}>{u.status}</span>
                {u.status === 'active' && !u.is_admin && (
                  <button className="btn-deny" onClick={() => revoke(u.id)}>Revoca</button>
                )}
              </div>
            ))}
          </div>
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
                  <div className="host-icon">🏠</div>
                  <div className="host-info">
                    <div className="host-name">{h.name}</div>
                    <div className="host-url">{h.base_url}</div>
                    {h.description && <div className="host-desc">{h.description}</div>}
                  </div>
                  <div className="host-actions">
                    <span className={`status-pill ${h.active?'status-active':'status-revoked'}`}>{h.active?'attivo':'disattivo'}</span>
                    <button className="btn-toggle" onClick={() => toggleHost(h.id)}>{h.active?'Disattiva':'Attiva'}</button>
                    <button className="btn-deny" onClick={() => deleteHost(h.id)}>Elimina</button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
