/**
 * Error Handler Utility
 *
 * Provides comprehensive error handling with:
 * - User-friendly error messages in multiple languages
 * - Detailed console logging for debugging
 * - Error categorization and tracking
 * - Toast notifications with context
 */

import { ElMessage, ElNotification } from "element-plus";
import type { AxiosError } from "axios";

/**
 * Error categories for better organization
 */
export type ErrorCategory =
  | "auth" // Authentication/Authorization errors
  | "validation" // Input validation errors
  | "network" // Network/connectivity errors
  | "server" // Server-side errors (5xx)
  | "notFound" // Resource not found (404)
  | "permission" // Permission denied (403)
  | "conflict" // Conflict errors (409)
  | "rateLimit" // Rate limiting (429)
  | "unknown"; // Unknown errors

/**
 * Structured error information
 */
export interface ErrorInfo {
  category: ErrorCategory;
  message: string;
  details?: string;
  code?: string | number;
  field?: string;
  timestamp: Date;
  requestUrl?: string;
  requestMethod?: string;
}

/**
 * FastAPI validation error format
 */
interface FastAPIValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/**
 * Error response from backend
 */
interface ErrorResponse {
  detail?: string | FastAPIValidationError[];
  message?: string;
  error?:
    | {
        id?: string;
        code?: string;
        message?: string;
        details?: any;
        status?: number;
      }
    | string;
  errors?: Record<string, string[]>;
}

/**
 * Error messages by category (Russian)
 */
const ERROR_MESSAGES: Record<ErrorCategory, string> = {
  auth: "Ошибка аутентификации",
  validation: "Ошибка валидации данных",
  network: "Ошибка сети",
  server: "Ошибка сервера",
  notFound: "Ресурс не найден",
  permission: "Доступ запрещён",
  conflict: "Конфликт данных",
  rateLimit: "Слишком много запросов",
  unknown: "Неизвестная ошибка",
};

/**
 * HTTP status to category mapping
 */
const STATUS_TO_CATEGORY: Record<number, ErrorCategory> = {
  400: "validation",
  401: "auth",
  403: "permission",
  404: "notFound",
  409: "conflict",
  422: "validation",
  429: "rateLimit",
  500: "server",
  502: "server",
  503: "server",
  504: "server",
};

/**
 * Parse validation errors from FastAPI format
 */
function parseValidationErrors(errors: FastAPIValidationError[]): string {
  return errors
    .map((err) => {
      const field = err.loc.slice(1).join(".");
      const message = err.msg;
      return field ? `${field}: ${message}` : message;
    })
    .join("; ");
}

/**
 * Get human-readable field name
 */
function getFieldLabel(field: string): string {
  const fieldLabels: Record<string, string> = {
    email: "Email",
    password: "Пароль",
    firstName: "Имя",
    first_name: "Имя",
    lastName: "Фамилия",
    last_name: "Фамилия",
    title: "Название",
    description: "Описание",
    groupName: "Группа",
    group_name: "Группа",
    file: "Файл",
    startTime: "Время начала",
    start_time: "Время начала",
    endTime: "Время окончания",
    end_time: "Время окончания",
  };
  return fieldLabels[field] || field;
}

/**
 * Parse error from Axios error response
 */
export function parseError(error: AxiosError<ErrorResponse>): ErrorInfo {
  const timestamp = new Date();
  const requestUrl = error.config?.url;
  const requestMethod = error.config?.method?.toUpperCase();

  // Network error (no response)
  if (!error.response) {
    return {
      category: "network",
      message: "Не удалось подключиться к серверу",
      details: error.message || "Проверьте подключение к интернету",
      timestamp,
      requestUrl,
      requestMethod,
    };
  }

  const status = error.response.status;
  const data = error.response.data;
  const category = STATUS_TO_CATEGORY[status] || "unknown";

  // Extract message from response
  let message = ERROR_MESSAGES[category];
  let details: string | undefined;
  let field: string | undefined;

  if (data) {
    if (typeof data.detail === "string") {
      details = data.detail;
    } else if (Array.isArray(data.detail)) {
      // FastAPI validation errors
      details = parseValidationErrors(data.detail);
      if (data.detail[0]?.loc) {
        field = data.detail[0].loc.slice(1).join(".");
      }
    } else if (data.message) {
      details = data.message;
    } else if (data.error) {
      // New structured error format from backend
      if (typeof data.error === "object") {
        details = data.error.message || data.error.details;
        if (data.error.code) {
          message = `[${data.error.code}] ${message}`;
        }
      } else {
        details = data.error;
      }
    }
  }

  // Specific error messages based on status and context
  if (status === 401) {
    if (requestUrl?.includes("/login")) {
      message = "Неверный email или пароль";
    } else if (requestUrl?.includes("/refresh")) {
      message = "Сессия истекла";
      details = "Пожалуйста, войдите снова";
    } else {
      message = "Требуется авторизация";
    }
  } else if (status === 403) {
    message = "Недостаточно прав";
    details = details || "У вас нет доступа к этому ресурсу";
  } else if (status === 404) {
    message = "Не найдено";
    details = details || "Запрашиваемый ресурс не существует";
  } else if (status === 409) {
    message = "Конфликт данных";
    details = details || "Такая запись уже существует";
  } else if (status === 422) {
    message = "Ошибка валидации";
  } else if (status >= 500) {
    message = "Ошибка сервера";
    details = details || "Попробуйте позже или обратитесь в поддержку";
  }

  return {
    category,
    message,
    details,
    code: status,
    field,
    timestamp,
    requestUrl,
    requestMethod,
  };
}

