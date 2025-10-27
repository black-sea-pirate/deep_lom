import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { User } from "@/types";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const token = ref<string | null>(localStorage.getItem("token"));

  const isAuthenticated = computed(() => !!token.value);
  const isTeacher = computed(() => user.value?.role === "teacher");
  const isStudent = computed(() => user.value?.role === "student");

  // Mock login
  const login = async (
    email: string,
    password: string,
    role: "teacher" | "student"
  ) => {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const mockUser: User = {
      id: "1",
      email,
      role,
      firstName: role === "teacher" ? "John" : "Jane",
      lastName: role === "teacher" ? "Doe" : "Smith",
      createdAt: new Date(),
    };

    user.value = mockUser;
    token.value = "mock-jwt-token-" + Date.now();
    localStorage.setItem("token", token.value);

    return mockUser;
  };

  // Mock register
  const register = async (
    email: string,
    password: string,
    firstName: string,
    lastName: string,
    role: "teacher" | "student"
  ) => {
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const mockUser: User = {
      id: Date.now().toString(),
      email,
      role,
      firstName,
      lastName,
      createdAt: new Date(),
    };

    user.value = mockUser;
    token.value = "mock-jwt-token-" + Date.now();
    localStorage.setItem("token", token.value);

    return mockUser;
  };

  const logout = () => {
    user.value = null;
    token.value = null;
    localStorage.removeItem("token");
  };

  // Auto-login if token exists
  const checkAuth = async () => {
    if (token.value) {
      // Simulate fetching user from token
      user.value = {
        id: "1",
        email: "demo@example.com",
        role: "teacher",
        firstName: "John",
        lastName: "Doe",
        createdAt: new Date(),
      };
    }
  };

  return {
    user,
    token,
    isAuthenticated,
    isTeacher,
    isStudent,
    login,
    register,
    logout,
    checkAuth,
  };
});
