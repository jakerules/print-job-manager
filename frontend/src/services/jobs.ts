import { apiService } from './api'
import { Job, JobStats, PaginatedResponse } from '../types'

export const jobService = {
  async getJobs(params?: {
    status?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<PaginatedResponse<Job>> {
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.search) queryParams.append('search', params.search)
    if (params?.limit) queryParams.append('limit', params.limit.toString())
    if (params?.offset) queryParams.append('offset', params.offset.toString())

    const url = `/jobs?${queryParams.toString()}`
    return await apiService.get<PaginatedResponse<Job>>(url)
  },

  async getJob(jobId: string): Promise<Job> {
    const response = await apiService.get<{ success: boolean; job: Job }>(`/jobs/${jobId}`)
    return response.job
  },

  async updateJobStatus(jobId: string, acknowledged?: boolean, completed?: boolean): Promise<Job> {
    const data: any = {}
    if (acknowledged !== undefined) data.acknowledged = acknowledged
    if (completed !== undefined) data.completed = completed
    
    const response = await apiService.put<{ success: boolean; job: Job }>(`/jobs/${jobId}/status`, data)
    return response.job
  },

  async updateJobNotes(jobId: string, notes: string): Promise<void> {
    await apiService.put(`/jobs/${jobId}/notes`, { notes })
  },

  async getStats(): Promise<JobStats> {
    const response = await apiService.get<{ success: boolean; stats: JobStats }>('/jobs/stats')
    return response.stats
  },
}
