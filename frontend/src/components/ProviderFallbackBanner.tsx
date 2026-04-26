interface Props {
  message: string
  onDismiss: () => void
}

export default function ProviderFallbackBanner({ message, onDismiss }: Props) {
  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <p className="text-sm text-amber-800">
          <span className="font-medium">Provider changed:</span> {message}
        </p>
        <button
          onClick={onDismiss}
          className="shrink-0 rounded px-2 py-0.5 text-xs font-medium text-amber-700 hover:bg-amber-100"
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}
