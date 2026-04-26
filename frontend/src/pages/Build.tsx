import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type {
  BuildResponse,
  PromptBlueprint,
  PromptStyle,
  PromptTone,
  ResponseFormat,
} from '../lib/types'
import GradeResultCard from '../components/GradeResultCard'
import ScoreBadge from '../components/ScoreBadge'

// ---------------------------------------------------------------------------
// Draft persistence
// ---------------------------------------------------------------------------

const DRAFT_KEY = 'promptgrade.buildDraft'

interface DraftState {
  step: number
  blueprint: Partial<PromptBlueprint>
}

function loadDraft(): DraftState | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    return raw ? (JSON.parse(raw) as DraftState) : null
  } catch {
    return null
  }
}

function saveDraft(step: number, blueprint: Partial<PromptBlueprint>) {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify({ step, blueprint }))
  } catch {
    // storage full or unavailable — non-fatal
  }
}

function clearDraft() {
  try {
    localStorage.removeItem(DRAFT_KEY)
  } catch {}
}

// ---------------------------------------------------------------------------
// Step definitions
// ---------------------------------------------------------------------------

interface StepDef {
  label: string
  hint: string
  required: boolean
  field?: keyof PromptBlueprint
}

const STEPS: StepDef[] = [
  {
    label: 'Task',
    hint: 'What do you want the AI to do? (one sentence)',
    required: true,
    field: 'task',
  },
  {
    label: 'Context',
    hint: 'What background should the AI know?',
    required: false,
    field: 'context',
  },
  {
    label: 'Objective',
    hint: "What's the goal? What does success look like?",
    required: true,
    field: 'objective',
  },
  {
    label: 'Style & Tone',
    hint: 'Choose a writing style and emotional tone.',
    required: true,
  },
  {
    label: 'Audience',
    hint: 'Who is the output for?',
    required: true,
    field: 'audience',
  },
  {
    label: 'Response Format',
    hint: 'What format should the output be in?',
    required: true,
  },
  {
    label: 'Examples',
    hint: 'Paste 1–3 examples of ideal output (optional but boosts quality).',
    required: false,
    field: 'examples',
  },
  {
    label: 'Constraints',
    hint: 'Anything to avoid? Any must-haves?',
    required: false,
    field: 'constraints',
  },
  {
    label: 'Review & Generate',
    hint: 'Review your answers, then build your prompt.',
    required: true,
  },
]

const TOTAL = STEPS.length // 9

// ---------------------------------------------------------------------------
// Select option lists
// ---------------------------------------------------------------------------

const STYLES: { value: PromptStyle; label: string }[] = [
  { value: 'formal', label: 'Formal' },
  { value: 'casual', label: 'Casual' },
  { value: 'technical', label: 'Technical' },
  { value: 'creative', label: 'Creative' },
]

const TONES: { value: PromptTone; label: string }[] = [
  { value: 'neutral', label: 'Neutral' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'authoritative', label: 'Authoritative' },
  { value: 'playful', label: 'Playful' },
  { value: 'empathetic', label: 'Empathetic' },
]

const FORMATS: { value: ResponseFormat; label: string }[] = [
  { value: 'paragraph', label: 'Paragraph(s)' },
  { value: 'bulleted_list', label: 'Bulleted list' },
  { value: 'json', label: 'JSON' },
  { value: 'table', label: 'Table' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'code', label: 'Code block' },
]

// ---------------------------------------------------------------------------
// Shared input style helpers
// ---------------------------------------------------------------------------

const textareaClass =
  'w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-mono ' +
  'text-gray-800 placeholder-gray-400 focus:border-brand-500 focus:outline-none ' +
  'focus:ring-1 focus:ring-brand-500 resize-none transition-colors'

