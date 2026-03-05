import { useEffect, useState, useCallback } from 'react'
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
  Chip,
} from '@mui/material'
import { Save, Sync, SyncDisabled } from '@mui/icons-material'
import { apiService } from '../../services/api'

interface SettingsMap {
  [category: string]: { [key: string]: string }
}

interface SyncStatus {
  enabled: boolean
  last_sync_time: string | null
  last_sync_error: string | null
  last_sync_jobs_pulled: number
  last_sync_jobs_pushed: number
  sheets_configured: boolean
  google_connected: boolean
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

// These keys are managed by the OAuth / Sync section — hide from the generic form
const HIDDEN_KEYS = new Set([
  'google_credentials_json',
  'google_token_json',
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

  // Sync state
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [syncing, setSyncing] = useState(false)

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

  const loadSyncStatus = useCallback(async () => {
    try {
      const res = await apiService.get<SyncStatus & { success: boolean }>('/sync/status')
      setSyncStatus(res)
    } catch {
      // Sync endpoint may not exist on older backends
    }
  }, [])

  useEffect(() => { loadSettings(); loadSyncStatus() }, [loadSyncStatus])

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

  const handleSyncNow = async () => {
    setSyncing(true)
    try {
      const res = await apiService.post<{ success: boolean; pulled: number; pushed: number; error?: string }>('/sync/trigger', {})
      if (res.success) {
        setSnackbar({ open: true, message: `Sync complete: ${res.pulled} pulled, ${res.pushed} pushed`, severity: 'success' })
      } else {
        setSnackbar({ open: true, message: `Sync partially failed: ${res.error}`, severity: 'error' })
      }
      loadSyncStatus()
    } catch {
      setSnackbar({ open: true, message: 'Sync failed', severity: 'error' })
    } finally {
      setSyncing(false)
    }
  }

  const handleToggleSync = async (enabled: boolean) => {
    try {
      await apiService.put('/sync/toggle', { enabled })
      loadSyncStatus()
      setSnackbar({ open: true, message: `Background sync ${enabled ? 'enabled' : 'disabled'}`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Failed to toggle sync', severity: 'error' })
    }
  }

  const handleConnectGoogle = async () => {
    try {
      // Auto-save settings first so credentials.json is persisted to DB
      if (dirty) {
        const flat: Record<string, string> = {}
        for (const cat of Object.values(settings)) {
          for (const [k, v] of Object.entries(cat)) {
            flat[k] = v
          }
        }
        await apiService.put('/settings', { settings: flat })
        setDirty(false)
      }
      const res = await apiService.post<{ success: boolean; auth_url?: string; error?: string }>('/sync/oauth/start', {})
      if (res.success && res.auth_url) {
        window.open(res.auth_url, '_blank')
      } else {
        setSnackbar({ open: true, message: res.error || 'Failed to start OAuth', severity: 'error' })
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Failed to start Google authorization'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    }
  }

  const handleDisconnectGoogle = async () => {
    try {
      await apiService.post('/sync/oauth/disconnect', {})
      loadSyncStatus()
      setSnackbar({ open: true, message: 'Google Sheets disconnected', severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Failed to disconnect', severity: 'error' })
    }
  }

  // Handle OAuth redirect query params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('oauth_success') === '1') {
      setSnackbar({ open: true, message: 'Google Sheets connected successfully!', severity: 'success' })
      loadSyncStatus()
      window.history.replaceState({}, '', window.location.pathname)
    } else if (params.get('oauth_error')) {
      setSnackbar({ open: true, message: `Google OAuth error: ${params.get('oauth_error')}`, severity: 'error' })
      window.history.replaceState({}, '', window.location.pathname)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
            {Object.entries(settings[category]).filter(([key]) => !HIDDEN_KEYS.has(key)).map(([key, value]) =>
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

      {/* Google Sheets Connection & Sync Section */}
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
          Google Sheets Connection
        </Typography>
        <Divider sx={{ mb: 2 }} />

        {/* Step 1: Credentials JSON */}
        <Typography variant="body2" color="text.secondary" mb={1}>
          Paste the contents of your Google Cloud OAuth <code>credentials.json</code> file below.
          You can get this from the{' '}
          <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer">
            Google Cloud Console
          </a>{' '}
          → OAuth 2.0 Client IDs → Download JSON.
        </Typography>
        <TextField
          label="credentials.json contents"
          value={settings.google?.google_credentials_json || ''}
          onChange={(e) => handleChange('google', 'google_credentials_json', e.target.value)}
          size="small"
          fullWidth
          multiline
          minRows={2}
          maxRows={6}
          placeholder='{"installed":{"client_id":"...","client_secret":"..."}}'
          sx={{ mb: 2, fontFamily: 'monospace' }}
        />

        {/* Step 2: Connect / Disconnect */}
        {syncStatus && (
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            {syncStatus.google_connected ? (
              <>
                <Chip label="Connected" color="success" size="small" />
                <Button variant="outlined" color="error" size="small" onClick={handleDisconnectGoogle}>
                  Disconnect
                </Button>
              </>
            ) : (
              <>
                <Chip label="Not connected" color="default" size="small" />
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleConnectGoogle}
                  disabled={!settings.google?.google_credentials_json}
                >
                  Connect Google Sheets
                </Button>
                {!settings.google?.google_credentials_json && (
                  <Typography variant="caption" color="text.secondary">
                    Paste credentials above &amp; save, then connect
                  </Typography>
                )}
              </>
            )}
          </Box>
        )}

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          Sync Controls
        </Typography>

        {syncStatus ? (
          <Box display="flex" flexDirection="column" gap={2}>
            <Box display="flex" alignItems="center" gap={2}>
              <FormControlLabel
                control={
                  <Switch
                    checked={syncStatus.enabled}
                    onChange={(e) => handleToggleSync(e.target.checked)}
                  />
                }
                label="Enable Background Sync"
              />
              <Chip
                label={syncStatus.enabled ? 'Active' : 'Disabled'}
                color={syncStatus.enabled ? 'success' : 'default'}
                size="small"
              />
            </Box>
            {!syncStatus.sheets_configured && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                Set the <strong>Spreadsheet ID</strong> in the Google Sheets settings above to enable sync.
              </Alert>
            )}
            {!syncStatus.google_connected && syncStatus.sheets_configured && (
              <Alert severity="warning" sx={{ mb: 1 }}>
                Connect your Google account above before syncing.
              </Alert>
            )}
            {syncStatus.last_sync_time && (
              <Typography variant="body2" color="text.secondary">
                Last sync: {new Date(syncStatus.last_sync_time).toLocaleString()}
                {' — '}
                {syncStatus.last_sync_jobs_pulled} pulled, {syncStatus.last_sync_jobs_pushed} pushed
              </Typography>
            )}
            {syncStatus.last_sync_error && (
              <Alert severity="error" sx={{ mb: 1 }}>{syncStatus.last_sync_error}</Alert>
            )}
            <Box>
              <Button
                variant="outlined"
                startIcon={syncing ? <CircularProgress size={18} /> : <Sync />}
                onClick={handleSyncNow}
                disabled={syncing || !syncStatus.sheets_configured || !syncStatus.google_connected}
              >
                {syncing ? 'Syncing…' : 'Sync Now'}
              </Button>
            </Box>
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            <SyncDisabled fontSize="small" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
            Sync status unavailable
          </Typography>
        )}
      </Paper>

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
