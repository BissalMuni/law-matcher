import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface RoleProtectedRouteProps {
  allowedRoles: ('ADMIN' | 'USER')[]
}

const RoleProtectedRoute = ({ allowedRoles }: RoleProtectedRouteProps) => {
  const { user } = useAuth()

  if (!user || !allowedRoles.includes(user.user_type as 'ADMIN' | 'USER')) {
    return <Navigate to="/ordinances" replace />
  }

  return <Outlet />
}

export default RoleProtectedRoute
