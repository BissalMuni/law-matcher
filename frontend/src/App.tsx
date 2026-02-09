import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
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
import LawList from './pages/LawList'
import LawChangeList from './pages/LawChangeList'
import ReviewList from './pages/ReviewList'
import ReviewDetail from './pages/ReviewDetail'
import Statistics from './pages/Statistics'

function App() {
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
