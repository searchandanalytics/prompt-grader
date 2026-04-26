import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { StatusResponse } from '../lib/types'

const POLL_INTERVAL_MS = 30_000

export function useStatus() {
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  // Notification shown to user when provider falls back; null when dismissed.
  const [notification, setNotification] = useState<string | null>(null)
  // Tracks the last unhealthy_reason we surfaced so the same message isn't
  // shown again after the user dismisses it (until a *new* reason appears).
  const shownReasonRef = useRef<string | null>(null)

  const refetch = useCallback(() => {
    api
      .getStatus()
      .then((s) => {
        setStatus(s)
        // Surface a new unhealthy_reason only once per unique message.
        if (s.unhealthy_reason && s.unhealthy_reason !== shownReasonRef.current) {
          setNotification(s.unhealthy_reason)
          shownReasonRef.current = s.unhealthy_reason
        }
        // If the provider recovered, reset the ref so a future failure shows again.
        if (!s.unhealthy_reason) {
          shownReasonRef.current = null
        }
      })
      .catch(() => setStatus(null))
      .finally(() => setLoading(false))
  }, [])

  const dismissNotification = useCallback(() => {
    // Clear the visible banner but keep shownReasonRef so the same message
    // isn't re-shown on the next poll.
    setNotification(null)
  }, [])

  // Initial fetch
  useEffect(() => {
    setLoading(true)
    refetch()
  }, [refetch])

  // Periodic polling
  useEffect(() => {
    const id = setInterval(refetch, POLL_INTERVAL_MS)
    return () => clearInterval(id)
  }, [refetch])

  // Refetch on window focus (catches Ollama going down while tab was in background)
  useEffect(() => {
    window.addEventListener('focus', refetch)
    return () => window.removeEventListener('focus', refetch)
  }, [refetch])

  return { status, loading, refetch, notification, dismissNotification }
}
