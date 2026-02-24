import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Auto-login: tenta refresh al caricamento
  useEffect(() => {
    axios.post('https://homematrix.iotzator.com/api/auth/refresh',
      {}, { withCredentials: true })
      .then(({ data }) => {
        localStorage.setItem('access_token', data.access_token)
        const payload = JSON.parse(atob(data.access_token.split('.')[1]))
        setUser({ id: payload.sub, is_admin: payload.is_admin })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const { data } = await axios.post(
      'https://homematrix.iotzator.com/api/auth/login',
      { email, password }, { withCredentials: true }
    )
    localStorage.setItem('access_token', data.access_token)
    const payload = JSON.parse(atob(data.access_token.split('.')[1]))
    setUser({ id: payload.sub, is_admin: payload.is_admin })
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
