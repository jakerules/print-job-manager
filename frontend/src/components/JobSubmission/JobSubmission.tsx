import { useState } from 'react'
import { useSelector } from 'react-redux'
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Switch,
  Alert,
  Snackbar,
  Divider,
  Card,
  CardContent,
  Chip,
  LinearProgress,
} from '@mui/material'
import { Send, CheckCircle, CloudUpload } from '@mui/icons-material'
import { RootState } from '../../store/store'
import api from '../../services/api'

interface JobForm {
  email: string
  room: string
  quantity: string
  paper_size: string
  two_sided: boolean
  color: boolean
  stapled: boolean
  deadline: string
  notes: string
}

const defaultForm: JobForm = {
  email: '',
  room: '',
  quantity: '1',
  paper_size: 'Letter',
  two_sided: false,
  color: false,
  stapled: false,
  deadline: '',
  notes: '',
}

export default function JobSubmission() {
  const { user } = useSelector((state: RootState) => state.auth)
  const [form, setForm] = useState<JobForm>({ ...defaultForm, email: user?.email || '' })
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ job_id: string } | null>(null)
  const [error, setError] = useState('')
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

  const handleChange = (field: keyof JobForm, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      if (f.size > 50 * 1024 * 1024) {
        setSnackbar({ open: true, message: 'File must be under 50MB', severity: 'error' })
        return
      }
      setFile(f)
    }
  }

  const handleSubmit = async () => {
    setError('')
    if (!form.email || !form.room || !form.quantity) {
      setError('Email, room, and quantity are required')
      return
    }

    setSubmitting(true)
    try {
      // Upload file first if present
      let file_url = ''
      if (file) {
        const formData = new FormData()
        formData.append('file', file)
        const uploadRes = await api.post('/jobs/upload-file', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        file_url = uploadRes.data.file_url || uploadRes.data.url || ''
      }

      const payload = {
        email: form.email,
        room: form.room,
        quantity: parseInt(form.quantity, 10),
        paper_size: form.paper_size,
        two_sided: form.two_sided,
        color: form.color,
        stapled: form.stapled,
        deadline: form.deadline || undefined,
        notes: form.notes || undefined,
        file_url: file_url || undefined,
      }

      const res = await api.post('/jobs/submit', payload)
      setResult(res.data)
      setSnackbar({ open: true, message: `Job submitted! ID: ${res.data.job_id}`, severity: 'success' })
    } catch (err: any) {
      setError(err.response?.data?.error || 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReset = () => {
    setForm({ ...defaultForm, email: user?.email || '' })
    setFile(null)
    setResult(null)
    setError('')
  }

  // Success state
  if (result) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>Submit Print Job</Typography>
        <Card sx={{ maxWidth: 500, mx: 'auto', mt: 4, border: 2, borderColor: 'success.main' }}>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <CheckCircle color="success" sx={{ fontSize: 64, mb: 2 }} />
            <Typography variant="h5" gutterBottom>Job Submitted!</Typography>
            <Typography variant="body1" gutterBottom>Your print job has been submitted successfully.</Typography>
            <Chip label={result.job_id} sx={{ fontSize: '1.2rem', fontFamily: 'monospace', py: 2, px: 1, mt: 2 }} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Save this Job ID to track your print job status.
            </Typography>
            <Box mt={3}>
              <Button variant="contained" onClick={handleReset}>Submit Another Job</Button>
            </Box>
          </CardContent>
        </Card>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Submit Print Job</Typography>

      {submitting && <LinearProgress sx={{ mb: 2 }} />}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <Box display="flex" flexDirection="column" gap={2.5}>
          <TextField
            label="Email"
            type="email"
            required
            value={form.email}
            onChange={(e) => handleChange('email', e.target.value)}
            placeholder="your.email@example.com"
          />

          <TextField
            label="Room Number"
            required
            value={form.room}
            onChange={(e) => handleChange('room', e.target.value)}
            placeholder="e.g. 301"
          />

          <TextField
            label="Number of Copies"
            type="number"
            required
            value={form.quantity}
            onChange={(e) => handleChange('quantity', e.target.value)}
            inputProps={{ min: 1 }}
          />

          <FormControl>
            <InputLabel>Paper Size</InputLabel>
            <Select value={form.paper_size} label="Paper Size" onChange={(e) => handleChange('paper_size', e.target.value)}>
              <MenuItem value="Letter">Letter (8.5 x 11)</MenuItem>
              <MenuItem value="Legal">Legal (8.5 x 14)</MenuItem>
              <MenuItem value="Tabloid">Tabloid (11 x 17)</MenuItem>
              <MenuItem value="A4">A4</MenuItem>
            </Select>
          </FormControl>

          <Box display="flex" gap={3} flexWrap="wrap">
            <FormControlLabel
              control={<Switch checked={form.two_sided} onChange={(e) => handleChange('two_sided', e.target.checked)} />}
              label="Two-Sided"
            />
            <FormControlLabel
              control={<Switch checked={form.color} onChange={(e) => handleChange('color', e.target.checked)} />}
              label="Color"
            />
            <FormControlLabel
              control={<Switch checked={form.stapled} onChange={(e) => handleChange('stapled', e.target.checked)} />}
              label="Stapled"
            />
          </Box>

          <TextField
            label="Deadline"
            type="date"
            value={form.deadline}
            onChange={(e) => handleChange('deadline', e.target.value)}
            InputLabelProps={{ shrink: true }}
          />

          <TextField
            label="Notes"
            multiline
            rows={3}
            value={form.notes}
            onChange={(e) => handleChange('notes', e.target.value)}
            placeholder="Special instructions..."
          />

          <Divider />

          {/* File Upload */}
          <Box>
            <Button variant="outlined" component="label" startIcon={<CloudUpload />} fullWidth>
              {file ? file.name : 'Upload Print File'}
              <input type="file" hidden onChange={handleFileChange}
                     accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg" />
            </Button>
            {file && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                {(file.size / 1024 / 1024).toFixed(1)} MB • <Button size="small" onClick={() => setFile(null)}>Remove</Button>
              </Typography>
            )}
          </Box>

          <Button
            variant="contained"
            size="large"
            startIcon={<Send />}
            onClick={handleSubmit}
            disabled={submitting || !form.email || !form.room || !form.quantity}
          >
            {submitting ? 'Submitting...' : 'Submit Print Job'}
          </Button>
        </Box>
      </Paper>

      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  )
}
