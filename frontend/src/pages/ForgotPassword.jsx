import { useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import './Auth.css'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.post('/api/auth/forgot-password', { email })
      setSent(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore')
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
        <h1 className="auth-title">Password dimenticata</h1>

        {!sent ? (
          <>
            <p className="auth-sub">Inserisci la tua email e ti invieremo le istruzioni per reimpostare la password.</p>
            {error && <div className="auth-error">{error}</div>}
            <form onSubmit={submit}>
              <div className="field">
                <label>Email</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  required placeholder="nome@esempio.it" autoFocus />
              </div>
              <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? 'Invio...' : 'Invia istruzioni →'}
              </button>
            </form>
            <div className="auth-footer">
              <Link to="/">← Torna al login</Link>
            </div>
          </>
        ) : (
          <>
            <div className="auth-success">
              ✉ Email inviata! Controlla la tua casella di posta e segui le istruzioni.
            </div>
            <p className="auth-sub">Il link scade in 30 minuti. Controlla anche la cartella spam.</p>
            <div className="auth-footer">
              <Link to="/">← Torna al login</Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
