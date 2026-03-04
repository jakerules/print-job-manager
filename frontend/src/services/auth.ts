import { apiService } from './api'
import { LoginResponse, User } from '../types'

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await apiService.post<LoginResponse>('/auth/login', {
      username,
      password,
    })
    
    if (response.access_token && response.refresh_token) {
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      localStorage.setItem('user', JSON.stringify(response.user))
    }
    
    return response
  },

  async logout(): Promise<void> {
    try {
      await apiService.post('/auth/logout')
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiService.get<{ success: boolean; user: User }>('/auth/me')
    return response.user
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiService.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user')
    return userStr ? JSON.parse(userStr) : null
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token')
  },
}
