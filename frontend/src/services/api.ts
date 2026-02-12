import axios from 'axios';

// In production (Vercel), API is at /api
// In development, proxy handles it
const API_BASE_URL = import.meta.env.PROD ? '/api' : '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Post {
  id: number;
  content: string;
  image_url?: string;
  video_url?: string;
  word_count: number;
  status: string;
  scheduled_time?: string;
  platforms: string[];
  posted_ids: Record<string, string>;
  posted_time?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface CreatePostRequest {
  content: string;
  image_url?: string;
  video_url?: string;
  platforms: string[];
  scheduled_time?: string;
}

export interface PlatformInfo {
  connected: boolean;
  oauth_configured: boolean;
  page_name?: string;
  account_name?: string;
}

export interface PlatformStatus {
  twitter: PlatformInfo;
  linkedin: PlatformInfo;
  facebook: PlatformInfo;
  instagram_1: PlatformInfo;
  instagram_2: PlatformInfo;
  youtube: PlatformInfo;
}

// Posts API
export const postsApi = {
  async list(params?: { status?: string; limit?: number; offset?: number }) {
    const response = await api.get('/posts', { params });
    return response.data;
  },

  async get(id: number) {
    const response = await api.get(`/posts/${id}`);
    return response.data;
  },

  async create(data: CreatePostRequest) {
    const response = await api.post('/posts', data);
    return response.data;
  },

  async update(id: number, data: Partial<Post>) {
    const response = await api.patch(`/posts/${id}`, data);
    return response.data;
  },

  async delete(id: number) {
    const response = await api.delete(`/posts/${id}`);
    return response.data;
  },

  async publish(id: number) {
    const response = await api.post(`/posts/${id}/publish`);
    return response.data;
  },
};

// Platforms API
export const platformsApi = {
  async getStatus(): Promise<{ platforms: PlatformStatus }> {
    const response = await api.get('/platforms/status');
    return response.data;
  },

  async getScheduledJobs() {
    const response = await api.get('/platforms/scheduler/jobs');
    return response.data;
  },
};

export default api;
