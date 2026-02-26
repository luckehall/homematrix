import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import './Auth.css'

export default function Login() {
  const { login, user, loading, loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Step 2FA
  const [step, setStep] = useState('credentials') // 'credentials' | '2fa'
  const [tempToken, setTempToken] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [rememberDevice, setRememberDevice] = useState(false)

  if (!loading && user) {
    if (user.views?.length > 0 && !user.is_admin) navigate(`/view/${user.views[0].slug}`)
    else navigate('/dashboard')
  }

  const submitCredentials = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await login(email, password)
      if (result?.requires_2fa) {
        setTempToken(result.temp_token)
        setStep('2fa')
      }
      // Se non requires_2fa, login() gestisce già il redirect via AuthContext
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore di accesso')
    } finally {
      setBusy(false)
    }
  }

  const submit2fa = async e => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const r = await api.post('/api/auth/2fa/verify', {
        code: totpCode,
        remember_device: rememberDevice,
        device_name: navigator.userAgent
      }, { headers: { Authorization: `Bearer ${tempToken}` } })
      await loginWithToken(r.data.access_token)
    } catch (err) {
      setError(err.response?.data?.detail || 'Codice non valido')
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

        {step === 'credentials' && (
          <>
            <h1 className="auth-title">Accedi</h1>
            <p className="auth-sub">Sessione riconosciuta automaticamente se già autorizzato.</p>
            {error && <div className="auth-error">{error}</div>}
            <form onSubmit={submitCredentials}>
              <div className="field">
                <label>Email</label>
                <input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="nome@esempio.it" />
              </div>
              <div className="field">
                <label>Password</label>
                <input type="password" value={password} onChange={e=>setPassword(e.target.value)} required placeholder="••••••••" />
              </div>
              <button className="btn-primary" type="submit" disabled={busy}>
                {busy ? 'Accesso...' : 'Accedi →'}
              </button>
            </form>
            <div className="auth-footer">
              Non hai un account? <Link to="/register">Registrati</Link>
            </div>
          </>
        )}

        {step === '2fa' && (
          <>
            <h1 className="auth-title">Verifica 2FA</h1>
            <p className="auth-sub">Inserisci il codice a 6 cifre dalla tua app authenticator.</p>
            {error && <div className="auth-error">{error}</div>}
            <form onSubmit={submit2fa}>
              <div className="field">
                <label>Codice TOTP</label>
                <input type="text" value={totpCode} onChange={e=>setTotpCode(e.target.value.replace(/\D/,''))}
                  required placeholder="000000" maxLength={6} autoFocus
                  style={{letterSpacing:'0.3em', fontSize:'24px', textAlign:'center'}} />
              </div>
              <div className="field" style={{flexDirection:'row', alignItems:'center', gap:'10px'}}>
                <input type="checkbox" id="remember" checked={rememberDevice} onChange={e=>setRememberDevice(e.target.checked)} />
                <label htmlFor="remember" style={{margin:0, cursor:'pointer'}}>Ricorda questo dispositivo per 6 mesi</label>
              </div>
              <button className="btn-primary" type="submit" disabled={busy || totpCode.length !== 6}>
                {busy ? 'Verifica...' : 'Verifica →'}
              </button>
            </form>
            <div className="auth-footer">
              <span style={{cursor:'pointer', color:'var(--accent)'}} onClick={()=>{setStep('credentials');setError('')}}>← Torna al login</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
