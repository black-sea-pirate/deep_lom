<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import ThemeToggle from "@/components/ThemeToggle.vue";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

// Mock data
const upcomingTests = computed(() => [
  {
    id: "1",
    title: "Linear Equations",
    groupName: "KN420-Б",
    questionsCount: 18,
    duration: 60,
    scheduledAt: new Date(Date.now() + 86400000),
  },
  {
    id: "2",
    title: "Quantum Physics Introduction",
    groupName: "PH301-A",
    questionsCount: 10,
    duration: 90,
    scheduledAt: new Date(Date.now() + 172800000),
  },
]);

const statistics = computed(() => ({
  totalTests: 12,
  averageScore: 85,
  completedTests: 10,
}));

const handleLogout = () => {
  authStore.logout();
  router.push("/login");
};
</script>

<template>
  <div class="dashboard">
    <el-container>
      <el-header class="header">
        <div class="header-content">
          <h1>{{ t("student.dashboard") }}</h1>
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
        <div class="dashboard-content">
          <!-- Statistics -->
          <el-row :gutter="20" class="stats-row">
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover">
                <el-statistic
                  :title="t('student.totalTests')"
                  :value="statistics.totalTests"
                >
                  <template #prefix>
                    <el-icon color="#3b82f6"><Document /></el-icon>
                  </template>
                </el-statistic>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover">
                <el-statistic
                  :title="t('student.averageScore')"
                  :value="statistics.averageScore"
                  suffix="%"
                >
                  <template #prefix>
                    <el-icon color="#10b981"><TrophyBase /></el-icon>
                  </template>
                </el-statistic>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="hover">
                <el-statistic
                  :title="t('student.completedTests')"
                  :value="statistics.completedTests"
                >
                  <template #prefix>
                    <el-icon color="#f59e0b"><CircleCheck /></el-icon>
                  </template>
                </el-statistic>
              </el-card>
            </el-col>
          </el-row>

          <!-- Upcoming Tests -->
          <div class="section">
            <h2>{{ t("student.upcomingTests") }}</h2>

            <div class="tests-list">
              <el-card
                v-for="test in upcomingTests"
                :key="test.id"
                class="test-card"
                shadow="hover"
              >
                <div class="test-header">
                  <div>
                    <h3>{{ test.title }}</h3>
                    <p class="group-name">{{ test.groupName }}</p>
                  </div>
                  <el-tag type="warning">Upcoming</el-tag>
                </div>

                <div class="test-info">
                  <div class="info-item">
                    <el-icon><Document /></el-icon>
                    <span
                      >{{ test.questionsCount }}
                      {{ t("student.question") }}s</span
                    >
                  </div>
                  <div class="info-item">
                    <el-icon><Timer /></el-icon>
                    <span>{{ test.duration }} min</span>
                  </div>
                  <div class="info-item">
                    <el-icon><Calendar /></el-icon>
                    <span>{{ test.scheduledAt.toLocaleDateString() }}</span>
                  </div>
                </div>

                <el-button
                  type="primary"
                  size="large"
                  @click="router.push(`/student/test/${test.id}`)"
                  style="width: 100%; margin-top: 16px"
                >
                  {{ t("student.takeTest") }}
                </el-button>
              </el-card>

              <el-empty
                v-if="upcomingTests.length === 0"
                description="No upcoming tests"
              />
            </div>
          </div>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  min-height: 100vh;
  background-color: var(--color-surface);
}

.header {
  background: white;
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

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

.stats-row {
  margin-bottom: var(--spacing-2xl);
}

.section {
  margin-bottom: var(--spacing-2xl);

  h2 {
    margin-bottom: var(--spacing-lg);
  }
}

.tests-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--spacing-lg);
}

.test-card {
  transition: transform var(--transition-base);

  &:hover {
    transform: translateY(-4px);
  }

  .test-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-lg);

    h3 {
      font-size: 1.2rem;
      margin-bottom: var(--spacing-xs);
    }

    .group-name {
      color: var(--color-primary);
      font-weight: 500;
    }
  }

  .test-info {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);

    .info-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      color: var(--color-text-light);
    }
  }
}

@media (max-width: 768px) {
  .tests-list {
    grid-template-columns: 1fr;
  }

  .stats-row .el-col {
    margin-bottom: var(--spacing-md);
  }
}
</style>
