<script setup lang="ts">
// TeacherLayout provides a persistent left sidebar for all teacher routes
// It keeps the existing per-view headers intact (e.g., in TeacherDashboardView)
// and only handles global navigation for the teacher area.
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import ThemeToggle from "@/components/ThemeToggle.vue";

const route = useRoute();
const router = useRouter();
const { t, locale } = useI18n();

const languages = [
  { value: "en", label: "EN" },
  { value: "pl", label: "PL" },
  { value: "ua", label: "UA" },
  { value: "ru", label: "RU" },
];

const changeLanguage = (lang: string) => {
  locale.value = lang;
  localStorage.setItem("locale", lang);
};

// Compute active menu key based on current route path.
// This ensures nested routes like /teacher/project/:id still highlight Projects.
const activeMenu = computed(() => {
  const p = route.path;
  if (p.startsWith("/teacher/project")) return "/teacher";
  if (p.startsWith("/teacher/participants")) return "/teacher/participants";
  if (p.startsWith("/teacher/materials")) return "/teacher/materials";
  if (p.startsWith("/teacher/analytics")) return "/teacher/analytics";
  if (p.startsWith("/teacher/settings")) return "/teacher/settings";
  // Default to dashboard/projects
  return "/teacher";
});
</script>

<template>
  <div class="teacher-layout">
    <el-container>
      <!-- Left Sidebar: main teacher navigation -->
      <el-aside width="240px" class="sidebar">
        <div class="brand">
          <!-- Keep branding minimal; can be replaced with logo later -->
          <span class="brand-title">AI Tests</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          class="menu"
          :collapse="false"
        >
          <!-- Projects -->
          <el-menu-item index="/teacher">
            <el-icon><Folder /></el-icon>
            <span>{{ t("teacher.menu.projects") }}</span>
          </el-menu-item>

          <!-- Participants: groups + individuals -->
          <el-menu-item index="/teacher/participants">
            <el-icon><User /></el-icon>
            <span>{{ t("teacher.menu.participants") }}</span>
          </el-menu-item>

          <!-- Materials -->
          <el-menu-item index="/teacher/materials">
            <el-icon><Document /></el-icon>
            <span>{{ t("teacher.menu.materials") }}</span>
          </el-menu-item>

          <!-- Analytics & Reports -->
          <el-menu-item index="/teacher/analytics">
            <el-icon><DataAnalysis /></el-icon>
            <span>{{ t("teacher.menu.analytics") }}</span>
          </el-menu-item>

          <!-- Settings -->
          <el-menu-item index="/teacher/settings">
            <el-icon><Setting /></el-icon>
            <span>{{ t("teacher.menu.settings") }}</span>
          </el-menu-item>
        </el-menu>

        <!-- Bottom controls: Theme & Language -->
        <div class="sidebar-bottom">
          <div class="bottom-controls">
            <ThemeToggle />
            <el-select
              :model-value="locale"
              @change="changeLanguage"
              size="small"
              style="width: 70px"
            >
              <el-option
                v-for="lang in languages"
                :key="lang.value"
                :label="lang.label"
                :value="lang.value"
              />
            </el-select>
          </div>
        </div>
      </el-aside>

      <!-- Main area for nested teacher views -->
      <el-container>
        <el-main class="content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped lang="scss">
.teacher-layout {
  min-height: 100vh;
  background: var(--color-surface);
}

.sidebar {
  background: var(--color-background);
  border-right: 1px solid var(--color-neutral);
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: sticky;
  top: 0;
}

.brand {
  display: flex;
  align-items: center;
  height: 60px;
  padding: 0 var(--spacing-lg);
  border-bottom: 1px solid var(--color-neutral);

  .brand-title {
    font-weight: 700;
    color: var(--color-primary);
  }
}

.menu {
  border-right: none;
  flex: 1;
}

.sidebar-bottom {
  padding: var(--spacing-md);
  border-top: 1px solid var(--color-neutral);
  margin-top: auto;
  flex-shrink: 0;
}

.bottom-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.content {
  padding: 0; /* Child views already manage their own header/main padding */
}
</style>
