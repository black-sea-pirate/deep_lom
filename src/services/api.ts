/**
 * API Service - Centralized HTTP client configuration
 *
 * Access token  → Pinia memory only (not localStorage)
 * Refresh token → httpOnly cookie (managed by browser, never JS-accessible)
 *
 * On 401: silently calls /auth/refresh (cookie sent automatically by browser).
 * Concurrent requests during refresh are queued and retried once the new
 * access token arrives.
 */

import axios, {
  type AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from "axios";
import { ElMessage } from "element-plus";
import { handleError } from "@/utils/error-handler";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    error ? prom.reject(error) : prom.resolve(token);
  });
  failedQueue = [];
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true, // Required: sends httpOnly refresh-token cookie on every request
  headers: { "Content-Type": "application/json" },
});

// ---------------------------------------------------------------------------
// Request interceptor — attach access token from Pinia store
// ---------------------------------------------------------------------------
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Lazily import store to avoid circular dependency at module init time
    const token = _getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    if (import.meta.env.DEV) {
      console.log(
        `🚀 [API] ${config.method?.toUpperCase()} ${config.url}`,
        config.data || ""
      );
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// ---------------------------------------------------------------------------
// Response interceptor — silent token refresh on 401
// ---------------------------------------------------------------------------
api.interceptors.response.use(
  (response: AxiosResponse) => {
    if (import.meta.env.DEV) {
      console.log(`✅ [API] ${response.config.url}`, response.data);
    }
    return response;
  },
  async (error: AxiosError<{ detail?: string | any[]; message?: string }>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    const is401 = error.response?.status === 401;
    const isRefreshEndpoint = originalRequest?.url?.includes("/auth/refresh");

    if (is401 && !originalRequest._retry && !isRefreshEndpoint) {
      if (isRefreshing) {
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

      try {
        // No body needed — browser sends the httpOnly cookie automatically
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        const newToken: string = response.data.access_token;

        // Update in-memory store token
        _setAccessToken(newToken);
        processQueue(null, newToken);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        _clearSession();

        if (window.location.pathname !== "/login") {
          ElMessage.error("Сессия истекла. Пожалуйста, войдите снова.");
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // For all other errors use the centralized handler
    handleError(error, undefined, { silent: false });
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Helpers to read/write the access token stored in the Pinia auth store.
// We cannot import the store directly here (circular dep), so we delegate
// to a tiny in-module cache that the auth store syncs after each login/refresh.
// ---------------------------------------------------------------------------

let _inMemoryToken: string | null = null;

export function setApiToken(token: string | null): void {
  _inMemoryToken = token;
}

export function getApiToken(): string | null {
  return _inMemoryToken;
}

function _getAccessToken(): string | null {
  return _inMemoryToken;
}

function _setAccessToken(token: string): void {
  _inMemoryToken = token;
}

function _clearSession(): void {
  _inMemoryToken = null;
}

export default api;

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
