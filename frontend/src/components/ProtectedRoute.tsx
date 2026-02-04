import { Navigate, Outlet } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuth } from '../contexts/AuthContext'

const ProtectedRoute = () => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Spin size="large" tip="인증 확인 중..." />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/landing" replace />
  }

  return <Outlet />
}

export default ProtectedRoute
