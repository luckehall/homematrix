import { Link } from 'react-router-dom'
import './Auth.css'

export default function GooglePending() {
  return (
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
}
