import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import './CustomView.css'

const DOMAIN_MAP = {
  switch: 'switch', light: 'light', input_boolean: 'switch',
  button: 'button', cover: 'cover', climate: 'climate',
  fan: 'fan', media_player: 'media_player',
  sensor: 'sensor', binary_sensor: 'binary_sensor',
}

function Widget({ w, onAction }) {
  const domain = w.entity_id.split('.')[0]
  const isOn = w.state === 'on' || w.state === 'open'
  const isButton = domain === 'button'
  const isSensor = domain === 'sensor'
  const isBinary = domain === 'binary_sensor'
  const isControllable = ['switch','light','input_boolean','cover','fan','climate','media_player'].includes(domain)

  const accentColor = w.color || 'var(--accent)'
  const widgetStyle = {}
  if (w.color) widgetStyle['--widget-accent'] = w.color
  if (w.bg_color) widgetStyle['background'] = w.bg_color

  return (
    <div className={`cv-widget cv-widget--${w.size} ${isOn ? 'is-on' : ''}`}
         style={widgetStyle}>
      <div className="cv-widget-icon">{w.icon || (isBinary ? (isOn ? '🟢' : '🔴') : isSensor ? '📊' : '💡')}</div>
      <div className="cv-widget-label">{w.label}</div>
      <div className={`cv-widget-state ${isOn ? 'state-on' : ''}`}>
        {isBinary ? (isOn ? 'Aperto' : 'Chiuso') : w.state}
        {w.attributes?.unit_of_measurement && ` ${w.attributes.unit_of_measurement}`}
      </div>
      {isButton && (
        <button className="cv-btn cv-btn--press" onClick={() => onAction(w.entity_id, domain, 'press')}>
          ▶ Premi
        </button>
      )}
      {isControllable && (
        <button className={`cv-btn ${isOn ? 'cv-btn--off' : 'cv-btn--on'}`}
                onClick={() => onAction(w.entity_id, domain, isOn ? 'turn_off' : 'turn_on')}>
          {isOn ? 'Spegni' : 'Accendi'}
        </button>
      )}
    </div>
  )
}

export default function CustomView() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [view, setView] = useState(null)
  const [myViews, setMyViews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/api/views/${slug}/states`)
      setView({...r.data.view, states: r.data.states})
    } catch (e) {
      setError(e.response?.data?.detail || 'Errore caricamento vista')
    } finally { setLoading(false) }
  }, [slug])

  useEffect(() => {
    api.get('/api/views/my').then(r => setMyViews(r.data)).catch(()=>{})
  }, [])

  useEffect(() => {
    if (slug) api.post(`/api/views/${slug}/log-access`).catch(()=>{})
  }, [slug])

  useEffect(() => {
    load()
    const interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [load])

  const handleAction = async (entityId, domain, service) => {
    try {
      await api.post(`/api/views/${slug}/control`,
        { entity_id: entityId, service, domain })
    } catch {}
  }

  if (loading) return <div className="cv-shell"><div className="cv-loading">Caricamento...</div></div>
  if (error) return <div className="cv-shell"><div className="cv-error">{error}</div></div>

  return (
    <div className="cv-shell">
      <div className="cv-header">
        <div className="cv-topbar">
          <button className="cv-back" onClick={() => navigate('/profile')}>← Profilo</button>
          {myViews.length > 1 && (
            <div className="cv-tabs">
              {myViews.map(v => (
                <button key={v.slug}
                  className={`cv-tab ${v.slug === slug ? 'active' : ''}`}
                  onClick={() => navigate(`/view/${v.slug}`)}>
                  {v.title}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="cv-titlebar">
          <h1 className="cv-title">{view.title}</h1>
        </div>
      </div>
      <div className="cv-grid">
        {view.widgets.sort((a,b) => a.order - b.order).map(w => { const s = view.states?.[w.entity_id] || {}; const ww = {...w, state: s.state, attributes: s.attributes}; return (
          <Widget key={ww.id} w={ww} onAction={handleAction} />
        )})}
      </div>
    </div>
  )
}
