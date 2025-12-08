/**
 * Authentication Service
 *
 * Handles all authentication-related API calls:
 * - User login/logout
 * - User registration
 * - Password reset
 * - Token refresh
 * - Current user profile
 */

import api from "./api";
import type { User } from "@/types";

/**
 * Login request payload
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Registration request payload
 */
export interface RegisterRequest {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  role: "teacher" | "student";
}

/**
 * Authentication response from server
 */
export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user: User;
}

/**
 * Password reset request
 */
export interface PasswordResetRequest {
  email: string;
}

/**
 * Password reset confirm
 */
export interface PasswordResetConfirm {
  token: string;
  newPassword: string;
}

/**
 * Token refresh response
 */
export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
}

/**
 * Authentication Service
 */
export const authService = {
  /**
   * Login user with email and password
   * @param credentials - Login credentials
   * @returns Authentication response with token and user
   */
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    // FastAPI OAuth2 expects form data for token endpoint
    const formData = new FormData();
    formData.append("username", credentials.email); // OAuth2 uses 'username' field
    formData.append("password", credentials.password);

    const response = await api.post<AuthResponse>("/auth/login", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    // Store tokens in localStorage
    if (response.data.access_token) {
      localStorage.setItem("token", response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem("refreshToken", response.data.refresh_token);
    }

    return response.data;
  },

  /**
   * Register new user
   * @param userData - Registration data
   * @returns Authentication response with token and user
   */
  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>("/auth/register", {
      email: userData.email,
      password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName,
      role: userData.role,
    });

    // Store tokens in localStorage
    if (response.data.access_token) {
      localStorage.setItem("token", response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem("refreshToken", response.data.refresh_token);
    }

    return response.data;
  },

  /**
   * Logout current user
   * Clears tokens from localStorage
   */
  async logout(): Promise<void> {
    try {
      await api.post("/auth/logout");
    } finally {
      // Always clear tokens, even if API call fails
      localStorage.removeItem("token");
      localStorage.removeItem("refreshToken");
    }
  },

  /**
   * Get current authenticated user profile
   * @returns Current user data
   */
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  /**
   * Refresh access token using refresh token
   * @returns New token response
   */
  async refreshToken(): Promise<TokenRefreshResponse> {
    const refreshToken = localStorage.getItem("refreshToken");

    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await api.post<TokenRefreshResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });

    if (response.data.access_token) {
      localStorage.setItem("token", response.data.access_token);
    }

    return response.data;
  },

  /**
   * Request password reset email
   * @param data - Email for password reset
   */
  async requestPasswordReset(data: PasswordResetRequest): Promise<void> {
    await api.post("/auth/password-reset/request", data);
  },

  /**
   * Confirm password reset with token
   * @param data - Reset token and new password
   */
  async confirmPasswordReset(data: PasswordResetConfirm): Promise<void> {
    await api.post("/auth/password-reset/confirm", data);
  },

  /**
   * Update current user profile
   * @param userData - Updated user data
   * @returns Updated user
   */
  async updateProfile(userData: Partial<User>): Promise<User> {
    const response = await api.patch<User>("/auth/me", {
      first_name: userData.firstName,
      last_name: userData.lastName,
    });
    return response.data;
  },

  /**
   * Change current user password
   * @param oldPassword - Current password
   * @param newPassword - New password
   */
  async changePassword(
    oldPassword: string,
    newPassword: string
  ): Promise<void> {
    await api.post("/auth/change-password", {
      current_password: oldPassword,
      new_password: newPassword,
    });
  },

  /**
   * Check if user is authenticated
   * @returns true if user has a valid token
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem("token");
  },

  /**
   * Get stored access token
   * @returns Access token or null
   */
  getToken(): string | null {
    return localStorage.getItem("token");
  },

  /**
   * Get stored refresh token
   * @returns Refresh token or null
   */
  getRefreshToken(): string | null {
    return localStorage.getItem("refreshToken");
  },
};

export default authService;
