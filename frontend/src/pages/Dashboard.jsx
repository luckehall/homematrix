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
      .then(r => setStates(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [selectedHost])

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  const callService = async (domain, service, entity_id) => {
    await api.post(`/api/hosts/${selectedHost.id}/services/${domain}/${service}`, { entity_id })
    const r = await api.get(`/api/hosts/${selectedHost.id}/states`)
    setStates(r.data)
  }

  const domains = ['all', ...new Set(states.map(s => s.entity_id.split('.')[0]))]
  const filtered = filter === 'all' ? states : states.filter(s => s.entity_id.startsWith(filter + '.'))
  const sensors = filtered.filter(s => ['sensor','binary_sensor','weather'].includes(s.entity_id.split('.')[0]))
  const devices = filtered.filter(s => ['switch','light','climate','cover','fan','media_player'].includes(s.entity_id.split('.')[0]))

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
          <div className="nav-item" onClick={() => navigate('/profile')}>
            <span className="nav-icon">👤</span> Profilo
          </div>
          {user?.is_admin && (
            <div className="nav-item" onClick={() => navigate('/admin')}>
              <span className="nav-icon">⚙️</span> Admin
            </div>
          )}
          <div className="nav-item" onClick={handleLogout}>
            <span className="nav-icon">↩</span> Logout
          </div>
        </div>
      </aside>

      <main className="dash-main">
        <div className="dash-header">
          <div>
            <h1 className="dash-title">{selectedHost?.name || 'Seleziona host'}</h1>
            <div className="dash-sub">{states.length} entità · {devices.length} device · {sensors.length} sensori</div>
          </div>
          <div className="auto-banner">🔓 Sessione automatica attiva</div>
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
      </main>
    </div>
  )
}

function DeviceCard({ state, onToggle }) {
  const domain = state.entity_id.split('.')[0]
  const isOn = state.state === 'on' || state.state === 'open'
  const name = state.attributes.friendly_name || state.entity_id

  const toggle = () => {
    if (domain === 'switch' || domain === 'light') {
      onToggle(domain, isOn ? 'turn_off' : 'turn_on', state.entity_id)
    }
  }

  return (
    <div className={`device-card ${isOn ? 'on' : ''}`} onClick={toggle}>
      <div className="device-top">
        <div className="device-icon-wrap">{domainIcon(domain)}</div>
        <div className={`toggle ${isOn ? 'on' : ''}`} />
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
