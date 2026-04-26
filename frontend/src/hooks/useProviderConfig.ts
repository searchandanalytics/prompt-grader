import { useCallback, useEffect, useState } from 'react'
import { setProviderHeaders } from '../lib/api'
import type { ProviderConfig, ProviderName } from '../lib/types'

const STORAGE_KEY = 'promptgrade.providerConfig'
const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function readFromStorage(): ProviderConfig | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as ProviderConfig
    // Validate shape before trusting it.
    if (!parsed.provider || typeof parsed.provider !== 'string') return null
    return { ...parsed, remember: true }
  } catch {
    return null
  }
}

function writeToStorage(config: ProviderConfig): void {
  try {
    // Never persist the API key if it is null.
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch {
    // localStorage may be unavailable (private browsing, quota).
  }
}

function removeFromStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

export interface UseProviderConfigReturn {
  config: ProviderConfig | null
  setConfig: (config: ProviderConfig) => void
  clearConfig: () => void
  testConnection: () => Promise<{ ok: boolean; message: string }>
}

export function useProviderConfig(): UseProviderConfigReturn {
  const [config, setConfigState] = useState<ProviderConfig | null>(() => readFromStorage())

  // Sync provider headers into api.ts whenever config changes.
  useEffect(() => {
    if (config && config.provider !== 'rule_based' && config.apiKey) {
      const keySource = config.remember ? 'ui_persisted' : 'ui_session'
      setProviderHeaders(config.provider, config.apiKey, keySource)
    } else {
      setProviderHeaders(null, null, 'none')
    }
  }, [config])

  const setConfig = useCallback((next: ProviderConfig) => {
    setConfigState(next)
    if (next.remember) {
      writeToStorage(next)
    } else {
      // Not persisted — remove any previously stored config so a refresh
      // reverts to .env / Ollama / rule-based (per spec).
      removeFromStorage()
    }
  }, [])

  const clearConfig = useCallback(() => {
    setConfigState(null)
    removeFromStorage()
    setProviderHeaders(null, null)
  }, [])

  const testConnection = useCallback(async (): Promise<{ ok: boolean; message: string }> => {
    if (!config || config.provider === 'rule_based' || !config.apiKey) {
      return { ok: false, message: 'No provider key configured.' }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Provider-Name': config.provider as ProviderName,
      'X-Provider-Key': config.apiKey,
    }

    try {
      const res = await fetch(`${BASE}/api/v1/status/test`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          provider: config.provider,
          ...(config.model ? { model: config.model } : {}),
        }),
      })

      if (!res.ok) {
        // Deliberately do not include response body — it may echo the key.
        return { ok: false, message: `Server returned ${res.status}. Check your key and try again.` }
      }

      const data = (await res.json()) as { ok: boolean; error?: string; latency_ms?: number }

      if (!data.ok) {
        // Surface a generic message; never relay raw backend error which may
        // contain key material or stack traces.
        return { ok: false, message: 'Connection test failed. Verify your API key is correct.' }
      }

      const latency = data.latency_ms != null ? ` (${Math.round(data.latency_ms)}ms)` : ''
      return { ok: true, message: `Connected successfully${latency}.` }
    } catch {
      // Network error — no key material in message.
      return { ok: false, message: 'Could not reach the server. Check your network and try again.' }
    }
  }, [config])

  return { config, setConfig, clearConfig, testConnection }
}
