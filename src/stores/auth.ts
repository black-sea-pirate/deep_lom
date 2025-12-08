import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { User } from "@/types";
import { authService } from "@/services";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const token = ref<string | null>(localStorage.getItem("token"));
  const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
  const loading = ref(false);
  const error = ref<string | null>(null);
  const initialized = ref(false); // Флаг что checkAuth завершился

  const isAuthenticated = computed(() => !!token.value && !!user.value);
  const hasToken = computed(() => !!token.value); // Для быстрой проверки до checkAuth
  const isTeacher = computed(() => user.value?.role === "teacher");
  const isStudent = computed(() => user.value?.role === "student");

  /**
   * Login user with email and password
   */
  const login = async (
    email: string,
    password: string,
    _role: "teacher" | "student" // Role is determined by backend
  ) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await authService.login({ email, password });

      user.value = response.user;
      token.value = response.access_token;
      localStorage.setItem("token", response.access_token);

      return response.user;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Login failed";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Register new user
   */
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
      localStorage.setItem("token", response.access_token);

      return response.user;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Registration failed";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Logout current user
   */
  const logout = async () => {
    try {
      await authService.logout();
    } catch {
      // Ignore logout API errors
    } finally {
      user.value = null;
      token.value = null;
      refreshToken.value = null;
      localStorage.removeItem("token");
      localStorage.removeItem("refreshToken");
    }
  };

  /**
   * Check authentication status and fetch current user
   */
  const checkAuth = async () => {
    if (!token.value) {
      user.value = null;
      initialized.value = true;
      return;
    }

    loading.value = true;
    try {
      const currentUser = await authService.getCurrentUser();
      user.value = currentUser;
    } catch (err) {
      // Token is invalid or expired
      user.value = null;
      token.value = null;
      localStorage.removeItem("token");
    } finally {
      loading.value = false;
      initialized.value = true;
    }
  };

  /**
   * Refresh access token
   */
  const refreshAccessToken = async () => {
    if (!refreshToken.value) {
      throw new Error("No refresh token available");
    }

    try {
      const response = await authService.refreshToken();
      token.value = response.access_token;
      localStorage.setItem("token", response.access_token);
      return response.access_token;
    } catch (err) {
      // Refresh failed, logout user
      await logout();
      throw err;
    }
  };

  /**
   * Update user profile
   */
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

  /**
   * Change user password
   */
  const changePassword = async (oldPassword: string, newPassword: string) => {
    loading.value = true;
    try {
      await authService.changePassword(oldPassword, newPassword);
    } finally {
      loading.value = false;
    }
  };

  /**
   * Clear error state
   */
  const clearError = () => {
    error.value = null;
  };

  return {
    // State
    user,
    token,
    refreshToken,
    loading,
    error,
    initialized,
    // Getters
    isAuthenticated,
    hasToken,
    isTeacher,
    isStudent,
    // Actions
    login,
    register,
    logout,
    checkAuth,
    refreshAccessToken,
    updateProfile,
    changePassword,
    clearError,
  };
});
