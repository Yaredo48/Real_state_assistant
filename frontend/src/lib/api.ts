import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
const TOKEN_KEY = process.env.NEXT_PUBLIC_TOKEN_KEY || 'deallens_access_token';
const REFRESH_TOKEN_KEY = process.env.NEXT_PUBLIC_REFRESH_TOKEN_KEY || 'deallens_refresh_token';

// Create axios instance
const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = Cookies.get(REFRESH_TOKEN_KEY);
        if (refreshToken) {
          const response = await axios.post(`${API_URL}/api/auth/refresh`, {}, {
            headers: {
              Authorization: `Bearer ${refreshToken}`,
            },
          });

          const { access_token, refresh_token } = response.data;
          Cookies.set(TOKEN_KEY, access_token);
          Cookies.set(REFRESH_TOKEN_KEY, refresh_token);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return api(originalRequest);
        }
      } catch (refreshError) {
        Cookies.remove(TOKEN_KEY);
        Cookies.remove(REFRESH_TOKEN_KEY);
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  register: async (data: {
    email: string;
    password: string;
    full_name?: string;
    phone?: string;
    company?: string;
  }) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  logout: async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      Cookies.remove(TOKEN_KEY);
      Cookies.remove(REFRESH_TOKEN_KEY);
    }
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  changePassword: async (data: { current_password: string; new_password: string }) => {
    const response = await api.put('/auth/me/password', data);
    return response.data;
  },

  requestPasswordReset: async (email: string) => {
    const response = await api.post('/auth/password-reset/request', { email });
    return response.data;
  },

  confirmPasswordReset: async (data: { token: string; new_password: string }) => {
    const response = await api.post('/auth/password-reset/confirm', data);
    return response.data;
  },

  refreshToken: async () => {
    const refreshToken = Cookies.get(REFRESH_TOKEN_KEY);
    if (!refreshToken) throw new Error('No refresh token');

    const response = await api.post('/auth/refresh', {}, {
      headers: { Authorization: `Bearer ${refreshToken}` },
    });
    return response.data;
  },
};

// Properties API
export const propertiesApi = {
  list: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await api.get('/properties/', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/properties/${id}`);
    return response.data;
  },

  create: async (data: {
    property_address?: string;
    property_city?: string;
    property_zone?: string;
    property_description?: string;
  }) => {
    const response = await api.post('/properties/', data);
    return response.data;
  },

  update: async (id: string, data: Record<string, unknown>) => {
    const response = await api.put(`/properties/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/properties/${id}`);
  },

  analyze: async (id: string) => {
    const response = await api.post(`/properties/${id}/analyze`);
    return response.data;
  },
};

// Documents API
export const documentsApi = {
  list: async (params?: {
    property_id?: string;
    document_type?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await api.get('/documents/', { params });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  upload: async (file: File, propertyId?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (propertyId) {
      formData.append('property_id', propertyId);
    }

    const response = await api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadMultiple: async (files: File[], propertyId?: string) => {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    if (propertyId) {
      formData.append('property_id', propertyId);
    }

    const response = await api.post('/documents/upload/multiple', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  update: async (id: string, data: Record<string, unknown>) => {
    const response = await api.put(`/documents/${id}`, data);
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/documents/${id}`);
  },

  reprocess: async (id: string) => {
    const response = await api.post(`/documents/${id}/reprocess`);
    return response.data;
  },

  download: async (id: string) => {
    const response = await api.get(`/documents/${id}/download`);
    return response.data;
  },

  getTaskStatus: async (taskId: string) => {
    const response = await api.get(`/documents/task/${taskId}`);
    return response.data;
  },
};

// Analysis API
export const analysisApi = {
  analyze: async (data: { property_id: string; analysis_types?: string[] }) => {
    const response = await api.post('/analysis/analyze', data);
    return response.data;
  },

  getJob: async (jobId: string) => {
    const response = await api.get(`/analysis/jobs/${jobId}`);
    return response.data;
  },

  listJobs: async (params?: { skip?: number; limit?: number; status?: string }) => {
    const response = await api.get('/analysis/jobs', { params });
    return response.data;
  },

  getReport: async (jobId: string) => {
    const response = await api.get(`/analysis/jobs/${jobId}/report`);
    return response.data;
  },

  downloadReport: async (jobId: string) => {
    const response = await api.get(`/analysis/jobs/${jobId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  retryJob: async (jobId: string) => {
    const response = await api.post(`/analysis/jobs/${jobId}/retry`);
    return response.data;
  },
};

// RAG API
export const ragApi = {
  search: async (data: { query: string; document_type?: string; limit?: number }) => {
    const response = await api.post('/rag/search', data);
    return response.data;
  },

  analyze: async (data: {
    query: string;
    document_type?: string;
    analysis_type?: string;
    limit?: number;
  }) => {
    const response = await api.post('/rag/analyze', data);
    return response.data;
  },

  query: async (data: { query: string }) => {
    const response = await api.post('/rag/query', data);
    return response.data;
  },

  getStats: async () => {
    const response = await api.get('/rag/stats');
    return response.data;
  },

  deleteDocumentVectors: async (documentId: string) => {
    const response = await api.delete(`/rag/documents/${documentId}`);
    return response.data;
  },
};

export default api;
