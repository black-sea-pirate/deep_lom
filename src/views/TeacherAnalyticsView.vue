<script setup lang="ts">
/**
 * TeacherAnalyticsView
 *
 * Comprehensive analytics and reports for teacher:
 * - Overview statistics (tests, students, avg scores)
 * - Score distribution chart
 * - Recent test results
 * - Top performing students
 * - Project performance comparison
 */
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import ThemeToggle from "@/components/ThemeToggle.vue";
import {
  TrendCharts,
  User,
  Document,
  Timer,
  Trophy,
  DataAnalysis,
  ArrowUp,
  ArrowDown,
} from "@element-plus/icons-vue";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

// State
const loading = ref(false);
const selectedPeriod = ref("month");

// Mock analytics data
const overviewStats = ref({
  totalTests: 24,
  totalStudents: 156,
  avgScore: 78.5,
  completionRate: 92,
  avgTimeMinutes: 42,
  testsThisMonth: 8,
  scoreChange: 3.2, // positive = improvement
  studentsChange: 12,
});

// Mock score distribution data
const scoreDistribution = ref([
  { range: "0-20", count: 3, percentage: 2 },
  { range: "21-40", count: 8, percentage: 5 },
  { range: "41-60", count: 25, percentage: 16 },
  { range: "61-80", count: 68, percentage: 44 },
  { range: "81-100", count: 52, percentage: 33 },
]);

// Mock recent tests data
const recentTests = ref([
  {
    id: "test-1",
    projectName: "Linear Algebra Final",
    date: new Date("2024-11-20"),
    participants: 32,
    avgScore: 75.4,
    passRate: 88,
  },
  {
    id: "test-2",
    projectName: "Physics Midterm",
    date: new Date("2024-11-18"),
    participants: 45,
    avgScore: 82.1,
    passRate: 94,
  },
  {
    id: "test-3",
    projectName: "Programming Quiz 5",
    date: new Date("2024-11-15"),
    participants: 28,
    avgScore: 71.8,
    passRate: 79,
  },
  {
    id: "test-4",
    projectName: "Chemistry Lab Test",
    date: new Date("2024-11-12"),
    participants: 36,
    avgScore: 68.9,
    passRate: 72,
  },
  {
    id: "test-5",
    projectName: "Math Quiz 4",
    date: new Date("2024-11-10"),
    participants: 41,
    avgScore: 85.2,
    passRate: 96,
  },
]);

// Mock top students data
const topStudents = ref([
  { id: "s1", name: "Alice Williams", avgScore: 95.2, testsCompleted: 8 },
  { id: "s2", name: "John Doe", avgScore: 92.8, testsCompleted: 7 },
  { id: "s3", name: "Jane Smith", avgScore: 91.5, testsCompleted: 8 },
  { id: "s4", name: "Bob Johnson", avgScore: 89.3, testsCompleted: 6 },
  { id: "s5", name: "Charlie Brown", avgScore: 87.9, testsCompleted: 8 },
]);

// Mock project performance data
const projectPerformance = ref([
  {
    name: "Linear Algebra",
    avgScore: 76.2,
    tests: 6,
    students: 45,
    trend: "up",
  },
  { name: "Physics 101", avgScore: 82.5, tests: 4, students: 52, trend: "up" },
  {
    name: "Programming",
    avgScore: 71.3,
    tests: 8,
    students: 38,
    trend: "down",
  },
  {
    name: "Chemistry",
    avgScore: 68.9,
    tests: 3,
    students: 41,
    trend: "stable",
  },
  { name: "Mathematics", avgScore: 85.1, tests: 5, students: 48, trend: "up" },
]);

// Period options
const periodOptions = [
  { value: "week", label: "Last 7 days" },
  { value: "month", label: "Last 30 days" },
  { value: "quarter", label: "Last 3 months" },
  { value: "year", label: "Last year" },
  { value: "all", label: "All time" },
];

