import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  Chip,
  Divider,
  CircularProgress,
  TextField,
} from '@mui/material'
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
} from '@mui/lab'
import {
  CheckCircle,
  Print,
  FiberNew,
} from '@mui/icons-material'
import api from '../../services/api'

interface Job {
  job_id: string
  date_submitted: string
  email: string
  room: string
  status: {
    acknowledged: boolean
    completed: boolean
  }
}

const statusIcon = (job: Job) => {
  if (job.status.completed) return <CheckCircle />
  if (job.status.acknowledged) return <Print />
  return <FiberNew />
}

const statusColor = (job: Job): 'success' | 'primary' | 'warning' => {
  if (job.status.completed) return 'success'
  if (job.status.acknowledged) return 'primary'
  return 'warning'
}

export default function JobTimeline() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    api.get('/jobs', { params: { limit: 50 } })
      .then((res) => setJobs(res.data.jobs || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const filtered = jobs.filter((j) =>
    !filter ||
    j.job_id?.toLowerCase().includes(filter.toLowerCase()) ||
    j.email?.toLowerCase().includes(filter.toLowerCase())
  )

  if (loading) return <Box textAlign="center" py={4}><CircularProgress /></Box>

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">Job Timeline</Typography>
        <TextField
          size="small"
          placeholder="Filter by ID or email..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          sx={{ width: 250 }}
        />
      </Box>

      {filtered.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">No jobs to display</Typography>
        </Paper>
      ) : (
        <Timeline position="alternate">
          {filtered.map((job, i) => (
            <TimelineItem key={job.job_id || i}>
              <TimelineOppositeContent color="text.secondary" sx={{ flex: 0.3 }}>
                <Typography variant="caption">
                  {job.date_submitted
                    ? (() => {
                        const d = new Date(job.date_submitted)
                        return isNaN(d.getTime()) ? job.date_submitted : d.toLocaleString()
                      })()
                    : ''}
                </Typography>
              </TimelineOppositeContent>
              <TimelineSeparator>
                <TimelineDot color={statusColor(job)}>
                  {statusIcon(job)}
                </TimelineDot>
                {i < filtered.length - 1 && <TimelineConnector />}
              </TimelineSeparator>
              <TimelineContent>
                <Paper elevation={2} sx={{ p: 2 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="subtitle2" fontFamily="monospace">
                      {job.job_id || 'No ID'}
                    </Typography>
                    <Chip
                      label={job.status.completed ? 'Completed' : job.status.acknowledged ? 'In Progress' : 'Pending'}
                      size="small"
                      color={statusColor(job)}
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {job.email}
                  </Typography>
                  {job.room && (
                    <Typography variant="caption" color="text.secondary">
                      Room {job.room}
                    </Typography>
                  )}
                </Paper>
              </TimelineContent>
            </TimelineItem>
          ))}
        </Timeline>
      )}
    </Box>
  )
}
