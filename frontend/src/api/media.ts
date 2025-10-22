import apiClient from './client';

export interface Media {
  id: string;
  show_name: string;
  episode_name: string;
  language_code: string;
  created_at?: string;
  expression_count: number;
}

export interface MediaDetail {
  id: string;
  show_name: string;
  episode_name: string;
  language_code: string;
  subtitle_file_path?: string;
  video_file_path?: string;
  created_at?: string;
  updated_at?: string;
  expression_count: number;
}

export interface MediaListResponse {
  media: Media[];
  total: number;
  page: number;
  limit: number;
}

export interface Expression {
  id: string;
  expression: string;
  expression_translation?: string;
  expression_dialogue?: string;
  expression_dialogue_translation?: string;
  similar_expressions: string[];
  context_start_time?: string;
  context_end_time?: string;
  scene_type?: string;
  context_video_path?: string;
  slide_video_path?: string;
  created_at?: string;
}

export interface ExpressionListResponse {
  expressions: Expression[];
  total: number;
  page: number;
  limit: number;
}

export const mediaApi = {
  async listMedia(params?: {
    show_name?: string;
    page?: number;
    limit?: number;
  }): Promise<MediaListResponse> {
    const response = await apiClient.get('/api/v1/media', { params });
    return response.data;
  },

  async getMediaDetail(mediaId: string): Promise<MediaDetail> {
    const response = await apiClient.get(`/api/v1/media/${mediaId}`);
    return response.data;
  },

  async getMediaExpressions(
    mediaId: string,
    params?: {
      page?: number;
      limit?: number;
    }
  ): Promise<ExpressionListResponse> {
    const response = await apiClient.get(`/api/v1/media/${mediaId}/expressions`, {
      params,
    });
    return response.data;
  },

  async deleteMedia(mediaId: string): Promise<void> {
    await apiClient.delete(`/api/v1/media/${mediaId}`);
  },

  async getContextVideo(mediaId: string, expressionId: string) {
    const response = await apiClient.get(
      `/api/v1/media/${mediaId}/video/context/${expressionId}`
    );
    return response.data;
  },

  async getSlideVideo(mediaId: string, expressionId: string) {
    const response = await apiClient.get(
      `/api/v1/media/${mediaId}/video/slide/${expressionId}`
    );
    return response.data;
  },

  async getFinalVideo(mediaId: string) {
    const response = await apiClient.get(`/api/v1/media/${mediaId}/video/final`);
    return response.data;
  },

  // Video streaming URL generators
  getContextVideoUrl(mediaId: string, expressionId: string): string {
    return `${apiClient.defaults.baseURL}/api/v1/media/${mediaId}/video/context/${expressionId}`;
  },

  getSlideVideoUrl(mediaId: string, expressionId: string): string {
    return `${apiClient.defaults.baseURL}/api/v1/media/${mediaId}/video/slide/${expressionId}`;
  },

  getFinalVideoUrl(mediaId: string): string {
    return `${apiClient.defaults.baseURL}/api/v1/media/${mediaId}/video/final`;
  },
};