// Helpers
const formatDate = (date: Date): string => {
  return new Date(date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
};

const getScoreColor = (score: number): string => {
  if (score >= 80) return "var(--el-color-success)";
  if (score >= 60) return "var(--el-color-warning)";
  return "var(--el-color-danger)";
};

const getTrendIcon = (trend: string) => {
  if (trend === "up") return ArrowUp;
  if (trend === "down") return ArrowDown;
  return null;
};

const getTrendColor = (trend: string): string => {
  if (trend === "up") return "var(--el-color-success)";
  if (trend === "down") return "var(--el-color-danger)";
  return "var(--el-color-info)";
};

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
          <h1>{{ t("teacher.analyticsReports") }}</h1>
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
        <div class="analytics-content">
          <!-- Period Selector -->
          <div class="period-selector">
            <span class="period-label">{{
              t("analyticsPage.showDataFor") || "Show data for:"
            }}</span>
            <el-select
              v-model="selectedPeriod"
              size="default"
              style="width: 160px"
            >
              <el-option
                v-for="option in periodOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </div>

          <!-- Overview Stats Cards -->
          <div class="stats-grid">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon tests">
                <el-icon :size="28"><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ overviewStats.totalTests }}</div>
                <div class="stat-label">
                  {{ t("analyticsPage.totalTests") || "Total Tests" }}
                </div>
                <div class="stat-change positive">
                  +{{ overviewStats.testsThisMonth }}
                  {{ t("analyticsPage.thisMonth") || "this month" }}
                </div>
              </div>
            </el-card>

            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon students">
                <el-icon :size="28"><User /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ overviewStats.totalStudents }}</div>
                <div class="stat-label">
                  {{ t("analyticsPage.totalStudents") || "Total Students" }}
                </div>
                <div class="stat-change positive">
                  +{{ overviewStats.studentsChange }}
                  {{ t("analyticsPage.new") || "new" }}
                </div>
              </div>
            </el-card>

            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon score">
                <el-icon :size="28"><TrendCharts /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ overviewStats.avgScore }}%</div>
                <div class="stat-label">
                  {{ t("analyticsPage.averageScore") || "Average Score" }}
                </div>
                <div
                  class="stat-change"
                  :class="
                    overviewStats.scoreChange >= 0 ? 'positive' : 'negative'
                  "
                >
                  {{ overviewStats.scoreChange >= 0 ? "+" : ""
                  }}{{ overviewStats.scoreChange }}%
                </div>
              </div>
            </el-card>

            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon completion">
                <el-icon :size="28"><Timer /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">
                  {{ overviewStats.completionRate }}%
                </div>
                <div class="stat-label">
                  {{ t("analyticsPage.completionRate") || "Completion Rate" }}
                </div>
                <div class="stat-sub">
                  {{ t("analyticsPage.avgTime") || "Avg time" }}:
                  {{ overviewStats.avgTimeMinutes }}min
                </div>
              </div>
            </el-card>
          </div>

          <!-- Main Content Grid -->
          <div class="main-grid">
            <!-- Score Distribution -->
            <el-card class="chart-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>{{
                    t("analyticsPage.scoreDistribution") || "Score Distribution"
                  }}</span>
                </div>
              </template>
              <div class="distribution-chart">
                <div
                  v-for="item in scoreDistribution"
                  :key="item.range"
                  class="distribution-bar"
                >
                  <div class="bar-label">{{ item.range }}</div>
                  <div class="bar-container">
                    <div
                      class="bar-fill"
                      :style="{
                        width: `${item.percentage}%`,
                        backgroundColor: item.range.startsWith('8')
                          ? 'var(--el-color-success)'
                          : item.range.startsWith('6')
                          ? 'var(--el-color-primary)'
                          : item.range.startsWith('4')
                          ? 'var(--el-color-warning)'
                          : 'var(--el-color-danger)',
                      }"
                    ></div>
                  </div>
                  <div class="bar-value">
                    {{ item.count }} ({{ item.percentage }}%)
                  </div>
                </div>
              </div>
            </el-card>

            <!-- Recent Tests -->
            <el-card class="table-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>{{
                    t("analyticsPage.recentTests") || "Recent Tests"
                  }}</span>
                </div>
              </template>
              <el-table :data="recentTests" style="width: 100%" size="small">
                <el-table-column
                  :label="t('analyticsPage.project') || 'Project'"
                  min-width="150"
                >
                  <template #default="{ row }">
                    <span class="project-name">{{ row.projectName }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.date') || 'Date'"
                  width="80"
                >
                  <template #default="{ row }">
                    {{ formatDate(row.date) }}
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.students') || 'Students'"
                  width="80"
                  align="center"
                >
                  <template #default="{ row }">
                    {{ row.participants }}
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.avgScore') || 'Avg Score'"
                  width="90"
                  align="center"
                >
                  <template #default="{ row }">
                    <span :style="{ color: getScoreColor(row.avgScore) }"
                      >{{ row.avgScore }}%</span
                    >
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.passRate') || 'Pass Rate'"
                  width="90"
                  align="center"
                >
                  <template #default="{ row }">
                    <el-tag
                      :type="
                        row.passRate >= 80
                          ? 'success'
                          : row.passRate >= 60
                          ? 'warning'
                          : 'danger'
                      "
                      size="small"
                    >
                      {{ row.passRate }}%
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>

          <!-- Bottom Grid -->
          <div class="bottom-grid">
            <!-- Top Students -->
            <el-card class="leaderboard-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span
                    ><el-icon><Trophy /></el-icon>
                    {{
                      t("analyticsPage.topStudents") ||
                      "Top Performing Students"
                    }}</span
                  >
                </div>
              </template>
              <div class="leaderboard">
                <div
                  v-for="(student, index) in topStudents"
                  :key="student.id"
                  class="leaderboard-item"
                >
                  <div class="rank" :class="{ 'top-3': index < 3 }">
                    {{ index + 1 }}
                  </div>
                  <el-avatar :size="32" :icon="User" />
                  <div class="student-info">
                    <div class="student-name">{{ student.name }}</div>
                    <div class="student-tests">
                      {{ student.testsCompleted }} tests
                    </div>
                  </div>
                  <div class="student-score">{{ student.avgScore }}%</div>
                </div>
              </div>
            </el-card>

            <!-- Project Performance -->
            <el-card class="performance-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span
                    ><el-icon><DataAnalysis /></el-icon>
                    {{
                      t("analyticsPage.projectPerformance") ||
                      "Project Performance"
                    }}</span
                  >
                </div>
              </template>
              <el-table
                :data="projectPerformance"
                style="width: 100%"
                size="small"
              >
                <el-table-column
                  :label="t('analyticsPage.project') || 'Project'"
                  min-width="120"
                >
                  <template #default="{ row }">
                    <span class="project-name">{{ row.name }}</span>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.avgScore') || 'Avg Score'"
                  width="100"
                  align="center"
                >
                  <template #default="{ row }">
                    <span
                      :style="{
                        color: getScoreColor(row.avgScore),
                        fontWeight: 600,
                      }"
                      >{{ row.avgScore }}%</span
                    >
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.tests') || 'Tests'"
                  width="70"
                  align="center"
                >
                  <template #default="{ row }">
                    {{ row.tests }}
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('analyticsPage.trend') || 'Trend'"
                  width="80"
                  align="center"
                >
                  <template #default="{ row }">
                    <el-icon
                      v-if="getTrendIcon(row.trend)"
                      :style="{ color: getTrendColor(row.trend) }"
                    >
                      <component :is="getTrendIcon(row.trend)" />
                    </el-icon>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>
        </div>
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

