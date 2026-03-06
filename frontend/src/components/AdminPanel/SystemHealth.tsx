import { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Chip,
  Divider,
  CircularProgress,
  Button,
  Alert,
} from '@mui/material'
import {
  CheckCircle,
  Error as ErrorIcon,
  Storage,
  Cloud,
  Timer,
} from '@mui/icons-material'
import api from '../../services/api'

interface SystemStatus {
  uptime_seconds: number
  python_version: string
  database: {
    status: string
    user_count: number
    size_bytes: number
  }
  google_sheets: {
    status: string
  }
}

export default function SystemHealth() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [sheetsTest, setSheetsTest] = useState<{ message?: string; error?: string } | null>(null)
  const [testingSheets, setTestingSheets] = useState(false)

  useEffect(() => {
    api.get('/system/status')
      .then((res) => setStatus(res.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  const testSheetsConnection = async () => {
    setTestingSheets(true)
    setSheetsTest(null)
    try {
      const res = await api.post('/system/test-sheets')
      setSheetsTest(res.data)
    } catch {
      setSheetsTest({ error: 'Request failed' })
    } finally {
      setTestingSheets(false)
    }
  }

  const formatUptime = (secs: number) => {
    const d = Math.floor(secs / 86400)
    const h = Math.floor((secs % 86400) / 3600)
    const m = Math.floor((secs % 3600) / 60)
    if (d > 0) return `${d}d ${h}h ${m}m`
    if (h > 0) return `${h}h ${m}m`
    return `${m}m`
  }

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  if (loading) return <CircularProgress />

  if (error || !status) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <ErrorIcon color="error" />
          <Typography>Unable to fetch system status</Typography>
        </Box>
      </Paper>
    )
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>System Health</Typography>
      <Divider sx={{ mb: 2 }} />

      <Box display="flex" flexDirection="column" gap={2}>
        <Box display="flex" alignItems="center" gap={2}>
          <Timer color="primary" />
          <Box>
            <Typography variant="body2" color="text.secondary">Uptime</Typography>
            <Typography variant="body1">{formatUptime(status.uptime_seconds)}</Typography>
          </Box>
        </Box>

        <Box display="flex" alignItems="center" gap={2}>
          <Storage color="primary" />
          <Box flexGrow={1}>
            <Typography variant="body2" color="text.secondary">Database</Typography>
            <Box display="flex" gap={1} alignItems="center">
              <Chip
                icon={status.database.status === 'connected' ? <CheckCircle /> : <ErrorIcon />}
                label={status.database.status}
                color={status.database.status === 'connected' ? 'success' : 'error'}
                size="small"
              />
              <Typography variant="caption">
                {status.database.user_count} users • {formatBytes(status.database.size_bytes)}
              </Typography>
            </Box>
          </Box>
        </Box>

        <Box display="flex" alignItems="center" gap={2}>
          <Cloud color="primary" />
          <Box flexGrow={1}>
            <Typography variant="body2" color="text.secondary">Google Sheets</Typography>
            <Box display="flex" gap={1} alignItems="center">
              <Chip
                icon={status.google_sheets.status === 'connected' ? <CheckCircle /> : <ErrorIcon />}
                label={status.google_sheets.status}
                color={status.google_sheets.status === 'connected' ? 'success' : 'warning'}
                size="small"
              />
              <Button size="small" variant="outlined" onClick={testSheetsConnection} disabled={testingSheets}>
                {testingSheets ? 'Testing...' : 'Test Connection'}
              </Button>
            </Box>
            {sheetsTest && (
              <Alert severity={sheetsTest.error ? 'error' : 'success'} sx={{ mt: 1 }}>
                {sheetsTest.message || sheetsTest.error}
              </Alert>
            )}
          </Box>
        </Box>

        <Divider />
        <Typography variant="caption" color="text.secondary">
          Python {status.python_version?.split(' ')[0]}
        </Typography>
      </Box>
    </Paper>
  )
}
