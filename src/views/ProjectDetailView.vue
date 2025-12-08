<script setup lang="ts">
/**
 * ProjectDetailView
 *
 * Shows detailed project information:
 * - Project info (title, description, group)
 * - Linked materials
 * - Settings (time limits, question types)
 * - Status and progress
 * - Actions (edit, activate, delete)
 */
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import type { Project } from "@/types";
import {
  Back,
  Edit,
  Delete,
  Document,
  Timer,
  User,
  Setting,
  VideoPlay,
  CircleCheck,
} from "@element-plus/icons-vue";
import { projectService } from "@/services/project.service";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const loading = ref(true);
const project = ref<Project | null>(null);
const loadError = ref<string | null>(null);

// Edit dialog state
const editDialogVisible = ref(false);
const editLoading = ref(false);
const editForm = ref({
  title: "",
  groupName: "",
  description: "",
  totalTime: 60,
  timePerQuestion: 120,
  maxStudents: 30,
});

const projectId = computed(() => route.params.id as string);

// Load project data
const loadProject = async () => {
  loading.value = true;
  loadError.value = null;

  try {
    // Validate projectId
    if (!projectId.value) {
      throw new Error("Project ID is missing");
    }

    project.value = await projectStore.fetchProject(projectId.value);

    if (!project.value) {
      throw new Error("Project not found");
    }
  } catch (error: any) {
    console.error("Failed to load project:", error);
    loadError.value =
      error.response?.data?.detail || error.message || "Failed to load project";
    ElMessage.error(loadError.value || "Failed to load project");
    // Delay redirect to show error message
    setTimeout(() => {
      router.push("/teacher");
    }, 1500);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadProject();
});

// Computed
const statusType = computed(() => {
  switch (project.value?.status) {
    case "draft":
      return "info";
    case "ready":
      return "warning";
    case "active":
      return "success";
    case "completed":
      return "primary";
    case "generating":
      return "warning";
    default:
      return "info";
  }
});

const statusLabel = computed(() => {
  const status = project.value?.status;
  const labels: Record<string, string> = {
    draft: t("project.statusDraft") || "Draft",
    ready: t("project.statusReady") || "Ready",
    active: t("project.statusActive") || "Active",
    completed: t("project.statusCompleted") || "Completed",
    generating: t("project.statusGenerating") || "Generating",
    vectorizing: t("project.statusVectorizing") || "Vectorizing",
  };
  return labels[status || "draft"] || status;
});

const totalQuestions = computed(() => {
  if (!project.value?.settings?.questionTypes) return 0;
  return project.value.settings.questionTypes.reduce(
    (sum, qt) => sum + qt.count,
    0
  );
});

const formatDate = (date: Date | string | undefined): string => {
  if (!date) return "-";
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatDuration = (minutes: number): string => {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
};

// Actions
const handleEdit = () => {
  if (!project.value) return;

  // Populate edit form with current values
  editForm.value = {
    title: project.value.title || "",
    groupName: project.value.groupName || "",
    description: project.value.description || "",
    totalTime: project.value.settings?.totalTime || 60,
    timePerQuestion: project.value.settings?.timePerQuestion || 120,
    maxStudents: project.value.settings?.maxStudents || 30,
  };

  editDialogVisible.value = true;
};

const handleSaveEdit = async () => {
  if (!project.value) return;

  editLoading.value = true;
  try {
    // Update project basic info
    await projectService.updateProject(projectId.value, {
      title: editForm.value.title,
      groupName: editForm.value.groupName,
      description: editForm.value.description,
    });

    // Update project settings
    await projectService.configureSettings(projectId.value, {
      totalTime: editForm.value.totalTime,
      timePerQuestion: editForm.value.timePerQuestion,
      maxStudents: editForm.value.maxStudents,
      questionTypes: project.value.settings?.questionTypes || [],
    });

    ElMessage.success(t("project.updated") || "Project updated successfully");
    editDialogVisible.value = false;
    await loadProject();
  } catch (error: any) {
    ElMessage.error(
      error.response?.data?.detail ||
        error.message ||
        "Failed to update project"
    );
  } finally {
    editLoading.value = false;
  }
};

const handleEditQuestions = () => {
  router.push(`/teacher/project/${projectId.value}/edit`);
};

const handleActivate = async () => {
  try {
    await ElMessageBox.confirm(
      t("project.confirmActivate") ||
        "Activate this project? Students will be able to take the test.",
      t("project.activate") || "Activate Project",
      {
        confirmButtonText: t("common.confirm") || "Confirm",
        cancelButtonText: t("common.cancel") || "Cancel",
        type: "warning",
      }
    );

    await projectStore.activateProject(projectId.value);
    ElMessage.success(t("project.activated") || "Project activated");
    await loadProject();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "Failed to activate project");
    }
  }
};

