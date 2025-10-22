import apiClient from './client';

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

export interface ExpressionStats {
  total_expressions: number;
  total_media: number;
  expressions_by_show: Record<string, number>;
  recent_expressions: Expression[];
}

export const expressionsApi = {
  async listExpressions(params?: {
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<ExpressionListResponse> {
    const response = await apiClient.get('/api/v1/expressions', { params });
    return response.data;
  },

  async getExpressionDetail(expressionId: string): Promise<Expression> {
    const response = await apiClient.get(`/api/v1/expressions/${expressionId}`);
    return response.data;
  },

  async searchExpressions(params: {
    q: string;
    page?: number;
    limit?: number;
  }): Promise<ExpressionListResponse & { query: string }> {
    const response = await apiClient.get('/api/v1/expressions/search', { params });
    return response.data;
  },

  async getExpressionStats(): Promise<ExpressionStats> {
    const response = await apiClient.get('/api/v1/expressions/stats');
    return response.data;
  },
};
