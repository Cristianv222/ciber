import { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('ciber_token')
    const username = localStorage.getItem('ciber_user')
    if (token && username) setUser({ username })
    setReady(true)
  }, [])

  async function login(username, password) {
    const { data } = await api.post('/api/auth/login/', { username, password })
    localStorage.setItem('ciber_token', data.token)
    localStorage.setItem('ciber_user', data.username)
    setUser({ username: data.username, is_staff: data.is_staff })
    return data
  }

  function logout() {
    localStorage.removeItem('ciber_token')
    localStorage.removeItem('ciber_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
