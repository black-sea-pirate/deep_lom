/**
 * Authentication Service
 *
 * Access token is kept in memory (Pinia store + api.ts cache).
 * Refresh token lives in an httpOnly cookie — never touched by JS.
 */

import api, { setApiToken } from "./api";
import type { User } from "@/types";

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  role: "teacher" | "student";
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
}

export interface PasswordResetRequestPayload {
  email: string;
}

export interface PasswordResetConfirmPayload {
  email: string;
  code: string;
  new_password: string;
}

export const authService = {
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const formData = new FormData();
    formData.append("username", credentials.email);
    formData.append("password", credentials.password);

    const response = await api.post<AuthResponse>("/auth/login", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    setApiToken(response.data.access_token);
    return response.data;
  },

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>("/auth/register", {
      email: userData.email,
      password: userData.password,
      first_name: userData.firstName,
      last_name: userData.lastName,
      role: userData.role,
    });

    setApiToken(response.data.access_token);
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      await api.post("/auth/logout");
    } finally {
      setApiToken(null);
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  /**
   * Silent refresh — no body needed, the browser sends the httpOnly cookie.
   * Called automatically by api.ts on 401, and by the auth store on page load.
   */
  async refreshToken(): Promise<TokenRefreshResponse> {
    // withCredentials is already set on the axios instance, but we use the
    // raw axios here to bypass the response interceptor and avoid an infinite loop.
    const { default: axios } = await import("axios");
    const baseURL =
      import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

    const response = await axios.post<TokenRefreshResponse>(
      `${baseURL}/auth/refresh`,
      {},
      { withCredentials: true }
    );

    setApiToken(response.data.access_token);
    return response.data;
  },

  async updateProfile(userData: Partial<User>): Promise<User> {
    const response = await api.patch<User>("/auth/me", {
      first_name: userData.firstName,
      last_name: userData.lastName,
    });
    return response.data;
  },

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await api.post("/auth/change-password", {
      current_password: oldPassword,
      new_password: newPassword,
    });
  },

  /** Send 6-digit reset code to email */
  async requestPasswordReset(email: string): Promise<void> {
    await api.post("/auth/password-reset/request", { email });
  },

  /** Verify code and set new password */
  async confirmPasswordReset(
    payload: PasswordResetConfirmPayload
  ): Promise<void> {
    await api.post("/auth/password-reset/confirm", payload);
  },
};

export default authService;
