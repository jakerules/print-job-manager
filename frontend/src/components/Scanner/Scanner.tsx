import { useState, useRef, useEffect } from 'react'
import { useSelector } from 'react-redux'
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Card,
  CardContent,
  Alert,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Switch,
  FormControlLabel,
  Snackbar,
} from '@mui/material'
import {
  QrCodeScanner,
  Videocam,
  VideocamOff,
  Delete,
  CheckCircle,
  HourglassEmpty,
  Pending as PendingIcon,
} from '@mui/icons-material'
import { RootState } from '../../store/store'
import { jobService } from '../../services/jobs'
import { Job } from '../../types'
import CameraScanner from './CameraScanner'

interface ScanRecord {
  jobId: string
  job: Job
  action: string
  timestamp: Date
}

export default function Scanner() {
  const { user } = useSelector((state: RootState) => state.auth)
  const [jobId, setJobId] = useState('')
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [continuousMode, setContinuousMode] = useState(false)
  const [autoUpdate, setAutoUpdate] = useState(true)
  const [cameraActive, setCameraActive] = useState(false)
  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([])
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'info' })
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-focus the input
  useEffect(() => {
    inputRef.current?.focus()
  }, [job])

  const playBeep = (success: boolean) => {
    try {
      const ctx = new AudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = success ? 800 : 300
      gain.gain.value = 0.1
      osc.start()
      osc.stop(ctx.currentTime + (success ? 0.15 : 0.3))
    } catch {
      // Audio not available
    }
  }

  const handleScan = async () => {
    const trimmedId = jobId.trim().toUpperCase()
    if (!trimmedId) return

    setError('')
    setLoading(true)

    try {
      const jobData = await jobService.getJob(trimmedId)
      let action = 'viewed'

      if (autoUpdate) {
        if (!jobData.status.acknowledged) {
          await jobService.updateJobStatus(trimmedId, true, undefined)
          jobData.status.acknowledged = true
          action = 'acknowledged'
        } else if (!jobData.status.completed) {
          await jobService.updateJobStatus(trimmedId, undefined, true)
          jobData.status.completed = true
          action = 'completed'
        } else {
          action = 'already_completed'
        }
      }

      setJob(jobData)
      playBeep(true)

      // Add to history
      setScanHistory((prev) => [
        { jobId: trimmedId, job: jobData, action, timestamp: new Date() },
        ...prev.slice(0, 49),
      ])

      setSnackbar({
        open: true,
        message: action === 'acknowledged' ? `Job ${trimmedId} acknowledged` :
                 action === 'completed' ? `Job ${trimmedId} completed!` :
                 action === 'already_completed' ? `Job ${trimmedId} already done` :
                 `Job ${trimmedId} found`,
        severity: action === 'completed' ? 'success' : 'info',
      })

      setJobId('')

      if (continuousMode) {
        setTimeout(() => inputRef.current?.focus(), 100)
      }
    } catch (err: any) {
      playBeep(false)
      setError(err.response?.data?.error || 'Job not found')
      setJob(null)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleScan()
    if (e.key === 'Escape') { setJobId(''); setJob(null); setError('') }
  }

  const handleManualStatus = async (acknowledged: boolean, completed: boolean) => {
    if (!job) return
    try {
      await jobService.updateJobStatus(job.job_id, acknowledged, completed)
      const updated = await jobService.getJob(job.job_id)
      setJob(updated)
      setSnackbar({ open: true, message: `Job ${job.job_id} updated`, severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Failed to update', severity: 'error' })
    }
  }

  const getStatusIcon = (status: Job['status']) => {
    if (status.completed) return <CheckCircle color="success" />
    if (status.acknowledged) return <PendingIcon color="primary" />
    return <HourglassEmpty color="warning" />
  }

  const getStatusLabel = (status: Job['status']) => {
    if (status.completed) return 'Completed'
    if (status.acknowledged) return 'In Progress'
    return 'Pending'
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Barcode Scanner</Typography>

      {/* Scanner Input */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
          <QrCodeScanner fontSize="large" color="primary" />
          <TextField
            inputRef={inputRef}
            fullWidth
            label="Job ID"
            variant="outlined"
            value={jobId}
            onChange={(e) => setJobId(e.target.value.toUpperCase())}
            onKeyDown={handleKeyDown}
            placeholder="Scan barcode or type Job ID"
            autoFocus
            disabled={loading}
            sx={{ flexGrow: 1 }}
            inputProps={{ style: { fontFamily: 'monospace', fontSize: '1.2rem', letterSpacing: '0.1em' } }}
          />
          <Button variant="contained" size="large" onClick={handleScan} disabled={!jobId.trim() || loading}>
            {loading ? 'Scanning...' : 'Scan'}
          </Button>
        </Box>
        <Box display="flex" gap={3} mt={2}>
          <FormControlLabel
            control={<Switch checked={continuousMode} onChange={(e) => setContinuousMode(e.target.checked)} size="small" />}
            label={<Typography variant="body2">Continuous Mode</Typography>}
          />
          <FormControlLabel
            control={<Switch checked={autoUpdate} onChange={(e) => setAutoUpdate(e.target.checked)} size="small" />}
            label={<Typography variant="body2">Auto-Update Status</Typography>}
          />
          <Button
            variant={cameraActive ? 'contained' : 'outlined'}
            size="small"
            startIcon={cameraActive ? <VideocamOff /> : <Videocam />}
            onClick={() => setCameraActive(!cameraActive)}
            color={cameraActive ? 'error' : 'primary'}
          >
            {cameraActive ? 'Stop Camera' : 'Use Camera'}
          </Button>
        </Box>
      </Paper>

      {/* Camera Scanner */}
      {cameraActive && (
        <Box mb={3}>
          <CameraScanner active={cameraActive} onScan={(code) => { setJobId(code); handleScan() }} />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Job Details */}
      {job && (
        <Card sx={{ mb: 3, border: 2, borderColor: job.status.completed ? 'success.main' : job.status.acknowledged ? 'primary.main' : 'warning.main' }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h5" fontFamily="monospace">{job.job_id}</Typography>
              <Chip
                icon={getStatusIcon(job.status)}
                label={getStatusLabel(job.status)}
                color={job.status.completed ? 'success' : job.status.acknowledged ? 'primary' : 'warning'}
              />
            </Box>
            <Divider sx={{ mb: 2 }} />
            <Box display="grid" gridTemplateColumns={{ xs: '1fr', sm: '1fr 1fr' }} gap={1.5}>
              <Typography variant="body2"><strong>Email:</strong> {job.email}</Typography>
              <Typography variant="body2"><strong>Room:</strong> {job.room}</Typography>
              <Typography variant="body2"><strong>Quantity:</strong> {job.quantity}</Typography>
              <Typography variant="body2"><strong>Paper:</strong> {job.paper_size}</Typography>
              <Typography variant="body2"><strong>Two-Sided:</strong> {job.two_sided}</Typography>
              <Typography variant="body2"><strong>Submitted:</strong> {job.date_submitted}</Typography>
              {job.job_deadline && <Typography variant="body2"><strong>Deadline:</strong> {job.job_deadline}</Typography>}
              {job.staff_notes && <Typography variant="body2"><strong>Notes:</strong> {job.staff_notes}</Typography>}
            </Box>

            {/* Manual status buttons */}
            <Box display="flex" gap={1} mt={2} flexWrap="wrap">
              {!job.status.acknowledged && (
                <Button variant="contained" onClick={() => handleManualStatus(true, false)}>Acknowledge</Button>
              )}
              {!job.status.completed && (
                <Button variant="contained" color="success" onClick={() => handleManualStatus(true, true)}>Complete</Button>
              )}
              {job.status.completed && (
                <Alert severity="success" sx={{ flexGrow: 1 }}>This job is already completed ✓</Alert>
              )}
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Scan History */}
      {scanHistory.length > 0 && (
        <Paper sx={{ p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="h6">Scan History ({scanHistory.length})</Typography>
            <Button size="small" startIcon={<Delete />} onClick={() => setScanHistory([])}>Clear</Button>
          </Box>
          <Divider />
          <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
            {scanHistory.map((record, i) => (
              <ListItem key={`${record.jobId}-${i}`}>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      {getStatusIcon(record.job.status)}
                      <Typography variant="body2" fontFamily="monospace" fontWeight="bold">{record.jobId}</Typography>
                      <Chip label={record.action} size="small" variant="outlined" />
                    </Box>
                  }
                  secondary={`${record.job.email || ''} • ${record.timestamp.toLocaleTimeString()}`}
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  )
}
