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
  LinearProgress,
  Snackbar,
  Alert,
  Badge,
} from '@mui/material'
import {
  Assignment,
  CheckCircle,
  HourglassEmpty,
  Pending,
  QrCodeScanner,
  ListAlt,
  Refresh,
  Notifications,
  ArrowForward,
  FiberNew,
} from '@mui/icons-material'
import { RootState } from '../../store/store'
import { setStats, addJob } from '../../store/jobsSlice'
import { jobService } from '../../services/jobs'
import { wsService } from '../../services/websocket'
import { Job, JobStats } from '../../types'

interface Notification {
  id: number
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  timestamp: Date
  read: boolean
}

export default function Dashboard() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { stats } = useSelector((state: RootState) => state.jobs)
  const { user } = useSelector((state: RootState) => state.auth)

  const [loading, setLoading] = useState(true)
  const [recentJobs, setRecentJobs] = useState<Job[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
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

  const loadRecentJobs = useCallback(async () => {
    try {
      const data = await jobService.getJobs({ limit: 5 })
      setRecentJobs((data as any).jobs || [])
    } catch (error) {
      console.error('Failed to load recent jobs:', error)
    }
  }, [])

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([loadStats(), loadRecentJobs()])
      setLoading(false)
    }
    init()

    // Real-time listeners
    const handleStatsUpdate = (data: any) => {
      if (data.stats) dispatch(setStats(data.stats))
    }

    const handleNewJob = (data: any) => {
      if (data.job) {
        dispatch(addJob(data.job))
        setRecentJobs((prev) => [data.job, ...prev.slice(0, 4)])
        addNotification(`New job submitted: ${data.job.job_id}`, 'info')
        setSnackbar({ open: true, message: `New job: ${data.job.job_id}`, severity: 'info' })
      }
    }

    const handleJobUpdated = (data: any) => {
      if (data.action === 'completed') {
        addNotification(`Job ${data.job_id} completed`, 'success')
      } else if (data.action === 'acknowledged') {
        addNotification(`Job ${data.job_id} acknowledged`, 'info')
      }
      loadStats()
      loadRecentJobs()
    }

    wsService.on('stats:update', handleStatsUpdate)
    wsService.on('job:new', handleNewJob)
    wsService.on('job:updated', handleJobUpdated)

    // Poll for updates as fallback (every 30s)
    const pollInterval = setInterval(() => {
      loadStats()
      loadRecentJobs()
    }, 30000)

    return () => {
      wsService.off('stats:update', handleStatsUpdate)
      wsService.off('job:new', handleNewJob)
      wsService.off('job:updated', handleJobUpdated)
      clearInterval(pollInterval)
    }
  }, [dispatch, loadStats, loadRecentJobs])

  const addNotification = (message: string, type: Notification['type']) => {
    setNotifications((prev) => [
      { id: Date.now(), message, type, timestamp: new Date(), read: false },
      ...prev.slice(0, 19),
    ])
  }

  const completionRate = stats ? Math.round((stats.completed / Math.max(stats.total, 1)) * 100) : 0

  const getJobStatusChip = (status: Job['status']) => {
    if (status.completed) return <Chip label="Done" color="success" size="small" />
    if (status.acknowledged) return <Chip label="In Progress" color="primary" size="small" />
    return <Chip label="Pending" color="warning" size="small" />
  }

  const isStaff = user && ['admin', 'manager', 'staff'].includes(user.role)
  const isManager = user && ['admin', 'manager'].includes(user.role)
  const unreadCount = notifications.filter((n) => !n.read).length

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
          <IconButton onClick={() => { loadStats(); loadRecentJobs() }} title="Refresh">
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* Stat Cards */}
      <Grid container spacing={2}>
        {[
          { title: 'Total Jobs', value: stats?.total || 0, icon: <Assignment sx={{ fontSize: 40 }} />, color: '#1976d2' },
          { title: 'Pending', value: stats?.pending || 0, icon: <HourglassEmpty sx={{ fontSize: 40 }} />, color: '#ed6c02' },
          { title: 'In Progress', value: stats?.acknowledged || 0, icon: <Pending sx={{ fontSize: 40 }} />, color: '#0288d1' },
          { title: 'Completed', value: stats?.completed || 0, icon: <CheckCircle sx={{ fontSize: 40 }} />, color: '#2e7d32' },
        ].map((card) => (
          <Grid item xs={6} sm={6} md={3} key={card.title}>
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

      {/* Completion Progress */}
      {isManager && (
        <Paper sx={{ mt: 2, p: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle2" color="text.secondary">Completion Rate</Typography>
            <Typography variant="subtitle2" fontWeight="bold">{completionRate}%</Typography>
          </Box>
          <LinearProgress variant="determinate" value={completionRate} sx={{ height: 10, borderRadius: 5 }} />
        </Paper>
      )}

      {/* Main Content Grid */}
      <Grid container spacing={2} sx={{ mt: 1 }}>
        {/* Recent Jobs */}
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="h6">Recent Jobs</Typography>
              <Button size="small" endIcon={<ArrowForward />} onClick={() => navigate('/queue')}>View All</Button>
            </Box>
            <Divider />
            {recentJobs.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
                No recent jobs
              </Typography>
            ) : (
              <List dense disablePadding>
                {recentJobs.map((job, i) => (
                  <div key={job.job_id}>
                    <ListItem sx={{ px: 0 }}>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="body2" fontWeight="bold" fontFamily="monospace">
                              {job.job_id}
                            </Typography>
                            {getJobStatusChip(job.status)}
                          </Box>
                        }
                        secondary={`${job.email || 'N/A'} • Room ${job.room || '?'} • Qty: ${job.quantity || '?'}`}
                      />
                      <ListItemSecondaryAction>
                        <Typography variant="caption" color="text.secondary">
                          {job.date_submitted || ''}
                        </Typography>
                      </ListItemSecondaryAction>
                    </ListItem>
                    {i < recentJobs.length - 1 && <Divider />}
                  </div>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        {/* Notifications */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h6">Notifications</Typography>
                {unreadCount > 0 && (
                  <Badge badgeContent={unreadCount} color="error" />
                )}
              </Box>
              {notifications.length > 0 && (
                <Button size="small" onClick={() => setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))}>
                  Mark all read
                </Button>
              )}
            </Box>
            <Divider />
            {notifications.length === 0 ? (
              <Box textAlign="center" py={3}>
                <Notifications sx={{ fontSize: 40, color: 'text.disabled' }} />
                <Typography variant="body2" color="text.secondary" mt={1}>
                  No notifications yet
                </Typography>
                <Typography variant="caption" color="text.disabled">
                  New events will appear here in real-time
                </Typography>
              </Box>
            ) : (
              <List dense disablePadding sx={{ maxHeight: 300, overflow: 'auto' }}>
                {notifications.map((n) => (
                  <ListItem key={n.id} sx={{ px: 0, opacity: n.read ? 0.6 : 1 }}>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={0.5}>
                          {!n.read && <FiberNew color="error" sx={{ fontSize: 16 }} />}
                          <Typography variant="body2">{n.message}</Typography>
                        </Box>
                      }
                      secondary={n.timestamp.toLocaleTimeString()}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>

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
