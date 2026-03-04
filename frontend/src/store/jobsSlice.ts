import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Job, JobStats } from '../types'

interface JobsState {
  jobs: Job[]
  stats: JobStats | null
  loading: boolean
  error: string | null
  selectedJob: Job | null
  total: number
  limit: number
  offset: number
}

const initialState: JobsState = {
  jobs: [],
  stats: null,
  loading: false,
  error: null,
  selectedJob: null,
  total: 0,
  limit: 50,
  offset: 0,
}

const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    setJobs: (state, action: PayloadAction<{ jobs: Job[]; total: number; limit: number; offset: number }>) => {
      state.jobs = action.payload.jobs
      state.total = action.payload.total
      state.limit = action.payload.limit
      state.offset = action.payload.offset
      state.loading = false
    },
    setStats: (state, action: PayloadAction<JobStats>) => {
      state.stats = action.payload
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
      state.loading = false
    },
    setSelectedJob: (state, action: PayloadAction<Job | null>) => {
      state.selectedJob = action.payload
    },
    updateJob: (state, action: PayloadAction<Job>) => {
      const index = state.jobs.findIndex((j) => j.job_id === action.payload.job_id)
      if (index !== -1) {
        state.jobs[index] = action.payload
      }
      if (state.selectedJob?.job_id === action.payload.job_id) {
        state.selectedJob = action.payload
      }
    },
    addJob: (state, action: PayloadAction<Job>) => {
      state.jobs.unshift(action.payload)
      state.total += 1
    },
  },
})

export const { setJobs, setStats, setLoading, setError, setSelectedJob, updateJob, addJob } = jobsSlice.actions
export default jobsSlice.reducer
