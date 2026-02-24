import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import './Dashboard.css'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [hosts, setHosts] = useState([])
  const [selectedHost, setSelectedHost] = useState(null)
  const [states, setStates] = useState([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    api.get('/api/hosts/').then(r => {
      setHosts(r.data)
      if (r.data.length > 0) setSelectedHost(r.data[0])
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedHost) return
    setLoading(true)
    api.get(`/api/hosts/${selectedHost.id}/states`)
      .then(r => setStates([...r.data]))
      .catch(() => {})
      .finally(() => setLoading(false))

    const interval = setInterval(() => {
      api.get(`/api/hosts/${selectedHost.id}/states`)
        .then(r => setStates([...r.data]))
        .catch(() => {})
    }, 3000)

    return () => clearInterval(interval)
  }, [selectedHost])

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  const callService = async (domain, service, entity_id) => {
    await api.post(`/api/hosts/${selectedHost.id}/services/${domain}/${service}`, { entity_id })
  }

  const domains = ['all', ...new Set(states.map(s => s.entity_id.split('.')[0]))]
  const filtered = filter === 'all' ? states : states.filter(s => s.entity_id.startsWith(filter + '.'))
  const deviceDomains = ['switch','light','climate','cover','fan','media_player','button','input_boolean','input_select']
  const sensorDomains = ['sensor','binary_sensor','weather']
  const devices = filtered.filter(s => deviceDomains.includes(s.entity_id.split('.')[0]))
  const sensors = filtered.filter(s => sensorDomains.includes(s.entity_id.split('.')[0]))
  const others = filtered.filter(s => !deviceDomains.includes(s.entity_id.split('.')[0]) && !sensorDomains.includes(s.entity_id.split('.')[0]))

  return (
    <div className="dash-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">⌂</div>
          <div className="logo-text">Home<span>Matrix</span></div>
        </div>

        <div className="nav-section">Host</div>
        {hosts.map(h => (
          <div key={h.id}
            className={`nav-item ${selectedHost?.id === h.id ? 'active' : ''}`}
            onClick={() => setSelectedHost(h)}>
            <span className="nav-icon">🖥</span> {h.name}
          </div>
        ))}

        <div className="nav-section">Filtra</div>
        {domains.map(d => (
          <div key={d}
            className={`nav-item ${filter === d ? 'active' : ''}`}
            onClick={() => setFilter(d)}>
            <span className="nav-icon">{domainIcon(d)}</span> {d}
          </div>
        ))}

        <div className="sidebar-footer">
        </div>
      </aside>

      <main className="dash-main">
        <div className="dash-header">
          <div>
            <h1 className="dash-title">{selectedHost?.name || 'Seleziona host'}</h1>
            <div className="dash-sub">{states.length} entità · {devices.length} device · {sensors.length} sensori</div>
          </div>
          <div className="dash-header-right">
            <div className="auto-banner">🔓 Sessione automatica attiva</div>
            <div className="header-actions">
              <button className="btn-header" onClick={() => navigate('/profile')}>👤 Profilo</button>
              {user?.is_admin && (
                <button className="btn-header" onClick={() => navigate('/admin')}>⚙️ Admin</button>
              )}
              <button className="btn-header btn-logout" onClick={handleLogout}>↩ Logout</button>
            </div>
          </div>
        </div>

        {loading && <div className="loading-bar" />}

        {devices.length > 0 && (
          <>
            <div className="section-title">Dispositivi</div>
            <div className="devices-grid">
              {devices.map(s => (
                <DeviceCard key={s.entity_id} state={s} onToggle={callService} />
              ))}
            </div>
          </>
        )}

        {sensors.length > 0 && (
          <>
            <div className="section-title">Sensori</div>
            <div className="sensors-grid">
              {sensors.map(s => (
                <SensorCard key={s.entity_id} state={s} />
              ))}
            </div>
          </>
        )}

        {others.length > 0 && (
          <>
            <div className="section-title">Altro</div>
            <div className="sensors-grid">
              {others.map(s => (
                <SensorCard key={s.entity_id} state={s} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

function DeviceCard({ state, onToggle }) {
  const domain = state.entity_id.split('.')[0]
  const isOn = state.state === 'on' || state.state === 'open'
  const name = state.attributes.friendly_name || state.entity_id

  const toggle = () => {
    if (domain === 'switch' || domain === 'light' || domain === 'input_boolean') {
      onToggle(domain, isOn ? 'turn_off' : 'turn_on', state.entity_id)
    } else if (domain === 'button') {
      onToggle(domain, 'press', state.entity_id)
    } else if (domain === 'cover') {
      onToggle(domain, isOn ? 'close_cover' : 'open_cover', state.entity_id)
    } else if (domain === 'climate') {
      onToggle(domain, 'toggle', state.entity_id)
    } else if (domain === 'fan') {
      onToggle(domain, isOn ? 'turn_off' : 'turn_on', state.entity_id)
    } else if (domain === 'media_player') {
      onToggle(domain, isOn ? 'media_pause' : 'media_play', state.entity_id)
    }
  }

  const hasToggle = ['switch','light','input_boolean','cover','fan','media_player','climate'].includes(domain)
  const isButton = domain === 'button'

  return (
    <div className={`device-card ${isOn ? 'on' : ''} ${isButton ? 'btn-device' : ''}`} onClick={toggle}>
      <div className="device-top">
        <div className="device-icon-wrap">{domainIcon(domain)}</div>
        {hasToggle && <div className={`toggle ${isOn ? 'on' : ''}`} />}
        {isButton && <div className="btn-press">▶ Press</div>}
      </div>
      <div className="device-name">{name}</div>
      <div className="device-room">{domain}</div>
      <div className="device-value">{state.state}</div>
    </div>
  )
}

function SensorCard({ state }) {
  const name = state.attributes.friendly_name || state.entity_id
  const unit = state.attributes.unit_of_measurement || ''
  const domain = state.entity_id.split('.')[0]
  return (
    <div className="sensor-card">
      <div className="sensor-label">{name}</div>
      <div className="sensor-icon">{domainIcon(domain)}</div>
      <div className="sensor-value">{state.state}<span className="sensor-unit">{unit}</span></div>
    </div>
  )
}

function domainIcon(domain) {
  const icons = {
    all: '◉', light: '💡', switch: '🔌', climate: '🌡',
    cover: '🪟', fan: '💨', sensor: '📡', binary_sensor: '⚡',
    weather: '🌤', media_player: '🔊', camera: '📷',
  }
  return icons[domain] || '📦'
}
