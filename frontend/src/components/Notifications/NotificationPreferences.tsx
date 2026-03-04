import { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Snackbar,
  Button,
} from '@mui/material'
import { Save } from '@mui/icons-material'
import api from '../../services/api'

interface Prefs {
  browser_notifications: boolean
  sound_alerts: boolean
  email_notifications: boolean
}

export default function NotificationPreferences() {
  const [prefs, setPrefs] = useState<Prefs>({
    browser_notifications: true,
    sound_alerts: true,
    email_notifications: false,
  })
  const [dirty, setDirty] = useState(false)
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

  useEffect(() => {
    api.get('/api/notifications/preferences')
      .then((res) => setPrefs(res.data.preferences))
      .catch(() => {})
  }, [])

  const handleToggle = (field: keyof Prefs) => {
    setPrefs((prev) => ({ ...prev, [field]: !prev[field] }))
    setDirty(true)
  }

  const handleSave = async () => {
    try {
      await api.put('/api/notifications/preferences', prefs)
      setSnackbar({ open: true, message: 'Preferences saved', severity: 'success' })
      setDirty(false)

      // Request browser notification permission if enabled
      if (prefs.browser_notifications && 'Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission()
      }
    } catch {
      setSnackbar({ open: true, message: 'Failed to save', severity: 'error' })
    }
  }

  return (
    <Paper sx={{ p: 3, maxWidth: 500 }}>
      <Typography variant="h6" gutterBottom>Notification Preferences</Typography>
      <Divider sx={{ mb: 2 }} />

      <Box display="flex" flexDirection="column" gap={1}>
        <FormControlLabel
          control={<Switch checked={prefs.browser_notifications} onChange={() => handleToggle('browser_notifications')} />}
          label="Browser Push Notifications"
        />
        <Typography variant="caption" color="text.secondary" sx={{ ml: 6, mt: -1 }}>
          Show desktop notifications for new jobs and status changes
        </Typography>

        <FormControlLabel
          control={<Switch checked={prefs.sound_alerts} onChange={() => handleToggle('sound_alerts')} />}
          label="Sound Alerts"
        />
        <Typography variant="caption" color="text.secondary" sx={{ ml: 6, mt: -1 }}>
          Play a sound when new jobs arrive or scans complete
        </Typography>

        <FormControlLabel
          control={<Switch checked={prefs.email_notifications} onChange={() => handleToggle('email_notifications')} />}
          label="Email Notifications"
        />
        <Typography variant="caption" color="text.secondary" sx={{ ml: 6, mt: -1 }}>
          Receive email summaries of pending jobs (coming soon)
        </Typography>
      </Box>

      {dirty && (
        <Button variant="contained" startIcon={<Save />} onClick={handleSave} sx={{ mt: 2 }}>
          Save Preferences
        </Button>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Paper>
  )
}
