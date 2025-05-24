import axios, { AxiosError, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import { toast } from '@/components/ui/use-toast';

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: number;
      requestId: string;
    };
    _retry?: boolean;
  }
}

// Configure axios defaults
axios.defaults.withCredentials = true;
axios.defaults.baseURL = process.env.NEXT_PUBLIC_API_URL || '/api';
axios.defaults.timeout = 10000; // 10 second timeout

// Add request interceptor
axios.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add loading state management if needed
    const requestId = Math.random().toString(36).substring(7);
    config.metadata = { startTime: new Date().getTime(), requestId };

    // Add custom headers
    config.headers = {
      ...config.headers,
      'X-Request-ID': requestId,
      'Content-Type': 'application/json',
    };

    // Log request details in development
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[${requestId}] Request:`, {
        method: config.method?.toUpperCase(),
        url: config.url,
        data: config.data,
      });
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// Add response interceptor
axios.interceptors.response.use(
  (response) => {
    const config = response.config as InternalAxiosRequestConfig;
    
    // Log response timing in development
    if (process.env.NODE_ENV === 'development' && config.metadata?.startTime) {
      const endTime = new Date().getTime();
      const duration = endTime - config.metadata.startTime;
      console.debug(`[${config.metadata.requestId}] Response:`, {
        status: response.status,
        duration: `${duration}ms`,
        data: response.data,
      });
    }
    
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig;

    // Handle session expiry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Attempt to refresh the session
        await axios.post('/api/session/refresh');
        // Retry the original request
        return axios(originalRequest);
      } catch (refreshError) {
        // If refresh fails, redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    // Log errors in development
    if (process.env.NODE_ENV === 'development') {
      console.error('API Error:', {
        config: originalRequest,
        status: error.response?.status,
        data: error.response?.data,
      });
    }

    // Show error toast for other errors
    const errorMessage = error.response?.data?.message || error.message || 'An unexpected error occurred';
    toast({
      variant: "destructive",
      title: "Error",
      description: errorMessage,
    });

    return Promise.reject(error);
  }
);
