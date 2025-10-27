import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      redirect: "/login",
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
    },
    {
      path: "/teacher",
      name: "teacher",
      component: () => import("@/views/TeacherDashboardView.vue"),
      meta: { requiresAuth: true, role: "teacher" },
    },
    {
      path: "/teacher/project/create",
      name: "project-create",
      component: () => import("@/views/ProjectCreateView.vue"),
      meta: { requiresAuth: true, role: "teacher" },
    },
    {
      path: "/teacher/project/:id",
      name: "project-detail",
      component: () => import("@/views/ProjectDetailView.vue"),
      meta: { requiresAuth: true, role: "teacher" },
    },
    {
      path: "/teacher/project/:id/edit",
      name: "project-edit",
      component: () => import("@/views/QuestionEditorView.vue"),
      meta: { requiresAuth: true, role: "teacher" },
    },
    {
      path: "/teacher/project/:id/lobby",
      name: "project-lobby",
      component: () => import("@/views/LobbyView.vue"),
      meta: { requiresAuth: true, role: "teacher" },
    },
    {
      path: "/teacher/project/:id/statistics",
      name: "project-statistics",
      component: () => import("@/views/ProjectStatisticsView.vue"),
      meta: { requiresAuth: true, role: "teacher" },
    },
    {
      path: "/student",
      name: "student",
      component: () => import("@/views/StudentDashboardView.vue"),
      meta: { requiresAuth: true, role: "student" },
    },
    {
      path: "/student/test/:id",
      name: "test-take",
      component: () => import("@/views/TestTakeView.vue"),
      meta: { requiresAuth: true, role: "student" },
    },
    {
      path: "/student/test/:id/results",
      name: "test-results",
      component: () => import("@/views/TestResultsView.vue"),
      meta: { requiresAuth: true, role: "student" },
    },
  ],
});

// Navigation guard
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next("/login");
  } else if (to.meta.role && authStore.user?.role !== to.meta.role) {
    // Redirect to appropriate dashboard
    next(authStore.isTeacher ? "/teacher" : "/student");
  } else {
    next();
  }
});

export default router;
