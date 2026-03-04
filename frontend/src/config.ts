// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api'
export const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:5000'

// Features
export const FEATURES = {
  BARCODE_SCANNING: true,
  BROWSER_NOTIFICATIONS: true,
  EMAIL_NOTIFICATIONS: false,
}

// App Configuration
export const APP_NAME = 'Print Job Manager'
export const APP_VERSION = '1.0.0'

// Pagination
export const DEFAULT_PAGE_SIZE = 50
export const MAX_PAGE_SIZE = 100

// Timeouts
export const API_TIMEOUT = 30000 // 30 seconds
export const WEBSOCKET_RECONNECT_DELAY = 5000 // 5 seconds

// User Roles
export const ROLES = {
  ADMIN: 'admin',
  MANAGER: 'manager',
  STAFF: 'staff',
  SUBMITTER: 'submitter',
} as const

// Job Status
export const JOB_STATUS = {
  PENDING: 'pending',
  ACKNOWLEDGED: 'acknowledged',
  COMPLETED: 'completed',
} as const
