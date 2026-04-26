import type {
  BatchRequest,
  BatchResultItem,
  BuildResponse,
  CompareRequest,
  CompareResponse,
  GradeRequest,
  GradeResponse,
  OllamaModelsResponse,
  PromptBlueprint,
  StatusResponse,
} from './types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Provider-header store — written by useProviderConfig, read by every request.
// This is module-level state so it works outside React components.
// ---------------------------------------------------------------------------
let _providerName: string | null = null
let _providerKey: string | null = null
let _keySource: 'ui_session' | 'ui_persisted' | 'none' = 'none'

/** Called by useProviderConfig whenever the active config changes. */
export function setProviderHeaders(
  name: string | null,
  key: string | null,
  keySource: 'ui_session' | 'ui_persisted' | 'none' = 'none',
): void {
  _providerName = name
  _providerKey = key
  _keySource = keySource
}

/** Returns X-Provider-* headers when a key is active; empty object otherwise. */
function getProviderHeaders(): Record<string, string> {
  if (_providerName && _providerKey) {
    if (import.meta.env.DEV) {
      console.debug(`[BYOK] Sending request with key_source: ${_keySource}`)
    }
    return {
      'X-Provider-Name': _providerName,
      'X-Provider-Key': _providerKey,
    }
  }
  if (import.meta.env.DEV) {
    console.debug('[BYOK] Sending request with key_source: none')
  }
  return {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getProviderHeaders(),
      ...init?.headers,
    },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  grade(req: GradeRequest): Promise<GradeResponse> {
    return request('/api/v1/grade', { method: 'POST', body: JSON.stringify(req) })
  },

  compare(req: CompareRequest): Promise<CompareResponse> {
    return request('/api/v1/compare', { method: 'POST', body: JSON.stringify(req) })
  },

  /** Streams batch results as NDJSON, calling onItem for each completed item. */
  async batch(
    req: BatchRequest,
    onItem: (item: BatchResultItem) => void,
    onError?: (err: Error) => void,
  ): Promise<void> {
    const res = await fetch(`${BASE}/api/v1/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getProviderHeaders() },
      body: JSON.stringify(req),
    })
    if (!res.ok || !res.body) {
      const text = await res.text()
      throw new Error(`${res.status}: ${text}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const item = JSON.parse(line) as BatchResultItem
          if (item.error) {
            onError?.(new Error(`[${item.id}] ${item.error}`))
          } else {
            onItem(item)
          }
        } catch {
          // malformed line — skip
        }
      }
    }
  },

  getStatus(): Promise<StatusResponse> {
    return request('/api/v1/status')
  },

  refreshStatus(): Promise<StatusResponse> {
    return request('/api/v1/status/refresh', { method: 'POST' })
  },

  getOllamaModels(): Promise<OllamaModelsResponse> {
    return request('/api/v1/status/ollama-models')
  },

  setOllamaModel(model: string): Promise<StatusResponse> {
    return request('/api/v1/status/set-model', { method: 'POST', body: JSON.stringify({ model }) })
  },

  build(blueprint: PromptBlueprint): Promise<BuildResponse> {
    return request('/api/v1/build', { method: 'POST', body: JSON.stringify(blueprint) })
  },
}
