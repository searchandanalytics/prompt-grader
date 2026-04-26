import ProviderSelector from '../components/ProviderSelector'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configure your LLM judge provider. This is a{' '}
          <strong>Bring Your Own Key (BYOK)</strong> platform — the server never stores or proxies
          your API keys. Keys are sent directly with each request and discarded immediately.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-2">
        <h2 className="text-base font-semibold text-gray-800">LLM Judge Provider</h2>
        <p className="text-sm text-gray-500">
          Provider selection priority (highest wins):
        </p>
        <ol className="text-sm text-gray-500 list-decimal list-inside space-y-0.5 pl-1">
          <li>Key saved here in your browser (if "Remember" is on)</li>
          <li>Key entered here for this session (if "Remember" is off)</li>
          <li>API key in <code className="font-mono text-xs bg-gray-100 px-1 rounded">backend/.env</code></li>
          <li>Ollama auto-detected (local, free)</li>
          <li>Rule-based only (no LLM)</li>
        </ol>

        <div className="pt-4">
          <ProviderSelector />
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800">Privacy notes</h2>
        <ul className="mt-2 space-y-1.5 text-sm text-gray-500 list-disc list-inside">
          <li>API keys are <strong>never</strong> logged, never sent in URL parameters, and never stored on the server.</li>
          <li>Keys pass through HTTP headers (<code className="font-mono text-xs bg-gray-100 px-1 rounded">X-Provider-Key</code>) — use HTTPS in production.</li>
          <li>Choosing "Remember" stores the key in <code className="font-mono text-xs bg-gray-100 px-1 rounded">localStorage</code> under <code className="font-mono text-xs bg-gray-100 px-1 rounded">promptgrade.providerConfig</code>.</li>
          <li>LLM costs are charged to your own account — check your provider's pricing page for estimates.</li>
        </ul>
      </div>
    </div>
  )
}
