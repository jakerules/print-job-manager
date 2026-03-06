import { useEffect, useState, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Button,
  TablePagination,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
  Divider,
} from '@mui/material'
import {
  Refresh,
  Download,
  CheckCircle,
  Close,
  Visibility,
  Edit,
  PictureAsPdf,
  OpenInNew,
} from '@mui/icons-material'
import { RootState } from '../../store/store'
import { setJobs, setLoading, updateJob } from '../../store/jobsSlice'
import { jobService } from '../../services/jobs'
import { wsService } from '../../services/websocket'
import { Job } from '../../types'

function getDriveFileId(url: string): string | null {
  if (!url) return null
  // Match /d/FILE_ID/ or id=FILE_ID patterns
  const match = url.match(/\/d\/([a-zA-Z0-9_-]+)/) || url.match(/[?&]id=([a-zA-Z0-9_-]+)/)
  return match ? match[1] : null
}

export default function QueueManager() {
  const dispatch = useDispatch()
  const { jobs, total, loading } = useSelector((state: RootState) => state.jobs)
  const { user } = useSelector((state: RootState) => state.auth)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(50)
  const [selected, setSelected] = useState<string[]>([])
  const [detailJob, setDetailJob] = useState<Job | null>(null)
  const [editNotes, setEditNotes] = useState('')
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

  const isStaff = user && ['admin', 'manager', 'staff'].includes(user.role)

  const loadJobs = useCallback(async () => {
    dispatch(setLoading(true))
    try {
      const data = await jobService.getJobs({
        search: search || undefined,
        status: statusFilter || undefined,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      })
      dispatch(setJobs({
        jobs: (data as any).jobs || [],
        total: (data as any).total || 0,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      }))
    } catch (error) {
      console.error('Failed to load jobs:', error)
    }
  }, [dispatch, search, statusFilter, page, rowsPerPage])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  useEffect(() => {
    const handleJobUpdate = (data: any) => {
      if (data.job) dispatch(updateJob(data.job))
    }
    const handleNewJob = () => loadJobs()

    wsService.on('job:updated', handleJobUpdate)
    wsService.on('job:new', handleNewJob)
    return () => {
      wsService.off('job:updated', handleJobUpdate)
      wsService.off('job:new', handleNewJob)
    }
  }, [dispatch, loadJobs])

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelected(e.target.checked ? jobs.map((j) => j.job_id) : [])
  }

  const handleSelectOne = (jobId: string) => {
    setSelected((prev) =>
      prev.includes(jobId) ? prev.filter((id) => id !== jobId) : [...prev, jobId]
    )
  }

  const handleBulkComplete = async () => {
    try {
      for (const jobId of selected) {
        await jobService.updateJobStatus(jobId, true, true)
      }
      setSnackbar({ open: true, message: `${selected.length} jobs marked complete`, severity: 'success' })
      setSelected([])
      loadJobs()
    } catch {
      setSnackbar({ open: true, message: 'Failed to update jobs', severity: 'error' })
    }
  }

  const handleExportCSV = () => {
    const headers = ['Job ID', 'Email', 'Room', 'Quantity', 'Paper Size', 'Submitted', 'Status', 'Notes']
    const csvRows = [headers.join(',')]
    jobs.forEach((job) => {
      const status = job.status.completed ? 'Completed' : job.status.acknowledged ? 'In Progress' : 'Pending'
      csvRows.push([
        job.job_id, job.email, job.room, job.quantity, job.paper_size,
        job.date_submitted, status, `"${(job.staff_notes || '').replace(/"/g, '""')}"`
      ].join(','))
    })
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `print-jobs-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleStatusUpdate = async (jobId: string, acknowledged: boolean, completed: boolean) => {
    try {
      await jobService.updateJobStatus(jobId, acknowledged, completed)
      setSnackbar({ open: true, message: `Job ${jobId} updated`, severity: 'success' })
      loadJobs()
      if (detailJob?.job_id === jobId) {
        const updated = await jobService.getJob(jobId)
        setDetailJob(updated)
      }
    } catch {
      setSnackbar({ open: true, message: 'Failed to update status', severity: 'error' })
    }
  }

  const handleSaveNotes = async () => {
    if (!detailJob) return
    try {
      await jobService.updateJobNotes(detailJob.job_id, editNotes)
      setSnackbar({ open: true, message: 'Notes saved', severity: 'success' })
    } catch {
      setSnackbar({ open: true, message: 'Failed to save notes', severity: 'error' })
    }
  }

  const getStatusChip = (status: Job['status']) => {
    if (status.completed) return <Chip label="Completed" color="success" size="small" />
    if (status.acknowledged) return <Chip label="In Progress" color="primary" size="small" />
    return <Chip label="Pending" color="warning" size="small" />
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
        <Typography variant="h4">Job History</Typography>
        <Typography variant="body2" color="text.secondary">{total} total jobs</Typography>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
          <TextField
            label="Search"
            variant="outlined"
            size="small"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0) }}
            placeholder="Job ID, email, or room"
            sx={{ minWidth: 250 }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select value={statusFilter} label="Status" onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}>
              <MenuItem value="">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="acknowledged">In Progress</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
            </Select>
          </FormControl>
          <Box sx={{ flexGrow: 1 }} />
          {isStaff && selected.length > 0 && (
            <Button variant="contained" color="success" startIcon={<CheckCircle />} onClick={handleBulkComplete}>
              Complete ({selected.length})
            </Button>
          )}
          <Tooltip title="Export CSV">
            <IconButton onClick={handleExportCSV}><Download /></IconButton>
          </Tooltip>
          <Tooltip title="Refresh">
            <IconButton onClick={loadJobs}><Refresh /></IconButton>
          </Tooltip>
        </Box>
      </Paper>

      {/* Table */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {isStaff && (
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selected.length > 0 && selected.length < jobs.length}
                    checked={jobs.length > 0 && selected.length === jobs.length}
                    onChange={handleSelectAll}
                  />
                </TableCell>
              )}
              <TableCell>Job ID</TableCell>
              <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Email</TableCell>
              <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>Room</TableCell>
              <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>Qty</TableCell>
              <TableCell sx={{ display: { xs: 'none', lg: 'table-cell' } }}>Paper</TableCell>
              <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>Submitted</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">
                    {loading ? 'Loading...' : 'No jobs found'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              jobs.map((job) => (
                <TableRow key={job.job_id} hover selected={selected.includes(job.job_id)}>
                  {isStaff && (
                    <TableCell padding="checkbox">
                      <Checkbox checked={selected.includes(job.job_id)} onChange={() => handleSelectOne(job.job_id)} />
                    </TableCell>
                  )}
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace" fontWeight="bold">{job.job_id}</Typography>
                  </TableCell>
                  <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>{job.email}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>{job.room}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>{job.quantity}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', lg: 'table-cell' } }}>{job.paper_size}</TableCell>
                  <TableCell sx={{ display: { xs: 'none', sm: 'table-cell' } }}>{job.date_submitted}</TableCell>
                  <TableCell>{getStatusChip(job.status)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="View Details">
                      <IconButton size="small" onClick={() => { setDetailJob(job); setEditNotes(job.staff_notes || '') }}>
                        <Visibility fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_e, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0) }}
        />
      </TableContainer>

      {/* Job Detail Modal */}
      <Dialog open={!!detailJob} onClose={() => setDetailJob(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6">Job: {detailJob?.job_id}</Typography>
            <IconButton onClick={() => setDetailJob(null)}><Close /></IconButton>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          {detailJob && (
            <Box>
              <Box display="flex" flexDirection="column" gap={1.5}>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Status</Typography>
                  {getStatusChip(detailJob.status)}
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Email</Typography>
                  <Typography variant="body2">{detailJob.email}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Room</Typography>
                  <Typography variant="body2">{detailJob.room}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Quantity</Typography>
                  <Typography variant="body2">{detailJob.quantity}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Paper Size</Typography>
                  <Typography variant="body2">{detailJob.paper_size}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Two-Sided</Typography>
                  <Typography variant="body2">{detailJob.two_sided}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Stapled</Typography>
                  <Typography variant="body2">{detailJob.stapled || 'No'}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Hole Punch</Typography>
                  <Typography variant="body2">{detailJob.hole_punch || 'No'}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Submitted</Typography>
                  <Typography variant="body2">{detailJob.date_submitted}</Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">Deadline</Typography>
                  <Typography variant="body2">{detailJob.job_deadline || 'None'}</Typography>
                </Box>
              </Box>

              {/* PDF Preview from Drive Link */}
              {detailJob.file_url && getDriveFileId(detailJob.file_url) && (
                <Box mt={2}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="subtitle2" display="flex" alignItems="center" gap={0.5}>
                      <PictureAsPdf fontSize="small" /> File Preview
                    </Typography>
                    <Button
                      size="small"
                      startIcon={<OpenInNew />}
                      href={detailJob.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open in Drive
                    </Button>
                  </Box>
                  <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
                    <iframe
                      src={`https://drive.google.com/file/d/${getDriveFileId(detailJob.file_url)}/preview`}
                      width="100%"
                      height="400"
                      style={{ border: 'none' }}
                      allow="autoplay"
                      title="File Preview"
                    />
                  </Paper>
                </Box>
              )}

              {/* Drive link without preview */}
              {detailJob.file_url && !getDriveFileId(detailJob.file_url) && (
                <Box mt={2}>
                  <Button
                    size="small"
                    startIcon={<OpenInNew />}
                    href={detailJob.file_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Open File
                  </Button>
                </Box>
              )}

              {detailJob.user_notes && (
                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>User Notes</Typography>
                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography variant="body2">{detailJob.user_notes}</Typography>
                  </Paper>
                </Box>
              )}

              {isStaff && (
                <Box mt={2}>
                  <Typography variant="subtitle2" gutterBottom>Staff Notes</Typography>
                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    size="small"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                  />
                  <Button size="small" startIcon={<Edit />} onClick={handleSaveNotes} sx={{ mt: 1 }}>
                    Save Notes
                  </Button>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        {isStaff && detailJob && (
          <DialogActions>
            {!detailJob.status.acknowledged && (
              <Button variant="contained" onClick={() => handleStatusUpdate(detailJob.job_id, true, false)}>
                Mark Acknowledged
              </Button>
            )}
            {!detailJob.status.completed && (
              <Button variant="contained" color="success" onClick={() => handleStatusUpdate(detailJob.job_id, true, true)}>
                Mark Completed
              </Button>
            )}
          </DialogActions>
        )}
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  )
}
