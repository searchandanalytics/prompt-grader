import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { GradeResponse, GraderType } from '../lib/types'
import GradeResultCard from '../components/GradeResultCard'
import GraderControlBar from '../components/GraderControlBar'
import { useStatusContext } from '../App'
import { useAvailableModels } from '../hooks/useAvailableModels'

export default function Dashboard() {
  const [prompt, setPrompt] = useState('')
  const [grader, setGrader] = useState<GraderType>('hybrid')
  const [result, setResult] = useState<GradeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { status, refetch } = useStatusContext()
  const isOllama = status?.judge_provider === 'ollama'

  const availableModels = useAvailableModels()
  const [selectedModel, setSelectedModel] = useState<string>('')

  const navigate = useNavigate()
  const location = useLocation()

  // Build → Grade handoff: pre-fill textarea when navigated from Build page.
  useEffect(() => {
    const incoming = (location.state as { prompt?: string } | null)?.prompt
    if (incoming) {
      setPrompt(incoming)
      setResult(null)
      // Clear the router state so a refresh doesn't re-apply it.
      window.history.replaceState({}, '')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Initialise selectedModel once availableModels arrives, preferring the
  // currently active server model so the dropdown matches the badge.
  useEffect(() => {
    if (availableModels.length === 0 || selectedModel) return
    const active = status?.judge_model?.replace(/^ollama\//, '')
    setSelectedModel(
      active && availableModels.includes(active) ? active : availableModels[0],
    )
  }, [availableModels]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleModelChange(model: string) {
    setSelectedModel(model)
    try {
      await api.setOllamaModel(model)
      refetch()
    } catch {
      // non-fatal
    }
  }

  function handleGraderChange(v: GraderType) {
    setGrader(v)
    setResult(null)
    setError(null)
  }

  async function handleGrade() {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    try {
      const judge_model = isOllama && grader !== 'rule_based' && selectedModel
        ? `ollama/${selectedModel}`
        : undefined
      const res = await api.grade({ prompt, grader, judge_model })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Grading failed')
    } finally {
      setLoading(false)
    }
  }

  function handleBuildWithAI() {
    // Pass the current prompt as a task pre-fill if one exists.
    navigate('/build', prompt.trim() ? { state: { task: prompt } } : {})
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Grade a Prompt</h1>
        <p className="mt-1 text-sm text-gray-500">
          Paste your prompt below and get an instant score across 5 dimensions.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <div className="relative">
          <textarea
            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-mono
              text-gray-800 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1
              focus:ring-brand-500 resize-none transition-colors"
            rows={8}
            placeholder="Enter your prompt here…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          {/* Empty-state hint */}
          {!prompt && (
            <p className="mt-1.5 text-xs text-gray-400">
              Don't know where to start?{' '}
              <button
                type="button"
                onClick={() => navigate('/build')}
                className="text-brand-600 hover:text-brand-700 font-medium"
              >
                Try the Prompt Builder →
              </button>
            </p>
          )}
        </div>

        <GraderControlBar
          graderType={grader}
          onGraderTypeChange={handleGraderChange}
          model={selectedModel}
          onModelChange={handleModelChange}
          availableModels={availableModels}
          actionLabel={loading ? 'Grading…' : 'Grade Prompt'}
          onAction={handleGrade}
          actionDisabled={loading || !prompt.trim()}
        />
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleBuildWithAI}
            className="text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
          >
            ✨ Build with AI
          </button>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-3 border border-red-100">
            {error}
          </p>
        )}
      </div>

      {result && (
        <div className="space-y-3">
          <GradeResultCard result={result.result} />
          {/* Improve with Builder CTA — shown on any result */}
          <p className="text-sm text-gray-500 text-right">
            Want a better prompt?{' '}
            <button
              type="button"
              onClick={() => navigate('/build', { state: { task: prompt } })}
              className="text-brand-600 hover:text-brand-700 font-medium"
            >
              Improve with Builder →
            </button>
          </p>
        </div>
      )}
    </div>
  )
}
