import { useState } from 'react'
import { useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
} from '@mui/material'
import { loginStart, loginSuccess, loginFailure } from '../store/authSlice'
import { authService } from '../services/auth'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    dispatch(loginStart())

    try {
      const response = await authService.login(username, password)
      dispatch(loginSuccess(response.user))
      navigate('/dashboard')
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Login failed'
      setError(errorMessage)
      dispatch(loginFailure(errorMessage))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Print Job Manager
        </Typography>
        <Typography variant="subtitle1" gutterBottom align="center" color="text.secondary">
          Sign in to continue
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <TextField
            fullWidth
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            margin="normal"
            required
            autoFocus
            disabled={loading}
          />
          <TextField
            fullWidth
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            margin="normal"
            required
            disabled={loading}
          />
          <Button
            fullWidth
            type="submit"
            variant="contained"
            size="large"
            sx={{ mt: 3 }}
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>
        </Box>

        <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 3 }}>
          Default: admin / admin123
        </Typography>
      </Paper>
    </Container>
  )
}
