export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'manager' | 'staff' | 'submitter'
  is_active: boolean
  created_at?: string
  last_login?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
}

export interface LoginResponse {
  success: boolean
  access_token: string
  refresh_token: string
  user: User
}

export interface Job {
  job_id: string
  email: string
  room: string
  quantity: string
  paper_size: string
  two_sided: string
  date_submitted: string
  job_deadline: string
  staff_notes: string
  user_notes: string
  status: {
    acknowledged: boolean
    completed: boolean
  }
  row_number?: number
}

export interface JobStats {
  total: number
  pending: number
  acknowledged: number
  completed: number
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  total: number
  limit: number
  offset: number
}

export interface WebSocketEvent {
  type: 'job:new' | 'job:updated' | 'stats:update' | 'notification'
  data: any
  timestamp: string
}
