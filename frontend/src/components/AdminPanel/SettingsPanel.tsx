import { useEffect, useState } from 'react'
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Alert,
  Snackbar,
  Divider,
  CircularProgress,
} from '@mui/material'
import { Save } from '@mui/icons-material'
import { apiService } from '../../services/api'

interface SettingsMap {
  [category: string]: { [key: string]: string }
}

const CATEGORY_LABELS: Record<string, string> = {
  google: 'Google Sheets',
  printing: 'Printing',
  script: 'Script / Polling',
  footer: 'PDF Footer',
  notifications: 'Notifications',
}

const BOOLEAN_KEYS = new Set([
  'bypass_receipt_printer',
  'bypass_pdf_printer',
  'cleanup_after_processing',
  'enable_footer',
  'websocket_notifications',
  'browser_push_notifications',
  'email_notifications',
  'sound_alerts',
])

const LABEL_OVERRIDES: Record<string, string> = {
  spreadsheet_id: 'Spreadsheet ID',
  sheet_name: 'Sheet Name',
  adobe_reader_path: 'Adobe Reader Path',
  cover_sheet_printer: 'Cover Sheet Printer',
  pdf_printer: 'PDF Printer',
  receipt_printer: 'Receipt Printer',
  bypass_receipt_printer: 'Bypass Receipt Printer',
  bypass_pdf_printer: 'Bypass PDF Printer',
  poll_interval: 'Poll Interval (seconds)',
  cleanup_after_processing: 'Cleanup After Processing',
  cleanup_delay_minutes: 'Cleanup Delay (minutes)',
  enable_footer: 'Enable Footer',
  footer_font_size: 'Footer Font Size',
  footer_font_family: 'Footer Font Family',
  websocket_notifications: 'WebSocket Notifications',
  browser_push_notifications: 'Browser Push Notifications',
  email_notifications: 'Email Notifications',
  sound_alerts: 'Sound Alerts',
}

function keyLabel(key: string): string {
  return LABEL_OVERRIDES[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function SettingsPanel() {
  const [settings, setSettings] = useState<SettingsMap>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

  const loadSettings = async () => {
    setLoading(true)
    try {
      const res = await apiService.get<{ success: boolean; settings: SettingsMap }>('/settings')
      setSettings(res.settings || {})
      setDirty(false)
    } catch {
      setSnackbar({ open: true, message: 'Failed to load settings', severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSettings() }, [])

  const handleChange = (category: string, key: string, value: string) => {
    setSettings((prev) => ({
      ...prev,
      [category]: { ...prev[category], [key]: value },
    }))
    setDirty(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const flat: Record<string, string> = {}
      for (const cat of Object.values(settings)) {
        for (const [k, v] of Object.entries(cat)) {
          flat[k] = v
        }
      }
      await apiService.put('/settings', { settings: flat })
      setSnackbar({ open: true, message: 'Settings saved', severity: 'success' })
      setDirty(false)
    } catch {
      setSnackbar({ open: true, message: 'Failed to save settings', severity: 'error' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
  }

  const categories = Object.keys(CATEGORY_LABELS).filter((c) => settings[c])

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">System Settings</Typography>
        <Button variant="contained" startIcon={<Save />} onClick={handleSave} disabled={!dirty || saving}>
          {saving ? 'Saving…' : 'Save Changes'}
        </Button>
      </Box>

      {categories.map((category) => (
        <Paper key={category} sx={{ p: 3, mb: 2 }}>
          <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
            {CATEGORY_LABELS[category] || category}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Box display="flex" flexDirection="column" gap={2}>
            {Object.entries(settings[category]).map(([key, value]) =>
              BOOLEAN_KEYS.has(key) ? (
                <FormControlLabel
                  key={key}
                  control={
                    <Switch
                      checked={value === 'true'}
                      onChange={(e) => handleChange(category, key, e.target.checked ? 'true' : 'false')}
                    />
                  }
                  label={keyLabel(key)}
                />
              ) : (
                <TextField
                  key={key}
                  label={keyLabel(key)}
                  value={value}
                  onChange={(e) => handleChange(category, key, e.target.value)}
                  size="small"
                  fullWidth
                />
              ),
            )}
          </Box>
        </Paper>
      ))}

      {categories.length === 0 && (
        <Alert severity="info">No settings found. Settings will appear after the backend initializes.</Alert>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  )
}