const handleComplete = async () => {
  try {
    await ElMessageBox.confirm(
      t("project.confirmComplete") ||
        "Complete this project? No more students will be able to take the test.",
      t("project.complete") || "Complete Project",
      {
        confirmButtonText: t("common.confirm") || "Confirm",
        cancelButtonText: t("common.cancel") || "Cancel",
        type: "warning",
      }
    );

    await projectStore.completeProject(projectId.value);
    ElMessage.success(t("project.completed") || "Project completed");
    await loadProject();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "Failed to complete project");
    }
  }
};

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(
      t("project.confirmDelete") ||
        "Delete this project? This action cannot be undone.",
      t("common.delete") || "Delete",
      {
        confirmButtonText: t("common.delete") || "Delete",
        cancelButtonText: t("common.cancel") || "Cancel",
        type: "error",
      }
    );

    await projectStore.deleteProject(projectId.value);
    ElMessage.success(t("project.deleted") || "Project deleted");
    router.push("/teacher");
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "Failed to delete project");
    }
  }
};

const goBack = () => {
  router.push("/teacher");
};
</script>

<template>
  <div class="project-detail-view" v-loading="loading">
    <!-- Error State -->
    <div v-if="loadError && !loading" class="error-state">
      <el-result
        icon="error"
        :title="t('common.error') || 'Error'"
        :sub-title="loadError"
      >
        <template #extra>
          <el-button type="primary" @click="goBack">
            {{ t("common.backToDashboard") || "Back to Dashboard" }}
          </el-button>
          <el-button @click="loadProject">
            {{ t("common.retry") || "Retry" }}
          </el-button>
        </template>
      </el-result>
    </div>

    <!-- Main Content -->
    <template v-else-if="!loadError">
      <!-- Header -->
      <div class="page-header">
        <el-button :icon="Back" @click="goBack">
          {{ t("common.back") || "Back" }}
        </el-button>
        <div class="header-actions" v-if="project">
          <el-button :icon="Edit" @click="handleEdit">
            {{ t("common.edit") || "Edit" }}
          </el-button>
          <el-button type="primary" :icon="Edit" @click="handleEditQuestions">
            {{ t("project.editQuestions") || "Edit Questions" }}
          </el-button>
          <el-button
            v-if="project.status === 'ready'"
            type="success"
            :icon="VideoPlay"
            @click="handleActivate"
          >
            {{ t("project.activate") || "Activate" }}
          </el-button>
          <el-button
            v-if="project.status === 'active'"
            type="warning"
            :icon="CircleCheck"
            @click="handleComplete"
          >
            {{ t("project.complete") || "Complete" }}
          </el-button>
          <el-button type="danger" :icon="Delete" @click="handleDelete">
            {{ t("common.delete") || "Delete" }}
          </el-button>
        </div>
      </div>

      <div v-if="project" class="project-content">
        <!-- Project Info Card -->
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <h2>{{ project.title }}</h2>
              <el-tag :type="statusType" size="large">{{ statusLabel }}</el-tag>
            </div>
          </template>

          <div class="info-grid">
            <div class="info-item">
              <label>{{ t("teacher.groupName") || "Group" }}</label>
              <span>{{ project.groupName }}</span>
            </div>
            <div class="info-item">
              <label>{{ t("project.createdAt") || "Created" }}</label>
              <span>{{ formatDate(project.createdAt) }}</span>
            </div>
            <div class="info-item full-width" v-if="project.description">
              <label>{{ t("teacher.description") || "Description" }}</label>
              <p>{{ project.description }}</p>
            </div>
          </div>
        </el-card>

        <!-- Settings Card -->
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="20"><Setting /></el-icon>
              <h3>{{ t("wizard.configureSettings") || "Settings" }}</h3>
            </div>
          </template>

          <div class="settings-grid">
            <div class="setting-item">
              <el-icon :size="24"><Timer /></el-icon>
              <div class="setting-info">
                <span class="setting-value">{{
                  formatDuration(project.settings?.totalTime || 60)
                }}</span>
                <span class="setting-label">{{
                  t("teacher.totalTime") || "Total Time"
                }}</span>
              </div>
            </div>
            <div class="setting-item">
              <el-icon :size="24"><Timer /></el-icon>
              <div class="setting-info">
                <span class="setting-value"
                  >{{ project.settings?.timePerQuestion || 120 }}s</span
                >
                <span class="setting-label">{{
                  t("teacher.timePerQuestion") || "Per Question"
                }}</span>
              </div>
            </div>
            <div class="setting-item">
              <el-icon :size="24"><User /></el-icon>
              <div class="setting-info">
                <span class="setting-value">{{
                  project.settings?.maxStudents || 30
                }}</span>
                <span class="setting-label">{{
                  t("teacher.maxStudents") || "Max Students"
                }}</span>
              </div>
            </div>
            <div class="setting-item">
              <el-icon :size="24"><Document /></el-icon>
              <div class="setting-info">
                <span class="setting-value">{{ totalQuestions }}</span>
                <span class="setting-label">{{
                  t("project.questions") || "Questions"
                }}</span>
              </div>
            </div>
          </div>

          <!-- Question Types -->
          <div
            v-if="project.settings?.questionTypes?.length"
            class="question-types"
          >
            <h4>{{ t("teacher.questionTypes") || "Question Types" }}</h4>
            <div class="types-list">
              <el-tag
                v-for="(qt, index) in project.settings.questionTypes"
                :key="index"
                type="info"
                size="large"
              >
                {{ qt.type }}: {{ qt.count }}
              </el-tag>
            </div>
          </div>
        </el-card>

        <!-- Materials Card -->
        <el-card class="materials-card">
          <template #header>
            <div class="card-header">
              <el-icon :size="20"><Document /></el-icon>
              <h3>{{ t("wizard.selectMaterials") || "Materials" }}</h3>
              <el-tag type="info"
                >{{ project.materials?.length || 0 }} files</el-tag
              >
            </div>
          </template>

          <div v-if="project.materials?.length" class="materials-list">
            <div
              v-for="material in project.materials"
              :key="material.id"
              class="material-item"
            >
              <el-icon :size="20"><Document /></el-icon>
              <span class="material-name">{{
                material.originalName || material.fileName
              }}</span>
              <span class="material-type">{{ material.fileType }}</span>
            </div>
          </div>
          <el-empty
            v-else
            :description="t('project.noMaterials') || 'No materials linked'"
          />
        </el-card>

        <!-- Schedule Card (if set) -->
        <el-card
          v-if="project.startTime || project.endTime"
          class="schedule-card"
        >
          <template #header>
            <div class="card-header">
              <el-icon :size="20"><Timer /></el-icon>
              <h3>{{ t("project.schedule") || "Schedule" }}</h3>
            </div>
          </template>

          <div class="schedule-grid">
            <div class="schedule-item" v-if="project.startTime">
              <label>{{ t("project.startTime") || "Start Time" }}</label>
              <span>{{ formatDate(project.startTime) }}</span>
            </div>
            <div class="schedule-item" v-if="project.endTime">
              <label>{{ t("project.endTime") || "End Time" }}</label>
              <span>{{ formatDate(project.endTime) }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </template>

    <!-- Edit Project Dialog -->
    <el-dialog
      v-model="editDialogVisible"
      :title="t('project.editProject') || 'Edit Project'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="editForm" label-position="top">
        <el-form-item
          :label="t('teacher.projectTitle') || 'Project Title'"
          required
        >
          <el-input v-model="editForm.title" size="large" />
        </el-form-item>

        <el-form-item :label="t('teacher.groupName') || 'Group Name'">
          <el-input v-model="editForm.groupName" size="large" />
        </el-form-item>

        <el-form-item :label="t('teacher.description') || 'Description'">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>

        <el-divider />

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="t('teacher.totalTime') || 'Total Time (min)'">
              <el-input-number
                v-model="editForm.totalTime"
                :min="10"
                :max="300"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item
              :label="t('teacher.timePerQuestion') || 'Time Per Question (sec)'"
            >
              <el-input-number
                v-model="editForm.timePerQuestion"
                :min="30"
                :max="600"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="t('teacher.maxStudents') || 'Maximum Students'">
          <el-slider
            v-model="editForm.maxStudents"
            :min="1"
            :max="100"
            show-input
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">
          {{ t("common.cancel") || "Cancel" }}
        </el-button>
        <el-button
          type="primary"
          :loading="editLoading"
          @click="handleSaveEdit"
        >
          {{ t("common.save") || "Save" }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.project-detail-view {
  min-height: 100vh;
  background: var(--color-surface);
  padding: var(--spacing-xl);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
  gap: var(--spacing-md);

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }
}

.project-content {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);

  h2,
  h3 {
    margin: 0;
    flex: 1;
  }
}

