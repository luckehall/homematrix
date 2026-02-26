import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Auto-login: tenta refresh al caricamento
  useEffect(() => {
    const init = async () => {
      try {
        const { data } = await axios.post('https://homematrix.iotzator.com/api/auth/refresh',
          {}, { withCredentials: true })
        localStorage.setItem('access_token', data.access_token)
        const payload = JSON.parse(atob(data.access_token.split(".")[1]))
        const token = data.access_token
        const totp = await axios.get('https://homematrix.iotzator.com/api/auth/2fa/status',
          { headers: { Authorization: `Bearer ${token}` } }).then(r => r.data).catch(() => ({ enabled: true, required: false }))
        const views = await axios.get('https://homematrix.iotzator.com/api/views/my',
          { headers: { Authorization: `Bearer ${token}` } }).then(r => r.data).catch(() => [])
        setUser({ id: payload.sub, is_admin: payload.is_admin, totp_required: totp.required, totp_enabled: totp.enabled, views })
      } catch {}
      finally { setLoading(false) }
    }
    init()
  }, [])

  const check2fa = async (token) => {
    try {
      const res = await axios.get('https://homematrix.iotzator.com/api/auth/2fa/status',
        { headers: { Authorization: `Bearer ${token}` } })
      return res.data
    } catch { return { enabled: true, required: false } }
  }

  const login = async (email, password) => {
    const { data } = await axios.post(
      'https://homematrix.iotzator.com/api/auth/login',
      { email, password }, { withCredentials: true }
    )
    localStorage.setItem('access_token', data.access_token)
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    const totp = await check2fa(data.access_token)
    const views = await axios.get('https://homematrix.iotzator.com/api/views/my',
      { headers: { Authorization: `Bearer ${data.access_token}` } }).then(r => r.data).catch(() => [])
    setUser({ id: payload.sub, is_admin: payload.is_admin, totp_required: totp.required, totp_enabled: totp.enabled, views })
  }

  const logout = async () => {
    await axios.post('https://homematrix.iotzator.com/api/auth/logout',
      {}, { withCredentials: true })
    localStorage.removeItem('access_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
