<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import ThemeToggle from "@/components/ThemeToggle.vue";
import { Plus } from "@element-plus/icons-vue";

const router = useRouter();
const authStore = useAuthStore();
const projectStore = useProjectStore();
const { t } = useI18n();

const projects = computed(() => projectStore.projects);

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    draft: "info",
    ready: "success",
    active: "warning",
    completed: "",
  };
  return types[status] || "";
};

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
          <h1>{{ t("teacher.dashboard") }}</h1>
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
          <div class="header-actions">
            <h2>{{ t("teacher.myProjects") }}</h2>
            <el-button
              type="primary"
              size="large"
              @click="router.push('/teacher/project/create')"
              :icon="Plus"
            >
              {{ t("teacher.createProject") }}
            </el-button>
          </div>

          <div class="projects-grid">
            <el-card
              v-for="project in projects"
              :key="project.id"
              class="project-card"
              shadow="hover"
            >
              <template #header>
                <div class="card-header">
                  <span class="project-title">{{ project.title }}</span>
                  <el-tag :type="getStatusType(project.status)">
                    {{ t(`status.${project.status}`) }}
                  </el-tag>
                </div>
              </template>

              <div class="project-info">
                <p class="group-name">
                  <el-icon><UserFilled /></el-icon>
                  {{ project.groupName }}
                </p>
                <p class="description">{{ project.description }}</p>

                <div class="project-stats">
                  <el-statistic
                    :title="t('teacher.studentCount')"
                    :value="project.settings.maxStudents"
                  />
                  <el-statistic
                    title="Questions"
                    :value="
                      project.settings.questionTypes.reduce(
                        (sum, q) => sum + q.count,
                        0
                      )
                    "
                  />
                </div>
              </div>

              <template #footer>
                <div class="card-actions">
                  <el-button
                    v-if="
                      project.status === 'ready' || project.status === 'active'
                    "
                    type="success"
                    @click="router.push(`/teacher/project/${project.id}/lobby`)"
                  >
                    {{ t("teacher.lobby") }}
                  </el-button>
                  <el-button
                    v-if="project.status === 'completed'"
                    type="info"
                    @click="
                      router.push(`/teacher/project/${project.id}/statistics`)
                    "
                  >
                    {{ t("teacher.viewStatistics") }}
                  </el-button>
                  <el-button
                    @click="router.push(`/teacher/project/${project.id}`)"
                  >
                    {{ t("common.edit") }}
                  </el-button>
                  <el-button
                    type="primary"
                    link
                    @click="router.push(`/teacher/project/${project.id}/edit`)"
                  >
                    {{ t("teacher.editQuestions") }}
                  </el-button>
                </div>
              </template>
            </el-card>

            <el-empty
              v-if="projects.length === 0"
              description="No projects yet. Create your first project!"
            />
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

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--spacing-lg);
}

.project-card {
  transition: transform var(--transition-base);

  &:hover {
    transform: translateY(-4px);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .project-title {
      font-weight: 600;
      font-size: 1.1rem;
    }
  }

  .project-info {
    .group-name {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      color: var(--color-primary);
      font-weight: 500;
      margin-bottom: var(--spacing-md);
    }

    .description {
      color: var(--color-text-light);
      margin-bottom: var(--spacing-lg);
      min-height: 40px;
    }

    .project-stats {
      display: flex;
      gap: var(--spacing-xl);
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--color-neutral);
    }
  }

  .card-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }
}

@media (max-width: 768px) {
  .projects-grid {
    grid-template-columns: 1fr;
  }

  .header-actions {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }
}
</style>
