import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/AuthContext.jsx'
import Layout from './components/Layout.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Flows from './pages/Flows.jsx'
import Attacks from './pages/Attacks.jsx'
import Honeypot from './pages/Honeypot.jsx'
import Agents from './pages/Agents.jsx'
import Models from './pages/Models.jsx'
import System from './pages/System.jsx'

function Protected({ children }) {
  const { user, ready } = useAuth()
  if (!ready) return null
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="flujos" element={<Flows />} />
        <Route path="ataques" element={<Attacks />} />
        <Route path="honeypot" element={<Honeypot />} />
        <Route path="agentes" element={<Agents />} />
        <Route path="modelos" element={<Models />} />
        <Route path="sistema" element={<System />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
