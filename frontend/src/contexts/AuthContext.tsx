import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, AuthContextType } from '../types/auth'
import { authApi } from '../services/api'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'law_matcher_token'
const USER_KEY = 'law_matcher_user'

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // 환경변수만 체크하도록 변경
  const isDevBypass = () => {
    return import.meta.env.VITE_DEV_BYPASS_AUTH === 'true'
  }

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY)
      const storedUser = localStorage.getItem(USER_KEY)

      // Dev bypass 모드에서는 저장된 세션이 없어도 관리자 세션을 자동 주입
      if (isDevBypass() && (!storedToken || !storedUser)) {
        const devAdminUser: User = {
          id: 0,
          username: 'admin',
          user_type: 'ADMIN',
          full_name: '개발자 관리자',
        }
        const devToken = 'simple_admin_dev'

        setToken(devToken)
        setUser(devAdminUser)
        localStorage.setItem(TOKEN_KEY, devToken)
        localStorage.setItem(USER_KEY, JSON.stringify(devAdminUser))
        setIsLoading(false)
        return
      }

      if (storedToken && storedUser) {
        // Simple login인 경우 API 검증 건너뛰기
        if (storedToken.startsWith('simple_')) {
          setToken(storedToken)
          setUser(JSON.parse(storedUser))
        } else {
          try {
            setToken(storedToken)
            setUser(JSON.parse(storedUser))

            // Verify token is still valid by fetching current user
            const currentUser = await authApi.me()
            setUser(currentUser)
            localStorage.setItem(USER_KEY, JSON.stringify(currentUser))
          } catch (error) {
            // Token is invalid, clear auth state
            console.error('Token validation failed:', error)
            logout()
          }
        }
      }

      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = async (username: string, password: string, departmentName?: string, departmentId?: number) => {
    try {
      const response = await authApi.login({ username, password, department_name: departmentName })
      const { access_token, user: userData } = response

      // 부서 로그인 시 선택한 부서 ID를 user 객체에 주입
      if (departmentId && !userData.department_id) {
        userData.department_id = departmentId
      }

      setToken(access_token)
      setUser(userData)

      // Store in localStorage
      localStorage.setItem(TOKEN_KEY, access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(userData))
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }

  const loginSimple = (role: 'admin' | 'user', name: string, departmentName?: string) => {
    const simpleUser: User = {
      id: role === 'admin' ? 0 : 1,
      username: name,
      user_type: role === 'admin' ? 'ADMIN' : 'USER',
      full_name: name,
      department_name: departmentName,
    }
    const simpleToken = `simple_${role}_${Date.now()}`

    setToken(simpleToken)
    setUser(simpleUser)

    localStorage.setItem(TOKEN_KEY, simpleToken)
    localStorage.setItem(USER_KEY, JSON.stringify(simpleUser))
  }

  const logout = () => {
    setToken(null)
    setUser(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const value: AuthContextType = {
    user,
    token,
    login,
    loginSimple,
    logout,
    isAuthenticated: isDevBypass() || (!!user && !!token),
    isLoading,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY)
}
