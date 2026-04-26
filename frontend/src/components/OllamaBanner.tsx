import { Link } from 'react-router-dom'

export default function OllamaBanner() {
  return (
    <div className="border-b border-yellow-200 bg-yellow-50 px-4 py-2">
      <p className="mx-auto max-w-6xl text-sm text-yellow-800">
        No LLM provider configured — running in rule-based mode.{' '}
        <a
          href="https://ollama.com"
          target="_blank"
          rel="noreferrer"
          className="font-medium underline underline-offset-2"
        >
          Install Ollama (free, local)
        </a>{' '}
        or{' '}
        <Link to="/settings" className="font-medium underline underline-offset-2">
          add an API key
        </Link>{' '}
        to enable LLM grading.
      </p>
    </div>
  )
}
