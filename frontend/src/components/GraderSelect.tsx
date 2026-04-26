import type { GraderType } from '../lib/types'

interface Props {
  value: GraderType
  onChange: (v: GraderType) => void
}

const OPTIONS: { value: GraderType; label: string; description: string }[] = [
  { value: 'hybrid', label: 'Hybrid', description: '30% rules + 70% LLM (recommended)' },
  { value: 'rule_based', label: 'Rule-based', description: 'Fast, free, offline' },
  { value: 'llm_judge', label: 'LLM Judge', description: 'Full LLM evaluation' },
]

export default function GraderSelect({ value, onChange }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          title={opt.description}
          className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
            value === opt.value
              ? 'border-brand-500 bg-brand-50 text-brand-700'
              : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