.info-card {
  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-lg);
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);

    &.full-width {
      grid-column: 1 / -1;
    }

    label {
      font-size: 0.85rem;
      color: var(--color-text-light);
      font-weight: 500;
    }

    span,
    p {
      font-size: 1rem;
      color: var(--color-text);
      margin: 0;
    }
  }
}

.settings-card {
  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
  }

  .setting-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--color-surface);
    border-radius: var(--radius-md);

    .el-icon {
      color: var(--color-primary);
    }

    .setting-info {
      display: flex;
      flex-direction: column;

      .setting-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--color-text);
      }

      .setting-label {
        font-size: 0.8rem;
        color: var(--color-text-light);
      }
    }
  }

  .question-types {
    border-top: 1px solid var(--color-border);
    padding-top: var(--spacing-lg);

    h4 {
      margin: 0 0 var(--spacing-md);
      color: var(--color-text-light);
      font-size: 0.9rem;
    }

    .types-list {
      display: flex;
      flex-wrap: wrap;
      gap: var(--spacing-sm);
    }
  }
}

.materials-card {
  .materials-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .material-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-surface);
    border-radius: var(--radius-sm);

    .el-icon {
      color: var(--color-primary);
    }

    .material-name {
      flex: 1;
      font-weight: 500;
    }

    .material-type {
      font-size: 0.8rem;
      color: var(--color-text-light);
    }
  }
}

.schedule-card {
  .schedule-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--spacing-lg);
  }

  .schedule-item {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);

    label {
      font-size: 0.85rem;
      color: var(--color-text-light);
    }

    span {
      font-size: 1rem;
      font-weight: 500;
    }
  }
}

@media (max-width: 768px) {
  .project-detail-view {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
