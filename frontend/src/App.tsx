import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Spin } from 'antd'
import koKR from 'antd/locale/ko_KR'
import { AuthProvider } from './contexts/AuthContext'
import MainLayout from './components/layout/MainLayout'
import ProtectedRoute from './components/ProtectedRoute'
import RoleProtectedRoute from './components/RoleProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DepartmentList from './pages/DepartmentList'
import DepartmentDetail from './pages/DepartmentDetail'
import OrdinanceList from './pages/OrdinanceList'
import OrdinanceDetail from './pages/OrdinanceDetail'
import LawList from './pages/LawList'
import LawChangeList from './pages/LawChangeList'
import ReviewList from './pages/ReviewList'
import ReviewDetail from './pages/ReviewDetail'
import Maintenance from './pages/Maintenance'
import AdminSettings from './pages/AdminSettings'
import AiAnalytics from './pages/AiAnalytics'
import DetectionCompare from './pages/DetectionCompare'
import ChangePassword from './pages/ChangePassword'
import BatchProcessing from './pages/BatchProcessing'
import { maintenanceApi } from './services/api'

function App() {
  const [maintenanceMode, setMaintenanceMode] = useState(false)
  const [maintenanceMessage, setMaintenanceMessage] = useState('')
  const [checking, setChecking] = useState(true)

  // URL 파라미터로 점검모드 우회 (?bypass=admin)
  const isBypass = new URLSearchParams(window.location.search).get('bypass') === 'admin'

  useEffect(() => {
    maintenanceApi
      .getStatus()
      .then((res) => {
        setMaintenanceMode(res.enabled)
        setMaintenanceMessage(res.message)
      })
      .catch(() => {
        // API 실패 시 점검모드 아닌 것으로 간주
        setMaintenanceMode(false)
      })
      .finally(() => setChecking(false))
  }, [])

  if (checking) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  // 점검모드 활성화 && 우회 파라미터 없음 → 정비중 페이지
  if (maintenanceMode && !isBypass) {
    return (
      <ConfigProvider locale={koKR}>
        <Maintenance message={maintenanceMessage} />
      </ConfigProvider>
    )
  }

  return (
    <ConfigProvider locale={koKR}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/landing" element={<Landing />} />
            <Route path="/login" element={<Login />} />

            {/* Protected routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<MainLayout />}>
                <Route index element={<Navigate to="/ordinances" replace />} />

                {/* Shared routes (ADMIN + USER) */}
                <Route path="ordinances" element={<OrdinanceList />} />
                <Route path="ordinances/:id" element={<OrdinanceDetail />} />
                <Route path="dashboard" element={<Dashboard />} />

                {/* ADMIN only routes */}
                <Route element={<RoleProtectedRoute allowedRoles={['ADMIN']} />}>
                  <Route path="laws" element={<LawList />} />
                  <Route path="amendments" element={<LawChangeList />} />
                  <Route path="departments" element={<DepartmentList />} />
                  <Route path="departments/:id" element={<DepartmentDetail />} />
                  <Route path="reviews" element={<ReviewList />} />
                  <Route path="reviews/:id" element={<ReviewDetail />} />
                  <Route path="admin/settings" element={<AdminSettings />} />
                  <Route path="admin/ai-analytics" element={<AiAnalytics />} />
                  <Route path="admin/detection-compare" element={<DetectionCompare />} />
                  <Route path="admin/batch" element={<BatchProcessing />} />
                  <Route path="change-password" element={<ChangePassword />} />
                </Route>
              </Route>
            </Route>

            {/* Redirect any unknown routes to landing */}
            <Route path="*" element={<Navigate to="/landing" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ConfigProvider>
  )
}

export default App
