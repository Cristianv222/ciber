import axios from 'axios'

// La API y el WebSocket se alcanzan desde el navegador (host) por localhost.
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/flows/'

export const api = axios.create({ baseURL: API_URL })

// Adjunta el token (si existe) a cada petición.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ciber_token')
  if (token) config.headers.Authorization = `Token ${token}`
  return config
})

export default api
