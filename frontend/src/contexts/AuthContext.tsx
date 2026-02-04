import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, AuthContextType, RegisterRequest } from '../types/auth'
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

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY)
      const storedUser = localStorage.getItem(USER_KEY)

      if (storedToken && storedUser) {
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

      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = async (username: string, password: string) => {
    try {
      const response = await authApi.login({ username, password })
      const { access_token, user: userData } = response

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

  const register = async (data: RegisterRequest) => {
    try {
      const response = await authApi.register(data)
      const { access_token, user: userData } = response

      setToken(access_token)
      setUser(userData)

      // Store in localStorage
      localStorage.setItem(TOKEN_KEY, access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(userData))
    } catch (error) {
      console.error('Registration failed:', error)
      throw error
    }
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
    register,
    logout,
    isAuthenticated: !!user && !!token,
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
