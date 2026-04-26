import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { CompareResponse, GraderType } from '../lib/types'
import GradeResultCard from '../components/GradeResultCard'
import GraderControlBar from '../components/GraderControlBar'
import { useStatusContext } from '../App'
import { useAvailableModels } from '../hooks/useAvailableModels'

export default function Compare() {
  const [promptA, setPromptA] = useState('')
  const [promptB, setPromptB] = useState('')
  const [grader, setGrader] = useState<GraderType>('hybrid')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [result, setResult] = useState<CompareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { status } = useStatusContext()
  const isOllama = status?.judge_provider === 'ollama'
  const availableModels = useAvailableModels()

  // Default selectedModel to first available on mount.
  useEffect(() => {
    if (availableModels.length > 0 && !selectedModel) {
      setSelectedModel(availableModels[0])
    }
  }, [availableModels]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCompare() {
    if (!promptA.trim() || !promptB.trim()) return
    setLoading(true)
    setError(null)
    try {
      const judge_model =
        isOllama && grader !== 'rule_based' && selectedModel
          ? `ollama/${selectedModel}`
          : undefined
      const res = await api.compare({ prompt_a: promptA, prompt_b: promptB, grader, judge_model })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const winnerLabel =
    result?.winner === 'tie'
      ? "It's a tie!"
      : result?.winner === 'a'
        ? 'Prompt A wins'
        : 'Prompt B wins'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compare Prompts</h1>
        <p className="mt-1 text-sm text-gray-500">
          Enter two prompts side-by-side to see which scores better across all dimensions.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {[
          { label: 'Prompt A', value: promptA, set: setPromptA },
          { label: 'Prompt B', value: promptB, set: setPromptB },
        ].map(({ label, value, set }) => (
          <div key={label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
            <label className="text-sm font-medium text-gray-700">{label}</label>
            <textarea
              className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-mono
                text-gray-800 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1
                focus:ring-brand-500 resize-none"
              rows={7}
              placeholder={`Enter ${label.toLowerCase()}…`}
              value={value}
              onChange={(e) => set(e.target.value)}
            />
          </div>
        ))}
      </div>

      <GraderControlBar
        graderType={grader}
        onGraderTypeChange={(v) => { setGrader(v); setResult(null); setError(null) }}
        model={selectedModel}
        onModelChange={setSelectedModel}
        availableModels={availableModels}
        actionLabel={loading ? 'Comparing…' : 'Compare Prompts'}
        onAction={handleCompare}
        actionDisabled={loading || !promptA.trim() || !promptB.trim()}
      />

      {error && (
        <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-3 border border-red-100">
          {error}
        </p>
      )}

      {result && (
        <div className="space-y-4">
          <div
            className={`rounded-xl border px-5 py-3 text-center text-sm font-semibold ${
              result.winner === 'tie'
                ? 'border-gray-200 bg-gray-50 text-gray-700'
                : 'border-green-200 bg-green-50 text-green-800'
            }`}
          >
            {winnerLabel} — A: {result.result_a.score.toFixed(1)} vs B: {result.result_b.score.toFixed(1)}
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <GradeResultCard
              result={result.result_a}
              title={`Prompt A${result.winner === 'a' ? ' 🏆' : ''}`}
            />
            <GradeResultCard
              result={result.result_b}
              title={`Prompt B${result.winner === 'b' ? ' 🏆' : ''}`}
            />
          </div>
        </div>
      )}
    </div>
  )
}
