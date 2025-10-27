<script setup lang="ts">
import { ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const projectId = route.params.id as string;
const project = computed(() => projectStore.getProject(projectId));

// Mock completed tests data
const completedTests = ref([
  {
    id: "t1",
    studentName: "Alice Johnson",
    email: "alice@uni.edu",
    score: 85,
    maxScore: 100,
    completedAt: new Date("2025-10-26T14:30:00"),
    timeSpent: 45, // minutes
  },
  {
    id: "t2",
    studentName: "Bob Smith",
    email: "bob@uni.edu",
    score: 72,
    maxScore: 100,
    completedAt: new Date("2025-10-26T14:35:00"),
    timeSpent: 52,
  },
  {
    id: "t3",
    studentName: "Carol Williams",
    email: "carol@uni.edu",
    score: 95,
    maxScore: 100,
    completedAt: new Date("2025-10-26T14:28:00"),
    timeSpent: 38,
  },
  {
    id: "t4",
    studentName: "David Brown",
    email: "david@uni.edu",
    score: 68,
    maxScore: 100,
    completedAt: new Date("2025-10-26T15:10:00"),
    timeSpent: 60,
  },
]);

const statistics = computed(() => {
  const scores = completedTests.value.map((t) => (t.score / t.maxScore) * 100);
  return {
    totalStudents: completedTests.value.length,
    averageScore: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
    highestScore: Math.max(...scores),
    lowestScore: Math.min(...scores),
    passRate: Math.round(
      (scores.filter((s) => s >= 60).length / scores.length) * 100
    ),
  };
});

const getScoreType = (score: number, maxScore: number) => {
  const percentage = (score / maxScore) * 100;
  if (percentage >= 90) return "success";
  if (percentage >= 70) return "primary";
  if (percentage >= 60) return "warning";
  return "danger";
};

const formatDuration = (minutes: number) => {
  return `${minutes} min`;
};
</script>

<template>
  <div class="statistics-view">
    <el-container>
      <el-header>
        <div class="header-content">
          <div>
            <h1>{{ project?.title }} - {{ t("teacher.viewStatistics") }}</h1>
            <p class="subtitle">{{ project?.groupName }}</p>
          </div>
          <el-button @click="router.push('/teacher')">
            {{ t("common.back") }}
          </el-button>
        </div>
      </el-header>

      <el-main>
        <!-- Statistics overview -->
        <el-row :gutter="20" class="stats-row">
          <el-col :xs="24" :sm="12" :md="8" :lg="4">
            <el-card shadow="hover">
              <el-statistic
                :title="t('teacher.studentCount')"
                :value="statistics.totalStudents"
              >
                <template #prefix>
                  <el-icon color="#3b82f6"><User /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8" :lg="5">
            <el-card shadow="hover">
              <el-statistic
                title="Average Score"
                :value="statistics.averageScore"
                suffix="%"
              >
                <template #prefix>
                  <el-icon color="#10b981"><TrophyBase /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8" :lg="5">
            <el-card shadow="hover">
              <el-statistic
                title="Highest Score"
                :value="statistics.highestScore"
                suffix="%"
              >
                <template #prefix>
                  <el-icon color="#f59e0b"><StarFilled /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8" :lg="5">
            <el-card shadow="hover">
              <el-statistic
                title="Lowest Score"
                :value="statistics.lowestScore"
                suffix="%"
              >
                <template #prefix>
                  <el-icon color="#ef4444"><Warning /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>

          <el-col :xs="24" :sm="12" :md="8" :lg="5">
            <el-card shadow="hover">
              <el-statistic
                title="Pass Rate"
                :value="statistics.passRate"
                suffix="%"
              >
                <template #prefix>
                  <el-icon color="#10b981"><CircleCheck /></el-icon>
                </template>
              </el-statistic>
            </el-card>
          </el-col>
        </el-row>

        <!-- Detailed results table -->
        <el-card style="margin-top: 24px">
          <template #header>
            <h2>{{ t("teacher.studentResults") }}</h2>
          </template>

          <el-table :data="completedTests" stripe style="width: 100%">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="expand-content">
                  <h4>Test Details</h4>
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="Email">{{
                      row.email
                    }}</el-descriptions-item>
                    <el-descriptions-item label="Time Spent">{{
                      formatDuration(row.timeSpent)
                    }}</el-descriptions-item>
                    <el-descriptions-item label="Completed At">
                      {{ row.completedAt.toLocaleString() }}
                    </el-descriptions-item>
                    <el-descriptions-item label="Percentage">
                      {{ Math.round((row.score / row.maxScore) * 100) }}%
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="studentName" label="Student Name" sortable />

            <el-table-column
              label="Score"
              sortable
              :sort-method="(a, b) => a.score - b.score"
            >
              <template #default="{ row }">
                <el-tag
                  :type="getScoreType(row.score, row.maxScore)"
                  size="large"
                >
                  {{ row.score }} / {{ row.maxScore }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column label="Percentage" sortable>
              <template #default="{ row }">
                <el-progress
                  :percentage="Math.round((row.score / row.maxScore) * 100)"
                  :status="
                    row.score / row.maxScore >= 0.6 ? 'success' : 'exception'
                  "
                />
              </template>
            </el-table-column>

            <el-table-column prop="timeSpent" label="Time" sortable>
              <template #default="{ row }">
                {{ formatDuration(row.timeSpent) }}
              </template>
            </el-table-column>

            <el-table-column prop="completedAt" label="Completed" sortable>
              <template #default="{ row }">
                {{ row.completedAt.toLocaleTimeString() }}
              </template>
            </el-table-column>

            <el-table-column label="Actions" width="150">
              <template #default="{ row }">
                <el-button type="primary" size="small" link>
                  View Details
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- Chart placeholder -->
        <el-row :gutter="20" style="margin-top: 24px">
          <el-col :span="12">
            <el-card>
              <template #header>
                <h3>Score Distribution</h3>
              </template>
              <div class="chart-placeholder">
                <el-empty
                  description="Chart visualization will be here"
                  :image-size="100"
                />
              </div>
            </el-card>
          </el-col>

          <el-col :span="12">
            <el-card>
              <template #header>
                <h3>Time vs Score Analysis</h3>
              </template>
              <div class="chart-placeholder">
                <el-empty
                  description="Chart visualization will be here"
                  :image-size="100"
                />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped lang="scss">
.statistics-view {
  min-height: 100vh;
  background-color: var(--color-surface);
}

.el-header {
  background: var(--color-background);
  box-shadow: var(--shadow-sm);
  display: flex;
  align-items: center;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;

    h1 {
      margin: 0;
      color: var(--color-dark);
    }

    .subtitle {
      color: var(--color-primary);
      margin: 0;
      font-weight: 500;
    }
  }
}

.el-main {
  padding: var(--spacing-xl);
}

.stats-row {
  margin-bottom: var(--spacing-xl);

  .el-col {
    margin-bottom: var(--spacing-md);
  }
}

.expand-content {
  padding: var(--spacing-lg);

  h4 {
    margin-bottom: var(--spacing-md);
    color: var(--color-dark);
  }
}

.chart-placeholder {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

@media (max-width: 768px) {
  .el-main {
    padding: var(--spacing-md);
  }
}
</style>
