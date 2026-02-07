/**
 * Authentication Types
 */

export interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  user_type: 'DEPARTMENT' | 'GENERAL'
  department_id: number | null
  department_name?: string | null
  department_code?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
  full_name?: string
  user_type: 'DEPARTMENT' | 'GENERAL'
  department_id?: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface PasswordChangeRequest {
  current_password: string
  new_password: string
}

export interface AuthContextType {
  user: User | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  isLoading: boolean
}
