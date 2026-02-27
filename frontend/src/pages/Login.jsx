import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import './Auth.css'

export default function Login() {
  const { login, user, loading, loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useState(() => new URLSearchParams(window.location.search))

  // Gestisci redirect dopo Google OAuth
  useState(() => {
    const googleToken = searchParams.get('google_token')
    const googlePending = searchParams.get('google')
    if (googleToken) {
      loginWithToken(googleToken).then(() => {
        window.history.replaceState({}, '', '/')
      })
    } else if (googlePending === 'pending') {
      setError("Account in attesa di approvazione da parte dell'amministratore.")
      window.history.replaceState({}, '', '/')
    }
  })
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
            <div className="auth-divider"><span>oppure</span></div>
            <a href="https://homematrix.iotzator.com/api/auth/google/login" className="btn-google">
              <svg width="18" height="18" viewBox="0 0 18 18"><path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18z"/><path fill="#34A353" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17z"/><path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07z"/><path fill="#EA4335" d="M8.98 4.18c1.17 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.31z"/></svg>
              Accedi con Google
            </a>
            <div className="auth-footer">
              <Link to="/forgot-password">Password dimenticata?</Link>
            </div>
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
