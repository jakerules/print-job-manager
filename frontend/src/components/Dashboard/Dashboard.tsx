import { useEffect, useState, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Divider,
  Button,
  CircularProgress,
  Snackbar,
  Alert,
} from '@mui/material'
import {
  CheckCircle,
  HourglassEmpty,
  Pending,
  QrCodeScanner,
  ListAlt,
  Refresh,
  ArrowForward,
  Today,
} from '@mui/icons-material'
import { RootState } from '../../store/store'
import { setStats, addJob } from '../../store/jobsSlice'
import { jobService } from '../../services/jobs'
import { wsService } from '../../services/websocket'
import { Job } from '../../types'

export default function Dashboard() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { stats } = useSelector((state: RootState) => state.jobs)
  const { user } = useSelector((state: RootState) => state.auth)

  const [loading, setLoading] = useState(true)
  const [activeJobs, setActiveJobs] = useState<Job[]>([])
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'info' | 'success' | 'warning' | 'error' }>({
    open: false,
    message: '',
    severity: 'info',
  })

  const loadStats = useCallback(async () => {
    try {
      const data = await jobService.getStats()
      dispatch(setStats(data))
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }, [dispatch])

  const loadActiveJobs = useCallback(async () => {
    try {
      // Load new + in-progress jobs (not completed)
      const pending = await jobService.getJobs({ status: 'pending', limit: 10 })
      const inProgress = await jobService.getJobs({ status: 'acknowledged', limit: 10 })
      const combined = [
        ...((inProgress as any).jobs || []),
        ...((pending as any).jobs || []),
      ].slice(0, 15)
      setActiveJobs(combined)
    } catch (error) {
      console.error('Failed to load active jobs:', error)
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([loadStats(), loadActiveJobs()])
      setLoading(false)
    }
    init()

    const handleStatsUpdate = (data: any) => {
      if (data.stats) dispatch(setStats(data.stats))
    }

    const handleNewJob = (data: any) => {
      if (data.job) {
        dispatch(addJob(data.job))
        setActiveJobs((prev) => [data.job, ...prev.slice(0, 14)])
        setSnackbar({ open: true, message: `New job: ${data.job.job_id}`, severity: 'info' })
      }
    }

    const handleJobUpdated = () => {
      loadStats()
      loadActiveJobs()
    }

    wsService.on('stats:update', handleStatsUpdate)
    wsService.on('job:new', handleNewJob)
    wsService.on('job:updated', handleJobUpdated)

    const pollInterval = setInterval(() => {
      loadStats()
      loadActiveJobs()
    }, 30000)

    return () => {
      wsService.off('stats:update', handleStatsUpdate)
      wsService.off('job:new', handleNewJob)
      wsService.off('job:updated', handleJobUpdated)
      clearInterval(pollInterval)
    }
  }, [dispatch, loadStats, loadActiveJobs])

  const getJobStatusChip = (status: Job['status']) => {
    if (status.completed) return <Chip label="Done" color="success" size="small" />
    if (status.acknowledged) return <Chip label="In Progress" color="primary" size="small" />
    return <Chip label="New" color="warning" size="small" />
  }

  const isStaff = user && ['admin', 'manager', 'staff'].includes(user.role)

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3} flexWrap="wrap" gap={1}>
        <Typography variant="h4">Dashboard</Typography>
        <Box display="flex" gap={1}>
          {isStaff && (
            <Button variant="contained" startIcon={<QrCodeScanner />} onClick={() => navigate('/scanner')}>
              Scan
            </Button>
          )}
          <Button variant="outlined" startIcon={<ListAlt />} onClick={() => navigate('/queue')}>
            Queue
          </Button>
          <IconButton onClick={() => { loadStats(); loadActiveJobs() }} title="Refresh">
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* Stat Cards */}
      <Grid container spacing={2}>
        {[
          { title: 'New', value: stats?.pending || 0, icon: <HourglassEmpty sx={{ fontSize: 40 }} />, color: '#ed6c02' },
          { title: 'In Progress', value: stats?.acknowledged || 0, icon: <Pending sx={{ fontSize: 40 }} />, color: '#0288d1' },
          { title: 'Completed Today', value: stats?.completed_today || 0, icon: <Today sx={{ fontSize: 40 }} />, color: '#2e7d32' },
        ].map((card) => (
          <Grid item xs={4} sm={4} md={4} key={card.title}>
            <Card sx={{ bgcolor: card.color, color: 'white', cursor: 'pointer', '&:hover': { opacity: 0.9 } }}
                  onClick={() => navigate('/queue')}>
              <CardContent sx={{ p: { xs: 1.5, sm: 2 } }}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="h3" component="div" sx={{ fontSize: { xs: '1.8rem', sm: '2.5rem', md: '3rem' } }}>
                      {card.value}
                    </Typography>
                    <Typography variant="body2" sx={{ opacity: 0.9 }}>
                      {card.title}
                    </Typography>
                  </Box>
                  <Box sx={{ opacity: 0.7, display: { xs: 'none', sm: 'block' } }}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Active Jobs (New + In Progress) */}
      <Paper sx={{ mt: 3, p: 2 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Typography variant="h6">Active Jobs</Typography>
          <Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/queue')}>View All</Button>
        </Box>
        <Divider />
        {activeJobs.length === 0 ? (
          <Box textAlign="center" py={4}>
            <CheckCircle sx={{ fontSize: 48, color: 'text.disabled' }} />
            <Typography variant="body1" color="text.secondary" mt={1}>
              All caught up — no pending jobs!
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {activeJobs.map((job, i) => (
              <div key={job.job_id}>
                <ListItem
                  sx={{ px: 0, cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                  onClick={() => navigate('/queue')}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" fontWeight="bold" fontFamily="monospace">
                          {job.job_id}
                        </Typography>
                        {getJobStatusChip(job.status)}
                      </Box>
                    }
                    secondary={
                      <Typography variant="body2" color="text.secondary" component="span">
                        {job.email || 'N/A'} • Room {job.room || '?'} • Qty: {job.quantity || '?'} • {job.paper_size || '?'}
                        {job.two_sided === 'Yes' ? ' • Duplex' : ''}
                      </Typography>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Typography variant="caption" color="text.secondary">
                      {job.date_submitted || ''}
                    </Typography>
                  </ListItemSecondaryAction>
                </ListItem>
                {i < activeJobs.length - 1 && <Divider />}
              </div>
            ))}
          </List>
        )}
      </Paper>

      {/* Toast Notification */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={snackbar.severity} variant="filled" onClose={() => setSnackbar((prev) => ({ ...prev, open: false }))}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  )
}
