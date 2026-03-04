import { useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Box,
  Avatar,
  Menu,
  MenuItem,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  QueueMusic as QueueIcon,
  QrCodeScanner as ScannerIcon,
  AdminPanelSettings as AdminIcon,
  NoteAdd as SubmitIcon,
  Settings as SettingsIcon,
  Menu as MenuIcon,
  AccountCircle,
} from '@mui/icons-material'
import { useState } from 'react'
import { RootState } from '../../store/store'
import { logout } from '../../store/authSlice'
import { authService } from '../../services/auth'
import { wsService } from '../../services/websocket'

const drawerWidth = 240

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  
  const { user } = useSelector((state: RootState) => state.auth)
  const dispatch = useDispatch()
  const navigate = useNavigate()

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect()
    
    return () => {
      wsService.disconnect()
    }
  }, [])

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const handleLogout = async () => {
    await authService.logout()
    dispatch(logout())
    navigate('/login')
  }

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Submit Job', icon: <SubmitIcon />, path: '/submit' },
    { text: 'Queue', icon: <QueueIcon />, path: '/queue' },
    { text: 'Scanner', icon: <ScannerIcon />, path: '/scanner' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ]

  if (user?.role === 'admin') {
    menuItems.push({ text: 'Admin', icon: <AdminIcon />, path: '/admin' })
  }

  // Only staff+ can see scanner
  if (user && !['admin', 'manager', 'staff'].includes(user.role)) {
    const scannerIdx = menuItems.findIndex((m) => m.path === '/scanner')
    if (scannerIdx !== -1) menuItems.splice(scannerIdx, 1)
  }

  const drawer = (
    <div>
      <Toolbar>
        <Typography variant="h6" noWrap component="div">
          Print Manager
        </Typography>
      </Toolbar>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton onClick={() => navigate(item.path)}>
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </div>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Print Job Manager
          </Typography>
          <IconButton color="inherit" onClick={handleMenuOpen}>
            <AccountCircle />
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleMenuClose}
          >
            <MenuItem disabled>
              {user?.username} ({user?.role})
            </MenuItem>
            <MenuItem onClick={handleLogout}>Logout</MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  )
}
