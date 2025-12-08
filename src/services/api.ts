/**
 * API Service - Centralized HTTP client configuration
 *
 * This module provides a configured Axios instance with:
 * - Base URL from environment variables
 * - JWT token injection via interceptors
 * - Automatic token refresh handling
 * - Centralized error handling with detailed logging
 * - Request/Response logging in development
 */

import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { ElMessage } from "element-plus";
import { handleError, type ErrorInfo } from "@/utils/error-handler";

// API Base URL from environment variables
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
// Queue of failed requests to retry after token refresh
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

/**
 * Process queued requests after token refresh
 */
const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

/**
 * Configured Axios instance for all API calls
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds timeout
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Request Interceptor
 * - Injects JWT token from localStorage
 * - Logs requests in development mode
 */
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage
    const token = localStorage.getItem("token");

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log requests in development
    if (import.meta.env.DEV) {
      console.log(
        `🚀 [API Request] ${config.method?.toUpperCase()} ${config.url}`,
        config.data || ""
      );
    }

    return config;
  },
  (error: AxiosError) => {
    console.error("❌ [API Request Error]", error);
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * - Handles successful responses
 * - Manages authentication errors (401) with token refresh
 * - Provides user-friendly error messages with detailed logging
 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log responses in development
    if (import.meta.env.DEV) {
      console.log(`✅ [API Response] ${response.config.url}`, response.data);
    }
    return response;
  },
  async (
    error: AxiosError<{
      detail?: string | any[];
      message?: string;
      error?: any;
    }>
  ) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Handle 401 Unauthorized - Token expired or invalid
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Check if we're already refreshing
      if (isRefreshing) {
        // Queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem("refreshToken");

      if (refreshToken) {
        try {
          // Try to refresh the token
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const newToken = response.data.access_token;
          localStorage.setItem("token", newToken);

          // Process queued requests
          processQueue(null, newToken);

          // Retry original request
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed - clear tokens and redirect to login
          processQueue(refreshError as Error, null);
          localStorage.removeItem("token");
          localStorage.removeItem("refreshToken");

          if (window.location.pathname !== "/login") {
            ElMessage.error("Сессия истекла. Пожалуйста, войдите снова.");
            window.location.href = "/login";
          }

          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        // No refresh token - clear and redirect
        localStorage.removeItem("token");

        if (window.location.pathname !== "/login") {
          ElMessage.error("Сессия истекла. Пожалуйста, войдите снова.");
          window.location.href = "/login";
        }

        return Promise.reject(error);
      }
    }

    // Use centralized error handler for all other errors
    // This logs detailed error info and shows user-friendly messages
    handleError(error, undefined, { silent: false });

    return Promise.reject(error);
  }
);

export default api;

/**
 * Type-safe API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

/**
 * Paginated response type for list endpoints
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