.analytics-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

// Period Selector
.period-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);

  .period-label {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }
}

// Stats Grid
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.stat-card {
  :deep(.el-card__body) {
    display: flex;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;

    &.tests {
      background: linear-gradient(
        135deg,
        var(--el-color-primary),
        var(--el-color-primary-light-3)
      );
    }

    &.students {
      background: linear-gradient(
        135deg,
        var(--el-color-success),
        var(--el-color-success-light-3)
      );
    }

    &.score {
      background: linear-gradient(
        135deg,
        var(--el-color-warning),
        var(--el-color-warning-light-3)
      );
    }

    &.completion {
      background: linear-gradient(
        135deg,
        var(--el-color-info),
        var(--el-color-info-light-3)
      );
    }
  }

  .stat-info {
    flex: 1;

    .stat-value {
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text);
      line-height: 1.2;
    }

    .stat-label {
      font-size: 0.85rem;
      color: var(--color-text-light);
      margin-bottom: 4px;
    }

    .stat-change {
      font-size: 0.8rem;
      font-weight: 500;

      &.positive {
        color: var(--el-color-success);
      }

      &.negative {
        color: var(--el-color-danger);
      }
    }

    .stat-sub {
      font-size: 0.8rem;
      color: var(--color-text-light);
    }
  }
}

// Main Grid
.main-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-weight: 600;

  .el-icon {
    color: var(--color-primary);
  }
}

// Score Distribution Chart
.chart-card {
  .distribution-chart {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .distribution-bar {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);

    .bar-label {
      width: 50px;
      font-size: 0.85rem;
      color: var(--color-text-light);
      text-align: right;
    }

    .bar-container {
      flex: 1;
      height: 24px;
      background: var(--color-surface);
      border-radius: var(--radius-sm);
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      border-radius: var(--radius-sm);
      transition: width 0.5s ease;
    }

    .bar-value {
      width: 80px;
      font-size: 0.85rem;
      color: var(--color-text);
    }
  }
}

// Table Card
.table-card {
  .project-name {
    font-weight: 500;
  }
}

// Bottom Grid
.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xl);
}

// Leaderboard
.leaderboard-card {
  .leaderboard {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .leaderboard-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    transition: background-color var(--transition-base);

    &:hover {
      background: var(--color-surface);
    }

    .rank {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 0.85rem;
      background: var(--color-neutral);
      color: var(--color-text);

      &.top-3 {
        background: linear-gradient(135deg, #ffd700, #ffb700);
        color: #000;
      }
    }

    .student-info {
      flex: 1;

      .student-name {
        font-weight: 500;
        color: var(--color-text);
      }

      .student-tests {
        font-size: 0.8rem;
        color: var(--color-text-light);
      }
    }

    .student-score {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--el-color-success);
    }
  }
}

// Performance Card
.performance-card {
  .project-name {
    font-weight: 500;
  }
}

// Responsive
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .main-grid {
    grid-template-columns: 1fr;
  }

  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .analytics-content {
    padding: var(--spacing-md);
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .period-selector {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
