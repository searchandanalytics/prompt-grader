import { Link, NavLink, Outlet } from 'react-router-dom'
import { Settings } from 'lucide-react'
import { useStatusContext } from '../App'
import ProviderBadge from './ProviderBadge'
import OllamaBanner from './OllamaBanner'
import ProviderFallbackBanner from './ProviderFallbackBanner'

const NAV = [
  { to: '/', label: 'Grade' },
  { to: '/compare', label: 'Compare' },
  { to: '/batch', label: 'Batch' },
  { to: '/build', label: '✨ Build' },
]

export default function Layout() {
  const { status, loading, notification, dismissNotification } = useStatusContext()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <Link to="/" className="text-lg font-bold tracking-tight text-brand-700 hover:opacity-80">PromptGrade</Link>
            <nav className="flex gap-1 overflow-x-auto">
              {NAV.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-brand-50 text-brand-700'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <ProviderBadge status={status} loading={loading} />
            <NavLink
              to="/settings"
              title="Settings"
              className={({ isActive }) =>
                `rounded-md p-1.5 transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
                }`
              }
            >
              <Settings size={18} />
            </NavLink>
          </div>
        </div>
      </header>

      {notification && <ProviderFallbackBanner message={notification} onDismiss={dismissNotification} />}
      {status?.judge_provider === 'none' && !loading && <OllamaBanner />}

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
