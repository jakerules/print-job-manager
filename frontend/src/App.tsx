import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { Provider } from 'react-redux'
import { store } from './store/store'
import Login from './components/Login'
import Dashboard from './components/Dashboard/Dashboard'
import QueueManager from './components/QueueManager/QueueManager'
import Scanner from './components/Scanner/Scanner'
import AdminPanel from './components/AdminPanel/AdminPanel'
import JobSubmission from './components/JobSubmission/JobSubmission'
import Layout from './components/common/Layout'
import ProtectedRoute from './components/common/ProtectedRoute'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="queue" element={<QueueManager />} />
              <Route path="scanner" element={<Scanner />} />
              <Route path="submit" element={<JobSubmission />} />
              <Route path="admin" element={<ProtectedRoute requiredRole="admin"><AdminPanel /></ProtectedRoute>} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </Provider>
  )
}

export default App
