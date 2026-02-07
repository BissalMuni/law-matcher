import { Navigate, Outlet } from 'react-router-dom'
import { Spin, Alert } from 'antd'
import { useAuth } from '../contexts/AuthContext'

const ProtectedRoute = () => {
  const { isAuthenticated, isLoading, user } = useAuth()

  // 개발 모드 체크
  const isDevBypass = () => {
    const envBypass = import.meta.env.VITE_DEV_BYPASS_AUTH === 'true'
    const urlParams = new URLSearchParams(window.location.search)
    const queryBypass = urlParams.get('dev') === 'true'
    return envBypass || queryBypass
  }

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

  // 개발 모드일 경우 경고 표시
  const devBypassActive = isDevBypass()

  return (
    <>
      {devBypassActive && !user && (
        <Alert
          message="개발자 모드"
          description="현재 인증을 우회하여 접근 중입니다. 프로덕션에서는 비활성화되어야 합니다."
          type="warning"
          showIcon
          closable
          style={{ margin: '16px' }}
        />
      )}
      <Outlet />
    </>
  )
}

export default ProtectedRoute
