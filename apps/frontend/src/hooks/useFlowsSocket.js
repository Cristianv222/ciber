import { useEffect, useRef, useState } from 'react'
import { WS_URL } from '../api/client.js'

// Conexión al WebSocket de flujos en tiempo real.
// Entrega los últimos eventos (new_flow / flow_updated / new_honeypot_event)
// y un estado de conexión. Reconecta automáticamente.
export function useFlowsSocket(onEvent) {
  const [connected, setConnected] = useState(false)
  const cbRef = useRef(onEvent)
  cbRef.current = onEvent

  useEffect(() => {
    let ws
    let closed = false
    let retry

    function connect() {
      ws = new WebSocket(WS_URL)
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!closed) retry = setTimeout(connect, 2000)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          cbRef.current && cbRef.current(msg)
        } catch (_) {}
      }
    }
    connect()

    return () => {
      closed = true
      clearTimeout(retry)
      ws && ws.close()
    }
  }, [])

  return { connected }
}
