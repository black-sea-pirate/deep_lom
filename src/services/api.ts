/**
 * API Service - Centralized HTTP client configuration
 *
 * This module provides a configured Axios instance with:
 * - Base URL from environment variables
 * - JWT token injection via interceptors
 * - Automatic token refresh handling
 * - Centralized error handling
 * - Request/Response logging in development
 */

import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { ElMessage } from "element-plus";

// API Base URL from environment variables
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

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
 * - Manages authentication errors (401)
 * - Provides user-friendly error messages
 */
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Log responses in development
    if (import.meta.env.DEV) {
      console.log(`✅ [API Response] ${response.config.url}`, response.data);
    }
    return response;
  },
  async (error: AxiosError<{ detail?: string; message?: string }>) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized - Token expired or invalid
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem("token");

      // Only redirect if not already on login page
      if (window.location.pathname !== "/login") {
        ElMessage.error("Session expired. Please login again.");
        window.location.href = "/login";
      }

      return Promise.reject(error);
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      ElMessage.error("You do not have permission to perform this action.");
      return Promise.reject(error);
    }

    // Handle 404 Not Found
    if (error.response?.status === 404) {
      ElMessage.error("Resource not found.");
      return Promise.reject(error);
    }

    // Handle 422 Validation Error (FastAPI)
    if (error.response?.status === 422) {
      const detail = error.response.data?.detail;
      if (Array.isArray(detail)) {
        // FastAPI validation errors format
        const messages = detail.map((err: any) => err.msg).join(", ");
        ElMessage.error(`Validation error: ${messages}`);
      } else {
        ElMessage.error("Validation error. Please check your input.");
      }
      return Promise.reject(error);
    }

    // Handle 500 Server Error
    if (error.response?.status === 500) {
      ElMessage.error("Server error. Please try again later.");
      return Promise.reject(error);
    }

    // Handle network errors
    if (!error.response) {
      ElMessage.error("Network error. Please check your connection.");
      return Promise.reject(error);
    }

    // Generic error message
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "An error occurred";
    ElMessage.error(message);

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
