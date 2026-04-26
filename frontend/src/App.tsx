import { createContext, useContext } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Compare from './pages/Compare'
import Batch from './pages/Batch'
import Build from './pages/Build'
import SettingsPage from './pages/SettingsPage'
import { useStatus } from './hooks/useStatus'
import type { StatusResponse } from './lib/types'

interface StatusContextValue {
  status: StatusResponse | null
  loading: boolean
  refetch: () => void
  notification: string | null
  dismissNotification: () => void
}

export const StatusContext = createContext<StatusContextValue>({
  status: null,
  loading: true,
  refetch: () => {},
  notification: null,
  dismissNotification: () => {},
})

export function useStatusContext() {
  return useContext(StatusContext)
}

export default function App() {
  const statusState = useStatus()

  return (
    <StatusContext.Provider value={statusState}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="compare" element={<Compare />} />
            <Route path="batch" element={<Batch />} />
            <Route path="build" element={<Build />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </StatusContext.Provider>
  )
}
