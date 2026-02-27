import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Spin } from 'antd'
import koKR from 'antd/locale/ko_KR'
import { AuthProvider } from './contexts/AuthContext'
import MainLayout from './components/layout/MainLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DepartmentList from './pages/DepartmentList'
import DepartmentDetail from './pages/DepartmentDetail'
import OrdinanceList from './pages/OrdinanceList'
import OrdinanceDetail from './pages/OrdinanceDetail'
import ArticleList from './pages/ArticleList'
import ArticleDetail from './pages/ArticleDetail'
import RevisionNeededList from './pages/RevisionNeededList'
import LawList from './pages/LawList'
import LawChangeList from './pages/LawChangeList'
import ReviewList from './pages/ReviewList'
import ReviewDetail from './pages/ReviewDetail'
import Statistics from './pages/Statistics'
import Maintenance from './pages/Maintenance'
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
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="ordinances" element={<OrdinanceList />} />
                <Route path="ordinances/:id" element={<OrdinanceDetail />} />
                <Route path="articles" element={<ArticleList />} />
                <Route path="articles/:id" element={<ArticleDetail />} />
                <Route path="revision-needed" element={<RevisionNeededList />} />
                <Route path="laws" element={<LawList />} />
                <Route path="departments" element={<DepartmentList />} />
                <Route path="departments/:id" element={<DepartmentDetail />} />
                <Route path="amendments" element={<LawChangeList />} />
                <Route path="reviews" element={<ReviewList />} />
                <Route path="reviews/:id" element={<ReviewDetail />} />
                <Route path="statistics" element={<Statistics />} />
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
