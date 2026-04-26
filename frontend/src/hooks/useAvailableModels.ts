import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useStatusContext } from '../App'

/**
 * Returns the list of selectable model names for the active provider.
 *
 * Currently populated only when the provider is Ollama — fetched once from
 * /api/v1/status/ollama-models and cached for the component's lifetime.
 * Returns [] for every other provider; those users configure a model via
 * Settings (BYOK), not a tab-level dropdown.
 */
export function useAvailableModels(): string[] {
  const { status } = useStatusContext()
  const [models, setModels] = useState<string[]>([])

  const isOllama = status?.judge_provider === 'ollama'

  useEffect(() => {
    if (!isOllama) {
      setModels([])
      return
    }
    api
      .getOllamaModels()
      .then(({ models }) => setModels(models))
      .catch(() => setModels([]))
  }, [isOllama])

  return models
}
