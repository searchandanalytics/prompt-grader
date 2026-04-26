import { useState } from 'react'
import type { GradeResult } from '../lib/types'
import { DIMENSION_LABELS } from '../lib/types'
import { scoreColor, scoreBar } from '../lib/utils'
import ScoreRing from './ScoreRing'
import BreakdownChart from './BreakdownChart'
import ScoreBadge from './ScoreBadge'

interface Props {
  result: GradeResult
  title?: string
}

export default function GradeResultCard({ result, title }: Props) {
  const [showDetails, setShowDetails] = useState(false)

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-gray-700">{title ?? 'Result'}</h3>
        <ScoreBadge score={result.score} />
      </div>

      {showDetails && (
        <>
          <div className="flex items-center gap-5">
            <ScoreRing score={result.score} size={88} />
            <div>
              <p className={`text-4xl font-bold ${scoreColor(result.score)}`}>
                {result.score.toFixed(1)}
                <span className="text-lg font-normal text-gray-400">/100</span>
              </p>
              <p className="text-xs text-gray-500 mt-1 capitalize">
                {result.grader.replace('_', ' ')} · {result.provider}
              </p>
            </div>
          </div>

          <BreakdownChart breakdown={result.breakdown} />

          <div className="space-y-2">
            {Object.entries(result.breakdown).map(([key, val]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-xs text-gray-500">{DIMENSION_LABELS[key] ?? key}</span>
                <div className="flex-1 rounded-full bg-gray-100 h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${scoreBar(val)}`}
                    style={{ width: `${val}%` }}
                  />
                </div>
                <span className={`w-8 text-right text-xs font-medium ${scoreColor(val)}`}>
                  {Math.round(val)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {result.feedback && (
        <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3 border border-gray-100">
          {result.feedback}
        </p>
      )}

      <button
        type="button"
        onClick={() => setShowDetails((v) => !v)}
        className="text-xs text-brand-600 hover:text-brand-700 font-medium"
      >
        {showDetails ? 'Hide details' : 'Show details'}
      </button>
    </div>
  )
}
