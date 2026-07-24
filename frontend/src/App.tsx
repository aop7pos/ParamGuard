import { Routes, Route } from 'react-router-dom'
import MainLayout from '@/components/layout/MainLayout'
import WorkbenchPage from '@/pages/WorkbenchPage'
import HistoryPage from '@/pages/HistoryPage'
import AuditLogPage from '@/pages/AuditLogPage'
import PoliciesPage from '@/pages/PoliciesPage'
import SettingsPage from '@/pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<WorkbenchPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="audit" element={<AuditLogPage />} />
        <Route path="policies" element={<PoliciesPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