const selectClass =
  'rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 ' +
  'focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500'

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Build() {
  const location = useLocation()
  const navigate = useNavigate()

  // Initialise from router state (Grade → Build handoff) or saved draft.
  const [step, setStep] = useState<number>(() => {
    if (location.state?.task) return 0 // fresh start when coming from Grade
    return loadDraft()?.step ?? 0
  })

  const [blueprint, setBlueprint] = useState<Partial<PromptBlueprint>>(() => {
    if (location.state?.task) {
      return {
        style: 'formal',
        tone: 'neutral',
        response_format: 'paragraph',
        task: String(location.state.task),
      }
    }
    return loadDraft()?.blueprint ?? {
      style: 'formal',
      tone: 'neutral',
      response_format: 'paragraph',
    }
  })

  const [result, setResult] = useState<BuildResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [draftSaved, setDraftSaved] = useState(false)
  const promptTextRef = useRef<HTMLTextAreaElement>(null)

  // Auto-save draft whenever step or blueprint changes.
  useEffect(() => {
    saveDraft(step, blueprint)
  }, [step, blueprint])

  // ---------------------------------------------------------------------------
  // Navigation helpers
  // ---------------------------------------------------------------------------

  function patch(partial: Partial<PromptBlueprint>) {
    setBlueprint((prev) => ({ ...prev, ...partial }))
    setValidationError(null)
  }

  function validateCurrent(): string | null {
    const def = STEPS[step]
    if (!def.required) return null
    if (def.field) {
      const val = blueprint[def.field] as string | undefined
      if (!val?.trim()) return `${def.label} is required.`
    }
    // Step 4 (style/tone) and 5 (format) have defaults, so always valid.
    return null
  }

  function goNext() {
    const err = validateCurrent()
    if (err) { setValidationError(err); return }
    setValidationError(null)
    setStep((s) => Math.min(s + 1, TOTAL - 1))
  }

  function goBack() {
    setValidationError(null)
    setStep((s) => Math.max(s - 1, 0))
  }

  function skip() {
    setValidationError(null)
    setStep((s) => Math.min(s + 1, TOTAL - 1))
  }

  function saveAndConfirm() {
    saveDraft(step, blueprint)
    setDraftSaved(true)
    setTimeout(() => setDraftSaved(false), 2000)
  }

  // ---------------------------------------------------------------------------
  // Build action
  // ---------------------------------------------------------------------------

  async function handleBuild() {
    // Validate all required fields before submitting.
    const missing = (['task', 'objective', 'audience'] as const).find(
      (f) => !blueprint[f]?.trim(),
    )
    if (missing) {
      setError(`Missing required field: ${missing}. Go back and fill it in.`)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const res = await api.build(blueprint as PromptBlueprint)
      setResult(res)
      clearDraft()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Build failed')
    } finally {
      setLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Result actions
  // ---------------------------------------------------------------------------

  function handleCopy() {
    if (!result) return
    navigator.clipboard.writeText(result.prompt).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function handleGradeThis() {
    if (!result) return
    navigate('/', { state: { prompt: result.prompt } })
  }

  function handleEdit() {
    setResult(null)
    setStep(0)
  }

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  function renderStepContent() {
    const def = STEPS[step]

    // Simple textarea steps (task, context, objective, audience, examples, constraints)
    if (def.field && def.field !== 'style' && def.field !== 'tone' && def.field !== 'response_format') {
      const placeholders: Partial<Record<keyof PromptBlueprint, string>> = {
        task: 'e.g. Write product descriptions for an e-commerce site',
        context: 'e.g. We sell sustainable bamboo home goods to eco-conscious millennials',
        objective: 'e.g. Drive clicks and convey eco-friendliness in under 50 words',
        audience: 'e.g. Online shoppers aged 25–40, mobile users',
        examples: 'Paste one or more examples of the output you want…',
        constraints: 'e.g. No superlatives like "best ever". Always mention free shipping.',
      }
      return (
        <textarea
          className={textareaClass}
          rows={6}
          placeholder={placeholders[def.field] ?? ''}
          value={(blueprint[def.field] as string) ?? ''}
          onChange={(e) => patch({ [def.field!]: e.target.value })}
          autoFocus
        />
      )
    }

    // Step 3 — Style & Tone
    if (step === 3) {
      return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-600">Style</label>
            <select
              className={`${selectClass} w-full`}
              value={blueprint.style ?? 'formal'}
              onChange={(e) => patch({ style: e.target.value as PromptStyle })}
            >
              {STYLES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-600">Tone</label>
            <select
              className={`${selectClass} w-full`}
              value={blueprint.tone ?? 'neutral'}
              onChange={(e) => patch({ tone: e.target.value as PromptTone })}
            >
              {TONES.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        </div>
      )
    }

    // Step 5 — Response Format + optional length
    if (step === 5) {
      return (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-600">Format</label>
            <select
              className={`${selectClass} w-full`}
              value={blueprint.response_format ?? 'paragraph'}
              onChange={(e) => patch({ response_format: e.target.value as ResponseFormat })}
            >
              {FORMATS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-600">
              Length <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm
                text-gray-800 placeholder-gray-400 focus:border-brand-500 focus:outline-none
                focus:ring-1 focus:ring-brand-500 transition-colors"
              placeholder='e.g. "under 50 words" or "2–3 sentences"'
              value={blueprint.length ?? ''}
              onChange={(e) => patch({ length: e.target.value || undefined })}
            />
          </div>
        </div>
      )
    }

    // Step 8 — Review
    if (step === 8) {
      return renderReview()
    }

    return null
  }

  function ReviewRow({ label, value }: { label: string; value: string | undefined }) {
    return (
      <div className="flex gap-3 py-2 border-b border-gray-100 last:border-0">
        <span className="w-32 shrink-0 text-xs font-medium text-gray-500">{label}</span>
        <span className="text-sm text-gray-800 break-words min-w-0">
          {value?.trim() || <span className="text-gray-400 italic">not provided</span>}
        </span>
      </div>
    )
  }

  function renderReview() {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-500">
          Review your answers below, then click <strong>Build my prompt</strong>.
        </div>
        <div className="divide-y divide-gray-100">
          <ReviewRow label="Task" value={blueprint.task} />
          <ReviewRow label="Context" value={blueprint.context} />
          <ReviewRow label="Objective" value={blueprint.objective} />
          <ReviewRow label="Style" value={blueprint.style} />
          <ReviewRow label="Tone" value={blueprint.tone} />
          <ReviewRow label="Audience" value={blueprint.audience} />
          <ReviewRow label="Format" value={blueprint.response_format?.replace('_', ' ')} />
          <ReviewRow label="Length" value={blueprint.length} />
          <ReviewRow label="Examples" value={blueprint.examples} />
          <ReviewRow label="Constraints" value={blueprint.constraints} />
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const def = STEPS[step]
  const isReview = step === 8
  const isOptional = !def.required

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Prompt Builder</h1>
        <p className="mt-1 text-sm text-gray-500">
          Answer a few questions and we'll write a production-ready prompt for you.
        </p>
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Step {step + 1} of {TOTAL} — <span className="font-medium text-gray-700">{def.label}</span></span>
          <button
            type="button"
            onClick={saveAndConfirm}
            className="text-brand-600 hover:text-brand-700 font-medium transition-colors"
          >
            {draftSaved ? '✓ Draft saved' : 'Save draft'}
          </button>
        </div>
        <div className="w-full rounded-full bg-gray-100 h-1.5">
          <div
            className="h-1.5 rounded-full bg-brand-500 transition-all duration-300"
            style={{ width: `${((step + 1) / TOTAL) * 100}%` }}
          />
        </div>
      </div>

      {/* Step card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">{def.label}</h2>
          <p className="mt-0.5 text-sm text-gray-500">{def.hint}</p>
        </div>

        {renderStepContent()}

        {validationError && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 border border-red-100">
            {validationError}
          </p>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={goBack}
            disabled={step === 0}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium
              text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed
              transition-colors"
          >
            ← Back
          </button>

          <div className="flex items-center gap-3">
            {isOptional && !isReview && (
              <button
                type="button"
                onClick={skip}
                className="text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
              >
                Skip
              </button>
            )}
            {isReview ? (
              <button
                type="button"
                onClick={handleBuild}
                disabled={loading}
                className="rounded-lg bg-brand-600 px-6 py-2 text-sm font-semibold text-white shadow-sm
                  hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Building…' : 'Build my prompt'}
              </button>
            ) : (
              <button
                type="button"
                onClick={goNext}
                className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white shadow-sm
                  hover:bg-brand-700 transition-colors"
              >
                Next →
              </button>
            )}
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-3 border border-red-100">
            {error}
          </p>
        )}
      </div>

      {/* Result section — shown after a successful build */}
      {result && (
        <div className="rounded-xl border border-brand-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-gray-900">Your generated prompt</h3>
              <p className="text-xs text-gray-500 mt-0.5">{result.explanation}</p>
            </div>
            {result.grade_result && <ScoreBadge score={result.grade_result.score} />}
          </div>

          <textarea
            ref={promptTextRef}
            className={`${textareaClass} bg-brand-50 border-brand-200`}
            rows={8}
            readOnly
            value={result.prompt}
          />

          <div className="flex items-center gap-3 flex-wrap">
            <button
              type="button"
              onClick={handleCopy}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium
                text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copied ? '✓ Copied!' : 'Copy prompt'}
            </button>
            <button
              type="button"
              onClick={handleGradeThis}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm
                hover:bg-brand-700 transition-colors"
            >
              Grade this prompt →
            </button>
            <button
              type="button"
              onClick={handleEdit}
              className="text-sm text-gray-500 hover:text-gray-700 font-medium transition-colors"
            >
              Edit answers
            </button>
          </div>

          {result.grade_result && (
            <GradeResultCard result={result.grade_result} title="Auto-grade" />
          )}
        </div>
      )}
    </div>
  )
}
