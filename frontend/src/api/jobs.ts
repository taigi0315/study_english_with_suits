import apiClient from './client';

export interface Job {
  job_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress: number;
  error?: string;
  video_file?: string;
  subtitle_file?: string;
  show_name?: string;
  episode_name?: string;
  language_code?: string;
  max_expressions?: number;
  language_level?: string;
  test_mode?: boolean;
  no_shorts?: boolean;
  expressions?: any[];
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
}

export const jobsApi = {
  async createJob(formData: FormData): Promise<{ job_id: string; status: string; message: string }> {
    const response = await apiClient.post('/api/v1/jobs', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getJob(jobId: string): Promise<Job> {
    const response = await apiClient.get(`/api/v1/jobs/${jobId}`);
    return response.data;
  },

  async listJobs(): Promise<JobListResponse> {
    const response = await apiClient.get('/api/v1/jobs');
    return response.data;
  },

  async getJobExpressions(jobId: string): Promise<{ expressions: any[]; total: number }> {
    const response = await apiClient.get(`/api/v1/jobs/${jobId}/expressions`);
    return response.data;
  },
};
