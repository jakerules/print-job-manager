import { useEffect, useState } from 'react'
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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  IconButton,
  Switch,
  FormControlLabel,
  Alert,
  Snackbar,
  Tooltip,
  Tabs,
  Tab,
} from '@mui/material'
import { Add, Edit, Delete, PersonAdd, Settings, History, MonitorHeart } from '@mui/icons-material'
import { authService } from '../../services/auth'
import api from '../../services/api'
import AuditLogViewer from './AuditLogViewer'
import SystemHealth from './SystemHealth'
import SettingsPanel from './SettingsPanel'

interface User {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
  last_login: string | null
}

interface UserForm {
  username: string
  email: string
  password: string
  role: string
  is_active: boolean
}

const emptyForm: UserForm = { username: '', email: '', password: '', role: 'staff', is_active: true }

export default function AdminPanel() {
  const [tab, setTab] = useState(0)
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [form, setForm] = useState<UserForm>(emptyForm)
  const [deleteConfirm, setDeleteConfirm] = useState<User | null>(null)
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' })

  const loadUsers = async () => {
    setLoading(true)
    try {
      const res = await api.get('/api/users')
      setUsers(res.data.users || res.data || [])
    } catch {
      setSnackbar({ open: true, message: 'Failed to load users', severity: 'error' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadUsers() }, [])

  const handleOpenCreate = () => {
    setEditingUser(null)
    setForm(emptyForm)
    setDialogOpen(true)
  }

  const handleOpenEdit = (user: User) => {
    setEditingUser(user)
    setForm({ username: user.username, email: user.email, password: '', role: user.role, is_active: user.is_active })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    try {
      if (editingUser) {
        const data: any = { username: form.username, email: form.email, role: form.role, is_active: form.is_active }
        if (form.password) data.password = form.password
        await api.put(`/api/users/${editingUser.id}`, data)
        setSnackbar({ open: true, message: 'User updated', severity: 'success' })
      } else {
        await api.post('/api/users', form)
        setSnackbar({ open: true, message: 'User created', severity: 'success' })
      }
      setDialogOpen(false)
      loadUsers()
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.error || 'Operation failed', severity: 'error' })
    }
  }

  const handleDelete = async () => {
    if (!deleteConfirm) return
    try {
      await api.delete(`/api/users/${deleteConfirm.id}`)
      setSnackbar({ open: true, message: 'User deleted', severity: 'success' })
      setDeleteConfirm(null)
      loadUsers()
    } catch (err: any) {
      setSnackbar({ open: true, message: err.response?.data?.error || 'Delete failed', severity: 'error' })
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'error'
      case 'manager': return 'warning'
      case 'staff': return 'primary'
      case 'submitter': return 'default'
      default: return 'default'
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Admin Panel</Typography>

      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab icon={<PersonAdd />} label="Users" iconPosition="start" />
        <Tab icon={<History />} label="Activity" iconPosition="start" />
        <Tab icon={<MonitorHeart />} label="Health" iconPosition="start" />
        <Tab icon={<Settings />} label="Settings" iconPosition="start" />
      </Tabs>

      {/* Users Tab */}
      {tab === 0 && (
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">{users.length} Users</Typography>
            <Button variant="contained" startIcon={<Add />} onClick={handleOpenCreate}>Add User</Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Login</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id} hover>
                    <TableCell><Typography fontWeight="bold">{user.username}</Typography></TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell><Chip label={user.role} size="small" color={getRoleColor(user.role) as any} /></TableCell>
                    <TableCell>
                      <Chip label={user.is_active ? 'Active' : 'Disabled'} size="small"
                            color={user.is_active ? 'success' : 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>{user.last_login || 'Never'}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Edit">
                        <IconButton size="small" onClick={() => handleOpenEdit(user)}><Edit fontSize="small" /></IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton size="small" color="error" onClick={() => setDeleteConfirm(user)}><Delete fontSize="small" /></IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {/* Activity Log Tab */}
      {tab === 1 && <AuditLogViewer />}

      {/* System Health Tab */}
      {tab === 2 && <SystemHealth />}

      {/* Settings Tab */}
      {tab === 3 && <SettingsPanel />}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingUser ? 'Edit User' : 'Create User'}</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <TextField label="Username" required value={form.username}
                       onChange={(e) => setForm({ ...form, username: e.target.value })} />
            <TextField label="Email" type="email" required value={form.email}
                       onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <TextField label={editingUser ? 'New Password (leave blank to keep)' : 'Password'}
                       type="password" required={!editingUser} value={form.password}
                       onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <FormControl>
              <InputLabel>Role</InputLabel>
              <Select value={form.role} label="Role" onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <MenuItem value="admin">Admin</MenuItem>
                <MenuItem value="manager">Manager</MenuItem>
                <MenuItem value="staff">Staff</MenuItem>
                <MenuItem value="submitter">Submitter</MenuItem>
              </Select>
            </FormControl>
            <FormControlLabel
              control={<Switch checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />}
              label="Active"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave}
                  disabled={!form.username || !form.email || (!editingUser && !form.password)}>
            {editingUser ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete <strong>{deleteConfirm?.username}</strong>?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={3000} onClose={() => setSnackbar((p) => ({ ...p, open: false }))}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity={snackbar.severity} variant="filled">{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  )
}
