import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import koKR from 'antd/locale/ko_KR'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import DepartmentList from './pages/DepartmentList'
import DepartmentDetail from './pages/DepartmentDetail'
import OrdinanceList from './pages/OrdinanceList'
import OrdinanceDetail from './pages/OrdinanceDetail'
import AmendmentList from './pages/AmendmentList'
import ReviewList from './pages/ReviewList'
import ReviewDetail from './pages/ReviewDetail'

function App() {
  return (
    <ConfigProvider locale={koKR}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="ordinances" element={<OrdinanceList />} />
            <Route path="ordinances/:id" element={<OrdinanceDetail />} />
            <Route path="departments" element={<DepartmentList />} />
            <Route path="departments/:id" element={<DepartmentDetail />} />
            <Route path="amendments" element={<AmendmentList />} />
            <Route path="reviews" element={<ReviewList />} />
            <Route path="reviews/:id" element={<ReviewDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
