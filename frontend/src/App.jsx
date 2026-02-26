import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Admin from './pages/Admin'
import Profile from './pages/Profile'

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loading">Caricamento...</div>
  if (user) return <Navigate to="/dashboard" />
  return children
}

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loading">Caricamento...</div>
  if (!user) return <Navigate to="/" />
  // Se 2FA obbligatorio e non ancora attivato, forza il profilo
  if (user.totp_required && !user.totp_enabled && window.location.pathname !== '/profile') {
    return <Navigate to="/profile" state={{ force2fa: true }} />
  }
  return children
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="loading">Caricamento...</div>
  return user?.is_admin ? children : <Navigate to="/dashboard" />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<PublicRoute><Login /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
          <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
          <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
          <Route path="/admin" element={<AdminRoute><Admin /></AdminRoute>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
