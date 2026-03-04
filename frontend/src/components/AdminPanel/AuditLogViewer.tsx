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
  TablePagination,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import api from '../../services/api'

interface AuditEntry {
  id: number
  user_id: number
  username: string
  action: string
  resource_type: string | null
  resource_id: string | null
  details: string | null
  ip_address: string | null
  timestamp: string
}

export default function AuditLogViewer() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(25)
  const [actionFilter, setActionFilter] = useState('')

  useEffect(() => {
    loadEntries()
  }, [page, rowsPerPage, actionFilter])

  const loadEntries = async () => {
    try {
      const params: any = { limit: rowsPerPage, offset: page * rowsPerPage }
      if (actionFilter) params.action = actionFilter
      const res = await api.get('/api/audit/log', { params })
      setEntries(res.data.entries || [])
      setTotal(res.data.total || 0)
    } catch {
      // Not authorized or error
    }
  }

  const getActionColor = (action: string) => {
    if (action.includes('login')) return 'primary'
    if (action.includes('create')) return 'success'
    if (action.includes('delete')) return 'error'
    if (action.includes('update')) return 'warning'
    return 'default'
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>Activity Log</Typography>

      <Box display="flex" gap={2} mb={2}>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Action</InputLabel>
          <Select value={actionFilter} label="Action" onChange={(e) => { setActionFilter(e.target.value); setPage(0) }}>
            <MenuItem value="">All</MenuItem>
            <MenuItem value="login">Login</MenuItem>
            <MenuItem value="create">Create</MenuItem>
            <MenuItem value="update">Update</MenuItem>
            <MenuItem value="delete">Delete</MenuItem>
            <MenuItem value="scan">Scan</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Time</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Action</TableCell>
              <TableCell>Resource</TableCell>
              <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>Details</TableCell>
              <TableCell sx={{ display: { xs: 'none', lg: 'table-cell' } }}>IP</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {entries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary">No activity recorded yet</Typography>
                </TableCell>
              </TableRow>
            ) : (
              entries.map((entry) => (
                <TableRow key={entry.id} hover>
                  <TableCell>
                    <Typography variant="caption">{entry.timestamp ? new Date(entry.timestamp).toLocaleString() : ''}</Typography>
                  </TableCell>
                  <TableCell>{entry.username || `User #${entry.user_id}`}</TableCell>
                  <TableCell>
                    <Chip label={entry.action} size="small" color={getActionColor(entry.action) as any} variant="outlined" />
                  </TableCell>
                  <TableCell>
                    {entry.resource_type && (
                      <Typography variant="caption">
                        {entry.resource_type}{entry.resource_id ? `: ${entry.resource_id}` : ''}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell sx={{ display: { xs: 'none', md: 'table-cell' } }}>
                    <Typography variant="caption" noWrap sx={{ maxWidth: 200, display: 'block' }}>
                      {entry.details}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ display: { xs: 'none', lg: 'table-cell' } }}>
                    <Typography variant="caption" fontFamily="monospace">{entry.ip_address}</Typography>
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
          onPageChange={(_e, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0) }}
        />
      </TableContainer>
    </Box>
  )
}
