import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import api from '../api/client'
import './Auth.css'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [form, setForm] = useState({ new_password: '', confirm_password: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)
  const [validToken, setValidToken] = useState(null)

  useEffect(() => {
    if (!token) { setValidToken(false); return }
    api.get(`/api/auth/reset-password/validate?token=${token}`)
      .then(() => setValidToken(true))
      .catch(() => setValidToken(false))
  }, [token])

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post('/api/auth/reset-password', { token, ...form })
      setSuccess('Password reimpostata con successo! Reindirizzamento al login...')
      setTimeout(() => navigate('/'), 2500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore durante il reset')
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
        <h1 className="auth-title">Nuova password</h1>

        {validToken === null && <p className="auth-sub">Verifica token...</p>}

        {validToken === false && (
          <>
            <div className="auth-error">Il link non è valido o è scaduto.</div>
            <div className="auth-footer"><Link to="/">← Torna al login</Link></div>
          </>
        )}

        {validToken === true && !success && (
          <>
            <p className="auth-sub">Scegli una nuova password per il tuo account.</p>
            {error && <div className="auth-error">{error}</div>}
            <form onSubmit={submit}>
              <div className="field">
                <label>Nuova password</label>
                <input type="password" value={form.new_password}
                  onChange={e => setForm({...form, new_password: e.target.value})}
                  required placeholder="••••••••" />
              </div>
              <div className="field">
                <label>Conferma password</label>
                <input type="password" value={form.confirm_password}
                  onChange={e => setForm({...form, confirm_password: e.target.value})}
                  required placeholder="••••••••" />
              </div>
              <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? 'Salvataggio...' : 'Imposta nuova password →'}
              </button>
            </form>
          </>
        )}

        {success && <div className="auth-success">{success}</div>}
      </div>
    </div>
  )
}
