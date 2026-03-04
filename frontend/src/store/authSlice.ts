import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { User } from '../types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
  loading: false,
  error: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.loading = true
      state.error = null
    },
    loginSuccess: (state, action: PayloadAction<User>) => {
      state.user = action.payload
      state.isAuthenticated = true
      state.loading = false
      state.error = null
    },
    loginFailure: (state, action: PayloadAction<string>) => {
      state.loading = false
      state.error = action.payload
      state.isAuthenticated = false
      state.user = null
    },
    logout: (state) => {
      state.user = null
      state.isAuthenticated = false
      state.loading = false
      state.error = null
    },
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload
      state.isAuthenticated = true
    },
  },
})

export const { loginStart, loginSuccess, loginFailure, logout, setUser } = authSlice.actions
export default authSlice.reducer
