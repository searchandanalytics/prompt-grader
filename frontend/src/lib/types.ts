// Synced with backend Pydantic schemas in backend/app/models/schemas.py

export type GraderType = 'rule_based' | 'llm_judge' | 'hybrid'

export type JudgeProvider = 'anthropic' | 'openai' | 'google' | 'groq' | 'ollama' | 'none'

// ---------------------------------------------------------------------------
// BYOK provider config (Feature 1)
// ---------------------------------------------------------------------------

/** Mirrors backend KeySource literal — all five spec values. */
export type KeySource = 'ui_session' | 'ui_persisted' | 'env' | 'ollama_auto' | 'rule_based'

/** Provider names the UI exposes for selection. */
export type ProviderName = 'anthropic' | 'openai' | 'google' | 'groq' | 'ollama' | 'rule_based'

/** Client-side representation of a user-supplied provider configuration. */
export interface ProviderConfig {
  provider: ProviderName
  apiKey: string | null
  model: string | null
  remember: boolean
}

export interface RubricCriteria {
  weight: number
  description: string
}

export interface Rubric {
  clarity: RubricCriteria
  specificity: RubricCriteria
  structure: RubricCriteria
  task_alignment: RubricCriteria
  safety: RubricCriteria
}

export interface GradeResult {
  score: number
  breakdown: Record<string, number>
  feedback: string
  grader: GraderType
  provider: JudgeProvider
  metadata: Record<string, unknown>
}

export interface GradeRequest {
  prompt: string
  rubric?: Partial<Rubric>
  grader?: GraderType
  judge_model?: string
}

export interface OllamaModelsResponse {
  models: string[]
}

export interface GradeResponse {
  prompt: string
  result: GradeResult
}

export interface CompareRequest {
  prompt_a: string
  prompt_b: string
  rubric?: Partial<Rubric>
  grader?: GraderType
}

export interface CompareResponse {
  prompt_a: string
  prompt_b: string
  result_a: GradeResult
  result_b: GradeResult
  winner: 'a' | 'b' | 'tie'
}

export interface BatchItem {
  id?: string
  prompt: string
}

export interface BatchRequest {
  items: BatchItem[]
  rubric?: Partial<Rubric>
  grader?: GraderType
}

export interface BatchResultItem {
  id: string
  prompt: string
  result: GradeResult
  error?: string
}

export interface StatusResponse {
  status: string
  judge_provider: JudgeProvider
  judge_model: string | null
  mode: 'rule_based' | 'llm' | 'hybrid'
  key_source: KeySource
  /** Set when the server fell back from an unhealthy provider. Null when healthy. */
  unhealthy_reason?: string | null
}

// ---------------------------------------------------------------------------
// Prompt Builder (Feature 2 / Feature 4)
// ---------------------------------------------------------------------------

export type PromptStyle = 'formal' | 'casual' | 'technical' | 'creative'
export type PromptTone = 'friendly' | 'authoritative' | 'playful' | 'empathetic' | 'neutral'
export type ResponseFormat = 'paragraph' | 'bulleted_list' | 'json' | 'table' | 'markdown' | 'code'

export interface PromptBlueprint {
  task: string
  context?: string
  objective: string
  style: PromptStyle
  tone: PromptTone
  audience: string
  response_format: ResponseFormat
  length?: string
  examples?: string
  constraints?: string
}

export interface BuildResponse {
  prompt: string
  explanation: string
  generated_by: 'llm' | 'template'
  grade_result: GradeResult | null
}

export const DEFAULT_RUBRIC: Rubric = {
  clarity: { weight: 0.2, description: 'Is the prompt clear and unambiguous?' },
  specificity: { weight: 0.2, description: 'Does the prompt provide enough specific detail?' },
  structure: { weight: 0.2, description: 'Is the prompt well-structured and logically ordered?' },
  task_alignment: { weight: 0.2, description: 'Does the prompt align with the intended task?' },
  safety: { weight: 0.2, description: 'Is the prompt free of harmful or unsafe content?' },
}

export const DIMENSION_LABELS: Record<string, string> = {
  clarity: 'Clarity',
  specificity: 'Specificity',
  structure: 'Structure',
  task_alignment: 'Task Alignment',
  safety: 'Safety',
}