/**
 * Log error to console with full details
 */
export function logError(errorInfo: ErrorInfo, originalError?: unknown): void {
  const logStyle = "color: #ff4444; font-weight: bold;";
  const detailStyle = "color: #888;";

  console.groupCollapsed(
    `%c❌ ${errorInfo.category.toUpperCase()}: ${errorInfo.message}`,
    logStyle
  );

  console.log("%cTimestamp:", detailStyle, errorInfo.timestamp.toISOString());

  if (errorInfo.requestMethod && errorInfo.requestUrl) {
    console.log(
      "%cRequest:",
      detailStyle,
      `${errorInfo.requestMethod} ${errorInfo.requestUrl}`
    );
  }

  if (errorInfo.code) {
    console.log("%cStatus Code:", detailStyle, errorInfo.code);
  }

  if (errorInfo.details) {
    console.log("%cDetails:", detailStyle, errorInfo.details);
  }

  if (errorInfo.field) {
    console.log("%cField:", detailStyle, errorInfo.field);
  }

  if (originalError) {
    console.log("%cOriginal Error:", detailStyle, originalError);
  }

  console.groupEnd();
}

/**
 * Show error notification to user
 */
export function showError(
  errorInfo: ErrorInfo,
  options?: {
    showNotification?: boolean;
    duration?: number;
  }
): void {
  const { showNotification = false, duration = 5000 } = options || {};

  if (showNotification) {
    // Full notification with details
    ElNotification({
      title: errorInfo.message,
      message: errorInfo.details || "",
      type: "error",
      duration,
      position: "top-right",
    });
  } else {
    // Simple message
    const displayMessage = errorInfo.details
      ? `${errorInfo.message}: ${errorInfo.details}`
      : errorInfo.message;

    ElMessage({
      message: displayMessage,
      type: "error",
      duration,
      showClose: true,
    });
  }
}

/**
 * Handle error with logging and user notification
 * Main entry point for error handling
 */
export function handleError(
  error: unknown,
  context?: string,
  options?: {
    silent?: boolean; // Don't show user notification
    showNotification?: boolean; // Use notification instead of message
    rethrow?: boolean; // Rethrow after handling
  }
): ErrorInfo {
  const {
    silent = false,
    showNotification = false,
    rethrow = false,
  } = options || {};

  let errorInfo: ErrorInfo;

  if ((error as AxiosError).isAxiosError) {
    errorInfo = parseError(error as AxiosError<ErrorResponse>);
  } else if (error instanceof Error) {
    errorInfo = {
      category: "unknown",
      message: error.message || "Произошла ошибка",
      details: error.stack,
      timestamp: new Date(),
    };
  } else {
    errorInfo = {
      category: "unknown",
      message: "Произошла неизвестная ошибка",
      details: String(error),
      timestamp: new Date(),
    };
  }

  // Add context to message if provided
  if (context) {
    errorInfo.message = `${context}: ${errorInfo.message}`;
  }

  // Log to console
  logError(errorInfo, error);

  // Show to user unless silent
  if (!silent) {
    showError(errorInfo, { showNotification });
  }

  // Rethrow if needed
  if (rethrow) {
    throw error;
  }

  return errorInfo;
}

/**
 * Create error handler for specific context
 * Useful for creating scoped error handlers in components/services
 */
export function createErrorHandler(context: string) {
  return (error: unknown, options?: Parameters<typeof handleError>[2]) => {
    return handleError(error, context, options);
  };
}

/**
 * Wrap async function with error handling
 */
export function withErrorHandling<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  context?: string,
  options?: Parameters<typeof handleError>[2]
): T {
  return (async (...args: Parameters<T>) => {
    try {
      return await fn(...args);
    } catch (error) {
      handleError(error, context, options);
      throw error;
    }
  }) as T;
}

/**
 * Error boundary for Vue components (use in setup)
 */
export function useErrorHandler(context: string) {
  const handler = createErrorHandler(context);

  return {
    handleError: handler,

    // Wrapper for async operations
    async safeCall<T>(
      operation: () => Promise<T>,
      options?: Parameters<typeof handleError>[2]
    ): Promise<T | null> {
      try {
        return await operation();
      } catch (error) {
        handler(error, options);
        return null;
      }
    },

    // Wrapper that doesn't catch, just logs
    async trackedCall<T>(operation: () => Promise<T>): Promise<T> {
      try {
        return await operation();
      } catch (error) {
        handler(error, { rethrow: true });
        throw error; // TypeScript needs this
      }
    },
  };
}

export default handleError;
