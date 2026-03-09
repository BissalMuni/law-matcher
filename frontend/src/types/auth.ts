/**
 * Authentication Types
 */

export interface User {
  id: number
  username: string
  user_type: 'ADMIN' | 'USER' | 'GENERAL' | 'DEPARTMENT'
  full_name?: string
  department_name?: string
}

export interface LoginRequest {
  username: string
  password: string
  department_name?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string, departmentName?: string) => Promise<void>
  loginSimple: (role: 'admin' | 'user', name: string, departmentName?: string) => void
  logout: () => void
  isAuthenticated: boolean
  isLoading: boolean
}
