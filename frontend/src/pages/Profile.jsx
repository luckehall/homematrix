import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import './Auth.css'
import './Profile.css'

export default function Profile() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const force2fa = location.state?.force2fa

  const [pwdForm, setPwdForm] = useState({ current_password:'', new_password:'', confirm:'' })
  const [pwdMsg, setPwdMsg] = useState('')
  const [pwdError, setPwdError] = useState('')
  const [pwdBusy, setPwdBusy] = useState(false)

  const [totpStatus, setTotpStatus] = useState({ enabled: false, required: false })
  const [totpSetup, setTotpSetup] = useState(null) // { qr, secret }
  const [totpCode, setTotpCode] = useState('')
  const [totpMsg, setTotpMsg] = useState('')
  const [totpError, setTotpError] = useState('')
  const [totpBusy, setTotpBusy] = useState(false)
  const [disableCode, setDisableCode] = useState('')

  useEffect(() => {
    api.get('/api/auth/2fa/status').then(r => setTotpStatus(r.data)).catch(() => {})
  }, [])

  const submitPwd = async e => {
    e.preventDefault()
    if (pwdForm.new_password !== pwdForm.confirm) { setPwdError('Le password non coincidono'); return }
    setPwdBusy(true); setPwdError('')
    try {
      await api.post('/api/auth/change-password', {
        current_password: pwdForm.current_password,
        new_password: pwdForm.new_password,
      })
      setPwdMsg('Password aggiornata! Effettua di nuovo il login.')
      setTimeout(async () => { await logout(); navigate('/') }, 2000)
    } catch (err) {
      setPwdError(err.response?.data?.detail || 'Errore aggiornamento password')
    } finally { setPwdBusy(false) }
  }

  const startSetup = async () => {
    setTotpError(''); setTotpBusy(true)
    try {
      const { data } = await api.post('/api/auth/2fa/setup')
      console.log("TOTP setup data:", data); setTotpSetup(data)
    } catch (err) {
      setTotpError(err.response?.data?.detail || 'Errore setup 2FA')
    } finally { setTotpBusy(false) }
  }

  const confirmSetup = async () => {
    if (!totpCode) return
    setTotpError(''); setTotpBusy(true)
    try {
      await api.post('/api/auth/2fa/confirm', { code: totpCode })
      setTotpMsg('2FA attivato con successo ✓')
      setTotpSetup(null); setTotpCode('')
      setTotpStatus({ ...totpStatus, enabled: true })
    } catch (err) {
      setTotpError(err.response?.data?.detail || 'Codice non valido')
    } finally { setTotpBusy(false) }
  }

  const disable2fa = async () => {
    if (!disableCode) return
    setTotpError(''); setTotpBusy(true)
    try {
      await api.post('/api/auth/2fa/disable', { code: disableCode })
      setTotpMsg('2FA disabilitato')
      setDisableCode('')
      setTotpStatus({ ...totpStatus, enabled: false })
    } catch (err) {
      setTotpError(err.response?.data?.detail || 'Codice non valido')
    } finally { setTotpBusy(false) }
  }

  return (
    <div className="profile-shell">
      <div className="auth-bg" />

      <div className="profile-header">
        <div className="profile-header-logo">Home<span>Matrix</span></div>
        <button className="profile-logout-btn" onClick={async () => { await logout(); navigate("/") }}>⏻ Logout</button>
      </div>

      <div className="profile-grid">

        {/* ── CAMBIO PASSWORD ── */}
        <div className="auth-card">
          <div className="auth-logo">
            <div className="logo-icon">⌂</div>
            <div className="logo-text">Home<span>Matrix</span></div>
          </div>
          <h1 className="auth-title">Cambia password</h1>
          {pwdMsg && <div className="auth-success">{pwdMsg}</div>}
          {pwdError && <div className="auth-error">{pwdError}</div>}
          <form onSubmit={submitPwd}>
            <div className="field"><label>Password attuale</label>
              <input type="password" value={pwdForm.current_password} onChange={e=>setPwdForm({...pwdForm,current_password:e.target.value})} required placeholder="••••••••" />
            </div>
            <div className="field"><label>Nuova password</label>
              <input type="password" value={pwdForm.new_password} onChange={e=>setPwdForm({...pwdForm,new_password:e.target.value})} required placeholder="••••••••" />
            </div>
            <div className="field"><label>Conferma nuova password</label>
              <input type="password" value={pwdForm.confirm} onChange={e=>setPwdForm({...pwdForm,confirm:e.target.value})} required placeholder="••••••••" />
            </div>
            <button className="btn-primary" type="submit" disabled={pwdBusy}>{pwdBusy ? 'Aggiornamento...' : 'Aggiorna password'}</button>
          </form>
          <div className="auth-footer">
            <span style={{cursor:'pointer',color:'var(--accent)'}} onClick={() => navigate('/dashboard')}>← Torna alla dashboard</span>
          </div>
        </div>

        {/* ── 2FA ── */}
        <div className="auth-card">
          <div className="totp-header">
            <div className="totp-icon">🔐</div>
            <div>
              <h1 className="auth-title" style={{marginBottom:'4px'}}>Autenticazione a due fattori</h1>
              {force2fa && !totpStatus.enabled && <div className="auth-error" style={{marginTop:'8px'}}>⚠ Il tuo account richiede l'attivazione del 2FA per continuare.</div>}
              <div className="totp-badge-row">
                <span className={`totp-badge ${totpStatus.enabled ? 'on' : 'off'}`}>
                  {totpStatus.enabled ? '✓ Attivo' : '✗ Non attivo'}
                </span>
                {totpStatus.required && <span className="totp-badge required">⚠ Obbligatorio per il tuo ruolo</span>}
              </div>
            </div>
          </div>

          {totpMsg && <div className="auth-success">{totpMsg}</div>}
          {totpError && <div className="auth-error">{totpError}</div>}

          {!totpStatus.enabled && !totpSetup && (
            <>
              <p className="auth-sub">Usa un'app come <strong>Google Authenticator</strong> o <strong>Authy</strong> per generare codici temporanei.</p>
              <button className="btn-primary" onClick={startSetup} disabled={totpBusy}>
                {totpBusy ? 'Generazione...' : '+ Attiva 2FA'}
              </button>
            </>
          )}

          {!totpStatus.enabled && totpSetup && (
            <>
              <p className="auth-sub">Scansiona il QR code con la tua app authenticator, poi inserisci il codice per confermare.</p>
              <div className="qr-wrapper">
                <img src={`data:image/png;base64,${totpSetup.qr}`} alt="QR Code 2FA" className="qr-img" />
              </div>
              <p className="auth-sub" style={{marginTop:'8px'}}>Oppure inserisci manualmente il codice segreto:</p>
              <div className="secret-box">{totpSetup.secret}</div>
              <div className="field" style={{marginTop:'16px'}}>
                <label>Codice di verifica</label>
                <input type="text" inputMode="numeric" maxLength={6} value={totpCode}
                  onChange={e=>setTotpCode(e.target.value.replace(/\D/g,''))}
                  placeholder="000000" className="totp-input" />
              </div>
              <button className="btn-primary" onClick={confirmSetup} disabled={totpBusy || totpCode.length !== 6}>
                {totpBusy ? 'Verifica...' : 'Conferma e attiva'}
              </button>
            </>
          )}

          {totpStatus.enabled && (
            <>
              <p className="auth-sub">Il 2FA è attivo. Per disabilitarlo inserisci un codice valido dall'app.</p>
              <div className="field">
                <label>Codice authenticator</label>
                <input type="text" inputMode="numeric" maxLength={6} value={disableCode}
                  onChange={e=>setDisableCode(e.target.value.replace(/\D/g,''))}
                  placeholder="000000" className="totp-input" />
              </div>
              <button className="btn-deny-full" onClick={disable2fa} disabled={totpBusy || disableCode.length !== 6}>
                {totpBusy ? 'Disabilitazione...' : 'Disabilita 2FA'}
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  )
}
