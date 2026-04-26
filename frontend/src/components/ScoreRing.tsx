import { scoreColor } from '../lib/utils'

interface Props {
  score: number
  size?: number
}

export default function ScoreRing({ score, size = 96 }: Props) {
  const r = (size / 2) * 0.82
  const circ = 2 * Math.PI * r
  const filled = (score / 100) * circ

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-[-90deg]">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="#e5e7eb"
        strokeWidth={size * 0.1}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={size * 0.1}
        strokeDasharray={`${filled} ${circ - filled}`}
        strokeLinecap="round"
        className={scoreColor(score)}
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="middle"
        textAnchor="middle"
        className={`text-[${Math.round(size * 0.22)}px] font-bold ${scoreColor(score)}`}
        style={{ rotate: '90deg', transformOrigin: 'center', fontSize: size * 0.22 }}
        transform={`rotate(90, ${size / 2}, ${size / 2})`}
        fill="currentColor"
      >
        {Math.round(score)}
      </text>
    </svg>
  )
}
