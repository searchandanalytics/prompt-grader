import type { StatusResponse } from '../lib/types'
import { useProviderConfigContext } from '../App'

interface Props {
  status: StatusResponse | null
  loading: boolean
}

const PROVIDER_LABEL: Record<string, string> = {
  anthropic: 'Claude',
  openai: 'GPT',
  google: 'Gemini',
  groq: 'Groq',
  ollama: 'Ollama',
  none: 'Rule-based only',
}

export default function ProviderBadge({ status, loading }: Props) {
  // Read client-side config so the subtitle reflects UI-supplied keys
  // immediately — the server's /status endpoint can't know about them.
  const { config } = useProviderConfigContext()

  if (loading) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-200 px-3 py-1 text-xs font-medium text-gray-500 animate-pulse">
        Detecting judge…
      </span>
    )
  }
  if (!status) return null

  // When a UI key is active, treat the client-configured provider as the
  // effective provider — the server /status reflects startup config only.
  const uiProvider = config?.apiKey ? config.provider : null

  const label = (() => {
    if (uiProvider && uiProvider !== 'rule_based') {
      return `Judge: ${PROVIDER_LABEL[uiProvider] ?? uiProvider}`
    }
    if (status.judge_provider === 'none') return 'Rule-based only'
    return `Judge: ${PROVIDER_LABEL[status.judge_provider] ?? status.judge_provider}${status.judge_model ? ` (${status.judge_model.split('/').pop()})` : ''}`
  })()

  const isLlmActive = uiProvider ? uiProvider !== 'rule_based' : status.judge_provider !== 'none'

  // Subtitle priority: UI-supplied key (client state) > server-reported source.
  const subtitle = (() => {
    if (config?.apiKey && config.remember) return 'via UI · saved on device'
    if (config?.apiKey && !config.remember) return 'via UI · this session'
    switch (status.key_source) {
      case 'env': return 'via .env file'
      case 'ollama_auto': return 'auto-detected'
      case 'rule_based': return 'no key needed'
      default: return null
    }
  })()

  const colour = isLlmActive
    ? 'bg-brand-50 text-brand-700 border-brand-500/30'
    : 'bg-gray-100 text-gray-600 border-gray-300'

  return (
    <span className={`inline-flex flex-col items-start rounded-xl border px-3 py-1.5 text-xs font-medium ${colour}`}>
      <span className="flex items-center gap-1.5">
        <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${isLlmActive ? 'bg-green-500' : 'bg-gray-400'}`} />
        {label}
      </span>
      {subtitle && (
        <span className="pl-3 text-[10px] font-normal text-gray-400 leading-tight">{subtitle}</span>
      )}
    </span>
  )
}
