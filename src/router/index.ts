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
      redirect: "/login",
    },
    {
      path: "/verify-email",
      name: "verify-email",
      component: () => import("@/views/EmailVerificationView.vue"),
      meta: { requiresAuth: true },
    },
    {
      // Teacher area now uses a layout with a persistent sidebar
      path: "/teacher",
      component: () => import("@/layouts/TeacherLayout.vue"),
      meta: { requiresAuth: true, role: "teacher" },
      children: [
        {
          path: "",
          name: "teacher-dashboard",
          component: () => import("@/views/TeacherDashboardView.vue"),
        },
        {
          path: "participants",
          name: "teacher-participants",
          component: () => import("@/views/TeacherParticipantsView.vue"),
        },
        {
          path: "materials",
          name: "teacher-materials",
          component: () => import("@/views/TeacherMaterialsView.vue"),
        },
        {
          path: "analytics",
          name: "teacher-analytics",
          component: () => import("@/views/TeacherAnalyticsView.vue"),
        },
        {
          path: "settings",
          name: "teacher-settings",
          component: () => import("@/views/TeacherSettingsView.vue"),
        },
        {
          path: "project/create",
          name: "project-create",
          component: () => import("@/views/ProjectCreateView.vue"),
        },
        {
          path: "project/:id",
          name: "project-detail",
          component: () => import("@/views/ProjectDetailView.vue"),
        },
        {
          path: "project/:id/edit",
          name: "project-edit",
          component: () => import("@/views/QuestionEditorView.vue"),
        },
        {
          path: "project/:id/lobby",
          name: "project-lobby",
          component: () => import("@/views/LobbyView.vue"),
        },
        {
          path: "project/:id/test/:testId/review",
          name: "test-review",
          component: () => import("@/views/TestReviewView.vue"),
        },
      ],
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
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // On first navigation always attempt a silent refresh via httpOnly cookie.
  if (!authStore.initialized) {
    await authStore.checkAuth();
  }

  const isAuth = authStore.isAuthenticated;
  const isVerified = authStore.user?.isVerified ?? false;
  const requiresAuth = to.meta.requiresAuth;
  const requiredRole = to.meta.role as string | undefined;

  // Not authenticated — send to login
  if (requiresAuth && !isAuth) {
    return next("/login");
  }

  // Authenticated but email not verified — send to verification page
  // (except for verify-email itself and auth endpoints to avoid loop)
  if (isAuth && !isVerified && to.name !== "verify-email") {
    return next("/verify-email");
  }

  // Wrong role
  if (requiredRole && authStore.user?.role !== requiredRole) {
    return next(authStore.isTeacher ? "/teacher" : "/student");
  }

  next();
});

export default router;
