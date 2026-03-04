import { Navigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { RootState } from '../../store/store'
import { authService } from '../../services/auth'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: 'admin' | 'manager' | 'staff' | 'submitter'
}

export default function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useSelector((state: RootState) => state.auth)

  // Check if user is authenticated
  if (!isAuthenticated && !authService.isAuthenticated()) {
    return <Navigate to="/login" replace />
  }

  // Check role if required
  if (requiredRole && user) {
    const roleHierarchy = {
      admin: 4,
      manager: 3,
      staff: 2,
      submitter: 1,
    }
    
    const userLevel = roleHierarchy[user.role]
    const requiredLevel = roleHierarchy[requiredRole]
    
    if (userLevel < requiredLevel) {
      return <Navigate to="/dashboard" replace />
    }
  }

  return <>{children}</>
}
