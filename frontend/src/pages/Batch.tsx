import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { BatchItem, BatchResultItem, GraderType } from '../lib/types'
import GraderControlBar from '../components/GraderControlBar'
import ScoreBadge from '../components/ScoreBadge'
import { useStatusContext } from '../App'
import { useAvailableModels } from '../hooks/useAvailableModels'

export default function Batch() {
  const [items, setItems] = useState<BatchItem[]>([])
  const [grader, setGrader] = useState<GraderType>('hybrid')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [results, setResults] = useState<BatchResultItem[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [parseError, setParseError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const { status } = useStatusContext()
  const isOllama = status?.judge_provider === 'ollama'
  const availableModels = useAvailableModels()

  // Default selectedModel to first available on mount.
  useEffect(() => {
    if (availableModels.length > 0 && !selectedModel) {
      setSelectedModel(availableModels[0])
    }
  }, [availableModels]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setParseError(null)
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const text = reader.result as string
        const parsed = parseFile(file.name, text)
        setItems(parsed)
      } catch (err) {
        setParseError(err instanceof Error ? err.message : 'Parse error')
        setItems([])
      }
    }
    reader.readAsText(file)
  }

  async function handleRun() {
    if (!items.length) return
    setRunning(true)
    setResults([])
    setErrors([])
    try {
      const judge_model =
        isOllama && grader !== 'rule_based' && selectedModel
          ? `ollama/${selectedModel}`
          : undefined
      await api.batch(
        { items, grader, judge_model },
        (item) => setResults((prev) => [...prev, item]),
        (err) => setErrors((prev) => [...prev, err.message]),
      )
    } finally {
      setRunning(false)
    }
  }

  const progress = items.length ? Math.round((results.length / items.length) * 100) : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Batch Grading</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload a JSON or CSV file with prompts to grade them all at once. Results stream in as they
          complete.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <div>
          <p className="mb-2 text-xs text-gray-500">
            <strong>JSON</strong>: <code>{`[{"id":"1","prompt":"..."}]`}</code> &nbsp;|&nbsp;
            <strong>CSV</strong>: columns <code>id</code> (optional) + <code>prompt</code>
          </p>
          <label
            className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed
              border-gray-200 bg-gray-50 p-8 text-center transition hover:border-brand-500 hover:bg-brand-50"
          >
            <span className="text-sm text-gray-500">
              {items.length
                ? `${items.length} prompt${items.length !== 1 ? 's' : ''} loaded`
                : 'Click to upload JSON or CSV'}
            </span>
            <input
              ref={fileRef}
              type="file"
              accept=".json,.csv"
              className="sr-only"
              onChange={handleFile}
            />
          </label>
          {parseError && (
            <p className="mt-2 text-xs text-red-600">{parseError}</p>
          )}
        </div>

        <GraderControlBar
          graderType={grader}
          onGraderTypeChange={(v) => { setGrader(v); setResults([]); setErrors([]) }}
          model={selectedModel}
          onModelChange={setSelectedModel}
          availableModels={availableModels}
          actionLabel={running ? `Running… ${results.length}/${items.length}` : 'Run Batch'}
          onAction={handleRun}
          actionDisabled={running || !items.length}
        />

        {running && (
          <div className="w-full rounded-full bg-gray-100 h-2">
            <div
              className="h-2 rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {errors.map((err, i) => (
        <p key={i} className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2 border border-red-100">
          {err}
        </p>
      ))}

      {results.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">ID</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Prompt</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Grade</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {results.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2 text-gray-500 font-mono text-xs">{row.id}</td>
                  <td className="px-4 py-2 text-gray-800 max-w-xs truncate" title={row.prompt}>
                    {row.prompt}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <ScoreBadge score={row.result.score} />
                  </td>
                  <td className="px-4 py-2 text-gray-500 max-w-sm truncate text-xs" title={row.result.feedback}>
                    {row.result.feedback}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// File parsers
// ---------------------------------------------------------------------------

function parseFile(filename: string, text: string): BatchItem[] {
  if (filename.endsWith('.json')) {
    const data = JSON.parse(text) as unknown
    if (!Array.isArray(data)) throw new Error('JSON must be an array of objects with a "prompt" field.')
    return (data as Record<string, unknown>[]).map((row, i) => {
      if (typeof row.prompt !== 'string') throw new Error(`Item ${i} missing "prompt" field.`)
      return { id: String(row.id ?? i), prompt: row.prompt }
    })
  }
  if (filename.endsWith('.csv')) {
    return parseCsv(text)
  }
  throw new Error('Unsupported file type. Upload a .json or .csv file.')
}

function parseCsv(text: string): BatchItem[] {
  const lines = text.trim().split('\n')
  if (lines.length < 2) throw new Error('CSV must have a header row and at least one data row.')
  const headers = lines[0].split(',').map((h) => h.trim().toLowerCase())
  const promptIdx = headers.indexOf('prompt')
  if (promptIdx === -1) throw new Error('CSV must have a "prompt" column.')
  const idIdx = headers.indexOf('id')

  return lines.slice(1).map((line, i) => {
    const cols = line.split(',')
    const prompt = cols[promptIdx]?.trim() ?? ''
    if (!prompt) throw new Error(`Row ${i + 2} has an empty prompt.`)
    const id = idIdx >= 0 ? cols[idIdx]?.trim() ?? String(i) : String(i)
    return { id, prompt }
  })
}
