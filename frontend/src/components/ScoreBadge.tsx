import { EXCELLENT_THRESHOLD } from '../lib/constants'

interface Props {
  score: number | null
}

export default function ScoreBadge({ score }: Props) {
  if (score === null) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-600">
        ❓ Unknown
      </span>
    )
  }
  if (score >= EXCELLENT_THRESHOLD) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-800">
        ✨ Excellent
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-amber-100 text-amber-800">
      ⚠️ Needs Review
    </span>
  )
}
