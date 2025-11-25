<script setup lang="ts">
// Teacher settings: profile, preferences, defaults
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import ThemeToggle from "@/components/ThemeToggle.vue";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

const handleLogout = () => {
  authStore.logout();
  router.push("/login");
};
</script>

<template>
  <div class="page-wrap">
    <el-container>
      <el-header class="page-header">
        <div class="header-content">
          <h1>{{ t("teacher.settings") }}</h1>
          <div class="user-section">
            <ThemeToggle />
            <span
              >{{ authStore.user?.firstName }}
              {{ authStore.user?.lastName }}</span
            >
            <el-button @click="handleLogout" link>{{
              t("common.logout")
            }}</el-button>
          </div>
        </div>
      </el-header>
      <el-main>
        <el-empty :description="t('teacher.settings')" />
      </el-main>
    </el-container>
  </div>
</template>

<style scoped lang="scss">
.page-wrap {
  min-height: 100%;
  background: var(--color-surface);
}
.page-header {
  background: var(--color-background);
  box-shadow: var(--shadow-sm);

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;

    h1 {
      font-size: 1.5rem;
      color: var(--color-primary);
    }

    .user-section {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
    }
  }
}
</style>
