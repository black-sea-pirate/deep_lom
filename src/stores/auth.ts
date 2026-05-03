import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { User } from "@/types";
import { authService } from "@/services";
import { setApiToken } from "@/services/api";

export const useAuthStore = defineStore("auth", () => {
  // Access token lives in memory only — never in localStorage.
  // Refresh token is an httpOnly cookie managed by the browser.
  const user = ref<User | null>(null);
  const token = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  // False until the initial silent-refresh attempt completes (success or failure).
  const initialized = ref(false);

  const isAuthenticated = computed(() => !!token.value && !!user.value);
  const isVerified = computed(() => user.value?.isVerified === true);
  const isTeacher = computed(() => user.value?.role === "teacher");
  const isStudent = computed(() => user.value?.role === "student");

  const login = async (
    email: string,
    password: string,
    _role: "teacher" | "student"
  ) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await authService.login({ email, password });
      user.value = response.user;
      token.value = response.access_token;
      setApiToken(response.access_token);
      return response.user;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Login failed";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const register = async (
    email: string,
    password: string,
    firstName: string,
    lastName: string,
    role: "teacher" | "student"
  ) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await authService.register({
        email,
        password,
        firstName,
        lastName,
        role,
      });
      user.value = response.user;
      token.value = response.access_token;
      setApiToken(response.access_token);
      return response.user;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Registration failed";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch {
      // Always clear local state even if the API call fails
    } finally {
      user.value = null;
      token.value = null;
      setApiToken(null);
    }
  };

  /**
   * Called once on app boot (router guard).
   * Tries a silent token refresh via the httpOnly cookie.
   * If the cookie is absent or expired the user must log in manually.
   */
  const checkAuth = async () => {
    loading.value = true;
    try {
      const refreshResponse = await authService.refreshToken();
      token.value = refreshResponse.access_token;
      setApiToken(refreshResponse.access_token);

      const currentUser = await authService.getCurrentUser();
      user.value = currentUser;
    } catch {
      user.value = null;
      token.value = null;
      setApiToken(null);
    } finally {
      loading.value = false;
      initialized.value = true;
    }
  };

  const updateProfile = async (userData: Partial<User>) => {
    loading.value = true;
    try {
      const updatedUser = await authService.updateProfile(userData);
      user.value = updatedUser;
      return updatedUser;
    } finally {
      loading.value = false;
    }
  };

  const changePassword = async (oldPassword: string, newPassword: string) => {
    loading.value = true;
    try {
      await authService.changePassword(oldPassword, newPassword);
    } finally {
      loading.value = false;
    }
  };

  const clearError = () => {
    error.value = null;
  };

  return {
    user,
    token,
    loading,
    error,
    initialized,
    isAuthenticated,
    isVerified,
    isTeacher,
    isStudent,
    login,
    register,
    logout,
    checkAuth,
    updateProfile,
    changePassword,
    clearError,
  };
});
