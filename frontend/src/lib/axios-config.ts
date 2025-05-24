import axios from 'axios';
import { toast } from '@/components/ui/use-toast';

// Configure axios defaults
axios.defaults.withCredentials = true;

// Add request interceptor
axios.interceptors.request.use(
  (config) => {
    // You can add common headers or other request modifications here
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor
axios.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

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

    // Show error toast for other errors
    const errorMessage = error.response?.data?.message || 'An error occurred';
    toast({
      variant: "destructive",
      title: "Error",
      description: errorMessage,
    });

    return Promise.reject(error);
  }
);
