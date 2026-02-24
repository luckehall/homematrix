import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import './Auth.css'

export default function Profile() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ current_password:'', new_password:'', confirm:'' })
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async e => {
    e.preventDefault()
    if (form.new_password !== form.confirm) {
      setError('Le password non coincidono'); return
    }
    setBusy(true); setError('')
    try {
      await api.post('/api/auth/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
      })
      setMsg('Password aggiornata! Effettua di nuovo il login.')
      setTimeout(async () => { await logout(); navigate('/') }, 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore aggiornamento password')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-bg" />
      <div className="auth-card">
        <div className="auth-logo">
          <div className="logo-icon">⌂</div>
          <div className="logo-text">Home<span>Matrix</span></div>
        </div>
        <h1 className="auth-title">Cambia password</h1>
        {msg && <div style={{background:'rgba(0,229,192,.1)',border:'1px solid rgba(0,229,192,.3)',borderRadius:'10px',padding:'12px 16px',fontSize:'13px',color:'#00e5c0',marginBottom:'16px'}}>{msg}</div>}
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field"><label>Password attuale</label>
            <input type="password" value={form.current_password} onChange={e=>setForm({...form,current_password:e.target.value})} required placeholder="••••••••" />
          </div>
          <div className="field"><label>Nuova password</label>
            <input type="password" value={form.new_password} onChange={e=>setForm({...form,new_password:e.target.value})} required placeholder="••••••••" />
          </div>
          <div className="field"><label>Conferma nuova password</label>
            <input type="password" value={form.confirm} onChange={e=>setForm({...form,confirm:e.target.value})} required placeholder="••••••••" />
          </div>
          <button className="btn-primary" type="submit" disabled={busy}>{busy ? 'Aggiornamento...' : 'Aggiorna password'}</button>
        </form>
        <div className="auth-footer">
          <span style={{cursor:'pointer',color:'var(--accent)'}} onClick={() => navigate('/dashboard')}>← Torna alla dashboard</span>
        </div>
      </div>
    </div>
  )
}
