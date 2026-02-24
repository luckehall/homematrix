import { useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import './Auth.css'

export default function Register() {
  const [form, setForm] = useState({ email: '', full_name: '', password: '', request_reason: '' })
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const update = e => setForm({ ...form, [e.target.name]: e.target.value })

  const submit = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await axios.post('https://homematrix.iotzator.com/api/auth/register', form)
      setDone(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore registrazione')
    } finally {
      setBusy(false)
    }
  }

  if (done) return (
    <div className="auth-shell">
      <div className="auth-bg" />
      <div className="auth-card">
        <div className="auth-logo">
          <div className="logo-icon">⌂</div>
          <div className="logo-text">Home<span>Matrix</span></div>
        </div>
        <div className="pending-icon">⌛</div>
        <h1 className="auth-title">Richiesta inviata!</h1>
        <p className="auth-sub">La tua registrazione è in attesa di approvazione. Riceverai una notifica quando il tuo account sarà attivato.</p>
        <p className="auth-sub" style={{marginTop:'12px'}}>Una volta approvato, torna su questo URL e verrai riconosciuto <strong>automaticamente</strong>.</p>
        <Link to="/" className="btn-primary" style={{display:'block',textAlign:'center',marginTop:'24px',textDecoration:'none'}}>Torna al login</Link>
      </div>
    </div>
  )

  return (
    <div className="auth-shell">
      <div className="auth-bg" />
      <div className="auth-card">
        <div className="auth-logo">
          <div className="logo-icon">⌂</div>
          <div className="logo-text">Home<span>Matrix</span></div>
        </div>
        <h1 className="auth-title">Crea account</h1>
        <p className="auth-sub">Accesso su approvazione amministratore.</p>
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Nome completo</label>
            <input name="full_name" value={form.full_name} onChange={update} required placeholder="Marco Rossi" />
          </div>
          <div className="field">
            <label>Email</label>
            <input name="email" type="email" value={form.email} onChange={update} required placeholder="nome@esempio.it" />
          </div>
          <div className="field">
            <label>Password</label>
            <input name="password" type="password" value={form.password} onChange={update} required placeholder="••••••••" />
          </div>
          <div className="field">
            <label>Motivo richiesta accesso</label>
            <input name="request_reason" value={form.request_reason} onChange={update} placeholder="Es. Gestione domotica abitazione principale" />
          </div>
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? 'Invio...' : 'Invia richiesta →'}
          </button>
        </form>
        <div className="auth-footer">
          Hai già un account? <Link to="/">Accedi</Link>
        </div>
      </div>
    </div>
  )
}
