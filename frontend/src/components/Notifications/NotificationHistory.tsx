import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Button,
  Divider,
  IconButton,
  Badge,
} from '@mui/material'
import {
  Notifications as NotifIcon,
  FiberNew,
  CheckCircle,
  Info,
  Warning,
  DeleteSweep,
  DoneAll,
} from '@mui/icons-material'
import { wsService } from '../../services/websocket'

export interface Notification {
  id: string
  type: 'new_job' | 'status_change' | 'info' | 'warning'
  title: string
  message: string
  timestamp: Date
  read: boolean
  jobId?: string
}

let notifCounter = 0

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])

  useEffect(() => {
    const handleNewJob = (data: any) => {
      const notif: Notification = {
        id: `n-${++notifCounter}`,
        type: 'new_job',
        title: 'New Print Job',
        message: `Job ${data.job?.job_id || 'unknown'} from ${data.job?.email || 'unknown'}`,
        timestamp: new Date(),
        read: false,
        jobId: data.job?.job_id,
      }
      setNotifications((prev) => [notif, ...prev.slice(0, 99)])
    }

    const handleJobUpdated = (data: any) => {
      const job = data.job
      if (!job) return
      const status = job.status?.completed ? 'completed' : job.status?.acknowledged ? 'acknowledged' : 'updated'
      const notif: Notification = {
        id: `n-${++notifCounter}`,
        type: 'status_change',
        title: `Job ${status}`,
        message: `Job ${job.job_id} is now ${status}`,
        timestamp: new Date(),
        read: false,
        jobId: job.job_id,
      }
      setNotifications((prev) => [notif, ...prev.slice(0, 99)])
    }

    const handleNotification = (data: any) => {
      const notif: Notification = {
        id: `n-${++notifCounter}`,
        type: data.type || 'info',
        title: data.title || 'Notification',
        message: data.message || '',
        timestamp: new Date(),
        read: false,
      }
      setNotifications((prev) => [notif, ...prev.slice(0, 99)])
    }

    wsService.on('job:new', handleNewJob)
    wsService.on('job:updated', handleJobUpdated)
    wsService.on('notification', handleNotification)

    return () => {
      wsService.off('job:new', handleNewJob)
      wsService.off('job:updated', handleJobUpdated)
      wsService.off('notification', handleNotification)
    }
  }, [])

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  const clearAll = () => setNotifications([])

  const unreadCount = notifications.filter((n) => !n.read).length

  return { notifications, unreadCount, markAllRead, clearAll }
}

interface NotificationHistoryProps {
  notifications: Notification[]
  unreadCount: number
  onMarkAllRead: () => void
  onClear: () => void
}

export default function NotificationHistory({ notifications, unreadCount, onMarkAllRead, onClear }: NotificationHistoryProps) {
  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'new_job': return <FiberNew color="primary" />
      case 'status_change': return <CheckCircle color="success" />
      case 'warning': return <Warning color="warning" />
      default: return <Info color="info" />
    }
  }

  const getTimeAgo = (date: Date) => {
    const secs = Math.floor((Date.now() - date.getTime()) / 1000)
    if (secs < 60) return 'just now'
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
    return date.toLocaleDateString()
  }

  return (
    <Paper sx={{ p: 2, maxHeight: 500, overflow: 'auto' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
        <Box display="flex" alignItems="center" gap={1}>
          <Badge badgeContent={unreadCount} color="error">
            <NotifIcon />
          </Badge>
          <Typography variant="h6">Notifications</Typography>
        </Box>
        <Box>
          {unreadCount > 0 && (
            <Button size="small" startIcon={<DoneAll />} onClick={onMarkAllRead}>
              Mark Read
            </Button>
          )}
          {notifications.length > 0 && (
            <IconButton size="small" onClick={onClear} title="Clear all">
              <DeleteSweep />
            </IconButton>
          )}
        </Box>
      </Box>
      <Divider />

      {notifications.length === 0 ? (
        <Box py={4} textAlign="center">
          <Typography variant="body2" color="text.secondary">No notifications yet</Typography>
        </Box>
      ) : (
        <List dense>
          {notifications.map((notif) => (
            <ListItem key={notif.id} sx={{ opacity: notif.read ? 0.6 : 1, bgcolor: notif.read ? 'transparent' : 'action.hover', borderRadius: 1, mb: 0.5 }}>
              <ListItemIcon sx={{ minWidth: 36 }}>
                {getIcon(notif.type)}
              </ListItemIcon>
              <ListItemText
                primary={
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" fontWeight={notif.read ? 'normal' : 'bold'}>{notif.title}</Typography>
                    <Typography variant="caption" color="text.secondary">{getTimeAgo(notif.timestamp)}</Typography>
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="caption">{notif.message}</Typography>
                    {notif.jobId && <Chip label={notif.jobId} size="small" variant="outlined" sx={{ ml: 1, height: 18, fontSize: '0.65rem' }} />}
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  )
}
