import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './Auth.css'

export default function Login() {
  const { login, user, loading } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Auto-redirect se già loggato
  if (!loading && user) {
    navigate(user.is_admin ? '/admin' : '/dashboard')
  }

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore di accesso')
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
        <h1 className="auth-title">Accedi</h1>
        <p className="auth-sub">Sessione riconosciuta automaticamente se già autorizzato.</p>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="nome@esempio.it" />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••" />
          </div>
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? 'Accesso...' : 'Accedi →'}
          </button>
        </form>
        <div className="auth-footer">
          Non hai un account? <Link to="/register">Registrati</Link>
        </div>
      </div>
    </div>
  )
}
