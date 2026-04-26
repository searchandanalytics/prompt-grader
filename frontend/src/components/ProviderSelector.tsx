import { useEffect, useState } from 'react'
import { CheckCircle2, Eye, EyeOff, XCircle } from 'lucide-react'
import { useProviderConfigContext } from '../App'
import type { ProviderName } from '../lib/types'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const PROVIDERS: { value: ProviderName; label: string; needsKey: boolean }[] = [
  { value: 'anthropic', label: 'Anthropic Claude', needsKey: true },
  { value: 'openai', label: 'OpenAI GPT', needsKey: true },
  { value: 'google', label: 'Google Gemini (free tier)', needsKey: true },
  { value: 'groq', label: 'Groq (free tier, fast)', needsKey: true },
  { value: 'ollama', label: 'Ollama (local, free)', needsKey: false },
  { value: 'rule_based', label: 'Rule-based only (no LLM)', needsKey: false },
]

export default function ProviderSelector() {
  const { config, setConfig, clearConfig } = useProviderConfigContext()

  // Staged form state — not committed until Save is clicked.
  const [provider, setProvider] = useState<ProviderName>(config?.provider ?? 'rule_based')
  const [apiKey, setApiKey] = useState<string>(config?.apiKey ?? '')
  const [model, setModel] = useState<string>(config?.model ?? '')
  const [remember, setRemember] = useState<boolean>(config?.remember ?? false)

  // UI state
  const [showKey, setShowKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [saved, setSaved] = useState(false)

  // Re-sync staged state if external config changes (e.g. on mount from localStorage).
  useEffect(() => {
    if (config) {
      setProvider(config.provider)
      setApiKey(config.apiKey ?? '')
      setModel(config.model ?? '')
      setRemember(config.remember)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const selected = PROVIDERS.find((p) => p.value === provider)!
  const needsKey = selected.needsKey

  function handleProviderChange(v: ProviderName) {
    setProvider(v)
    setApiKey('')
    setModel('')
    setTestResult(null)
    setSaved(false)
  }

  async function handleTest() {
    // Make the test request directly with staged credentials rather than going through
    // the hook's testConnection (which reads committed config state and would need a
    // re-render to pick up staged values).
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch(`${BASE}/api/v1/status/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Provider-Name': provider,
          'X-Provider-Key': apiKey,
        },
        body: JSON.stringify({ provider, ...(model ? { model } : {}) }),
      })
      if (!res.ok) {
        setTestResult({ ok: false, message: `Server returned ${res.status}. Check your key and try again.` })
        return
      }
      const data = (await res.json()) as { ok: boolean; error?: string; latency_ms?: number }
      if (!data.ok) {
        setTestResult({ ok: false, message: 'Connection test failed. Verify your API key is correct.' })
        return
      }
      const latency = data.latency_ms != null ? ` (${Math.round(data.latency_ms)}ms)` : ''
      setTestResult({ ok: true, message: `Connected successfully${latency}.` })
    } catch {
      setTestResult({ ok: false, message: 'Could not reach the server. Check your network and try again.' })
    } finally {
      setTesting(false)
    }
  }

  function handleSave() {
    setConfig({ provider, apiKey: apiKey || null, model: model || null, remember })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  function handleClear() {
    clearConfig()
    setProvider('rule_based')
    setApiKey('')
    setModel('')
    setRemember(false)
    setTestResult(null)
    setSaved(false)
  }

  return (
    <div className="space-y-6">
      {/* Provider */}
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-gray-700">
          LLM Provider
        </label>
        <select
          value={provider}
          onChange={(e) => handleProviderChange(e.target.value as ProviderName)}
          className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800
            focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>

      {/* API key — hidden for ollama / rule_based */}
      {needsKey && (
        <>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-gray-700">
              API Key
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => { setApiKey(e.target.value); setTestResult(null); setSaved(false) }}
                placeholder="Paste your API key here"
                autoComplete="off"
                className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 pr-10 text-sm
                  text-gray-800 placeholder-gray-400 focus:border-brand-500 focus:outline-none
                  focus:ring-1 focus:ring-brand-500 font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                aria-label={showKey ? 'Hide key' : 'Show key'}
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <p className="text-xs text-gray-400">
              Keys are sent directly to the backend per request and never stored on the server.
            </p>
          </div>

          {/* Optional model override */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-gray-700">
              Model <span className="font-normal text-gray-400">(optional — uses provider default if blank)</span>
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => { setModel(e.target.value); setSaved(false) }}
              placeholder={
                provider === 'anthropic' ? 'e.g. claude-sonnet-4-6' :
                provider === 'openai' ? 'e.g. gpt-4o' :
                provider === 'google' ? 'e.g. gemini-1.5-flash' :
                provider === 'groq' ? 'e.g. llama3-8b-8192' : ''
              }
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800
                placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1
                focus:ring-brand-500 font-mono"
            />
          </div>

          {/* Remember toggle */}
          <div className="rounded-lg border border-amber-100 bg-amber-50 px-4 py-3 space-y-2">
            <div className="flex items-center gap-3">
              {/* Custom toggle */}
              <button
                type="button"
                role="switch"
                aria-checked={remember}
                onClick={() => setRemember((v) => !v)}
                className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent
                  transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-500
                  focus:ring-offset-1 ${remember ? 'bg-brand-600' : 'bg-gray-300'}`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow
                    transform transition-transform duration-200 ${remember ? 'translate-x-4' : 'translate-x-0'}`}
                />
              </button>
              <span className="text-sm font-medium text-gray-700">Remember on this device</span>
            </div>
            <p className="text-xs text-amber-700">
              <strong>Warning:</strong> Stored in your browser only (localStorage). Anyone with
              access to this device can read it. Leave off to keep the key in memory for this
              session only.
            </p>
          </div>

          {/* Test connection */}
          <div className="flex items-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={handleTest}
              disabled={testing || !apiKey.trim()}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium
                text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed
                transition-colors"
            >
              {testing ? 'Testing…' : 'Test connection'}
            </button>

            {testResult && (
              <span className={`flex items-center gap-1.5 text-sm font-medium
                ${testResult.ok ? 'text-emerald-700' : 'text-red-600'}`}
              >
                {testResult.ok
                  ? <CheckCircle2 size={16} className="flex-shrink-0" />
                  : <XCircle size={16} className="flex-shrink-0" />
                }
                {testResult.message}
              </span>
            )}
          </div>
        </>
      )}

      {/* Rule-based / Ollama info */}
      {!needsKey && (
        <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
          <p className="text-sm text-gray-600">
            {provider === 'ollama'
              ? 'Ollama runs locally — no API key required. Make sure Ollama is running and the backend can reach it.'
              : 'Rule-based mode requires no LLM or API key. Grading uses fast heuristic checks only.'}
          </p>
        </div>
      )}

      {/* Save / Clear */}
      <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
        <button
          type="button"
          onClick={handleSave}
          className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white shadow-sm
            hover:bg-brand-700 transition-colors"
        >
          {saved ? 'Saved!' : 'Save'}
        </button>
        <button
          type="button"
          onClick={handleClear}
          className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium
            text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Clear (use .env / auto-detect)
        </button>
      </div>
    </div>
  )
}
