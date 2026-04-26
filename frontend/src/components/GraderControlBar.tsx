import type { GraderType } from '../lib/types'

export interface GraderControlBarProps {
  graderType: GraderType
  onGraderTypeChange: (type: GraderType) => void
  model: string | null
  onModelChange: (model: string) => void
  availableModels: string[]
  actionLabel: string
  onAction: () => void
  actionDisabled?: boolean
}

const GRADER_OPTIONS: { value: GraderType; label: string; description: string }[] = [
  { value: 'hybrid', label: 'Hybrid', description: '30% rules + 70% LLM (recommended)' },
  { value: 'rule_based', label: 'Rule-based', description: 'Fast, free, offline' },
  { value: 'llm_judge', label: 'LLM Judge', description: 'Full LLM evaluation' },
]

export default function GraderControlBar({
  graderType,
  onGraderTypeChange,
  model,
  onModelChange,
  availableModels,
  actionLabel,
  onAction,
  actionDisabled = false,
}: GraderControlBarProps) {
  // Model dropdown visible only when an LLM is involved and models are available.
  const showModelDropdown =
    graderType !== 'rule_based' && availableModels.length > 0

  return (
    <div className="flex items-center justify-between flex-wrap gap-3">
      {/* Left: grader-type pill buttons + optional model dropdown */}
      <div className="flex gap-2 flex-wrap items-center">
        {GRADER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onGraderTypeChange(opt.value)}
            title={opt.description}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              graderType === opt.value
                ? 'border-brand-500 bg-brand-50 text-brand-700'
                : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {opt.label}
          </button>
        ))}

        {showModelDropdown && (
          <select
            value={model ?? ''}
            onChange={(e) => onModelChange(e.target.value)}
            className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700
              focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        )}
      </div>

      {/* Right: primary action button */}
      <button
        type="button"
        onClick={onAction}
        disabled={actionDisabled}
        className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white shadow-sm
          hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {actionLabel}
      </button>
    </div>
  )
}
