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
          path: "project/:id/statistics",
          name: "project-statistics",
          component: () => import("@/views/ProjectStatisticsView.vue"),
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

  // Если есть токен, но checkAuth ещё не выполнялся — ждём
  if (authStore.hasToken && !authStore.initialized) {
    await authStore.checkAuth();
  }

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
