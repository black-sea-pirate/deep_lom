<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import { Message, Clock, Refresh, User } from "@element-plus/icons-vue";
import {
  projectService,
  type ProjectStudent,
} from "@/services/project.service";
import {
  participantService,
  type Participant,
} from "@/services/participant.service";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const projectId = route.params.id as string;
const project = computed(() => projectStore.getProject(projectId));

// Real students data from backend
const allowedStudents = ref<ProjectStudent[]>([]);
const loading = ref(false);
const addingStudent = ref(false);

// Confirmed contacts from teacher's database
const confirmedContacts = ref<Participant[]>([]);
const selectedStudentEmail = ref<string>("");
const loadingContacts = ref(false);

const showScheduleDialog = ref(false);
const scheduleForm = ref({
  startTime: new Date(),
  endTime: new Date(Date.now() + 5 * 60 * 60 * 1000), // +5 hours
});

// Load project and students on mount
onMounted(async () => {
  await loadProject();
  await Promise.all([loadStudents(), loadConfirmedContacts()]);
});

const loadProject = async () => {
  try {
    await projectStore.fetchProject(projectId);
  } catch (error) {
    console.error("Error loading project:", error);
    ElMessage.error("Failed to load project");
  }
};

const loadStudents = async () => {
  loading.value = true;
  try {
    allowedStudents.value = await projectService.getProjectStudents(projectId);
  } catch (error) {
    console.error("Error loading students:", error);
    // Initialize empty if endpoint fails
    allowedStudents.value = [];
  } finally {
    loading.value = false;
  }
};

const loadConfirmedContacts = async () => {
  loadingContacts.value = true;
  try {
    confirmedContacts.value =
      await participantService.getConfirmedParticipants();
  } catch (error) {
    console.error("Error loading confirmed contacts:", error);
    confirmedContacts.value = [];
  } finally {
    loadingContacts.value = false;
  }
};

// Available contacts (not already in project)
const availableContacts = computed(() => {
  const allowedEmails = allowedStudents.value.map((s) => s.email.toLowerCase());
  return confirmedContacts.value.filter(
    (contact) => !allowedEmails.includes(contact.email.toLowerCase())
  );
});

const handleAddStudent = async () => {
  const email = selectedStudentEmail.value?.trim().toLowerCase();

  if (!email) {
    ElMessage.warning(t("teacher.selectStudent") || "Please select a student");
    return;
  }

  const allowedEmails = allowedStudents.value.map((s) => s.email.toLowerCase());

  if (allowedEmails.includes(email)) {
    ElMessage.warning("Student already added to this project");
    return;
  }

  addingStudent.value = true;
  try {
    const result = await projectService.addStudentToProject(projectId, email);
    allowedStudents.value = result.students;
    ElMessage.success("Student added successfully");
    selectedStudentEmail.value = "";
  } catch (error: any) {
    console.error("Error adding student:", error);
    ElMessage.error(error.response?.data?.detail || "Failed to add student");
  } finally {
    addingStudent.value = false;
  }
};

const handleRemoveStudent = async (email: string) => {
  try {
    await ElMessageBox.confirm(
      `Remove ${email} from this project?`,
      "Confirm Removal",
      {
        confirmButtonText: "Remove",
        cancelButtonText: "Cancel",
        type: "warning",
      }
    );

    const result = await projectService.removeStudentFromProject(
      projectId,
      email
    );
    allowedStudents.value = result.students;
    ElMessage.success("Student removed from project");
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("Error removing student:", error);
      ElMessage.error(
        error.response?.data?.detail || "Failed to remove student"
      );
    }
  }
};

// Status helpers for translation
const getStatusTagType = (
  status?: string
): "success" | "warning" | "danger" | "info" => {
  switch (status) {
    case "confirmed":
      return "success";
    case "pending":
      return "warning";
    case "rejected":
      return "danger";
    default:
      return "info";
  }
};

const getStatusLabel = (status?: string): string => {
  switch (status) {
    case "confirmed":
      return t("participantsPage.confirmed") || "Confirmed";
    case "pending":
      return t("participantsPage.pending") || "Pending";
    case "rejected":
      return t("participantsPage.rejected") || "Rejected";
    default:
      return t("participantsPage.notLinked") || "Not linked";
  }
};

const handleScheduleTest = async () => {
  if (!project.value) return;

  try {
    await projectStore.updateProject(projectId, {
      startTime: scheduleForm.value.startTime.toISOString(),
      endTime: scheduleForm.value.endTime.toISOString(),
      status: "ready",
    });

    showScheduleDialog.value = false;
    ElMessage.success("Test scheduled successfully!");
  } catch (error) {
    console.error("Error scheduling test:", error);
    ElMessage.error("Failed to schedule test");
  }
};

const handleActivateNow = async () => {
  if (!project.value) return;

  if (allowedStudents.value.length === 0) {
    ElMessage.warning(
      t("teacher.addStudentFirst") ||
        "Add at least one student before starting the test"
    );
    return;
  }

  const totalTime = project.value.settings?.totalTime || 60;

  try {
    await projectStore.updateProject(projectId, {
      startTime: new Date().toISOString(),
      endTime: new Date(Date.now() + totalTime * 60 * 1000).toISOString(),
      status: "active",
    });

    ElMessage.success(
      t("teacher.testStarted") || "Test started! All students can now begin."
    );
  } catch (error) {
    console.error("Error activating test:", error);
    ElMessage.error(t("teacher.testStartFailed") || "Failed to start test");
  }
};
</script>

<template>
  <div class="lobby-view">
    <el-container>
      <el-header>
        <div class="header-content">
          <div>
            <h1>{{ project?.title }} - {{ t("teacher.lobby") }}</h1>
            <p class="subtitle">{{ project?.groupName }}</p>
          </div>
          <el-button @click="router.push('/teacher')">
            {{ t("common.back") }}
          </el-button>
        </div>
      </el-header>

      <el-main>
        <el-row :gutter="20">
          <el-col :xs="24" :lg="16">
            <el-card>
              <template #header>
                <div class="flex items-center justify-between">
                  <h2>
                    {{ t("teacher.waitingStudents") }} ({{
                      allowedStudents.length
                    }})
                  </h2>
                  <el-button
                    :icon="Refresh"
                    circle
                    size="small"
                    @click="loadStudents"
                    :loading="loading"
                  />
                </div>
              </template>

              <div class="add-student-section">
                <el-select
                  v-model="selectedStudentEmail"
                  filterable
                  :placeholder="
                    t('teacher.selectStudent') || 'Select student from contacts'
                  "
                  style="width: 350px; margin-right: 12px"
                  :loading="loadingContacts"
                  :no-data-text="
                    t('teacher.noConfirmedContacts') ||
                    'No confirmed contacts available'
                  "
                >
                  <el-option
                    v-for="contact in availableContacts"
                    :key="contact.id"
                    :label="`${contact.firstName} ${contact.lastName} (${contact.email})`"
                    :value="contact.email"
                  >
                    <div class="contact-option">
                      <el-icon><User /></el-icon>
                      <span class="contact-name"
                        >{{ contact.firstName }} {{ contact.lastName }}</span
                      >
                      <span class="contact-email">{{ contact.email }}</span>
                    </div>
                  </el-option>
                </el-select>
                <el-button
                  type="primary"
                  @click="handleAddStudent"
                  :loading="addingStudent"
                  :disabled="!selectedStudentEmail"
                >
                  {{ t("teacher.addStudent") }}
                </el-button>
              </div>

              <el-alert
                v-if="confirmedContacts.length === 0 && !loadingContacts"
                :title="t('teacher.noContactsTitle') || 'No confirmed contacts'"
                type="info"
                :description="
                  t('teacher.noContactsDesc') ||
                  'Add students to your contacts in Participants section and wait for them to confirm.'
                "
                show-icon
                :closable="false"
                style="margin-bottom: 16px"
              />

              <el-divider />

              <el-table
                :data="allowedStudents"
                style="width: 100%"
                v-loading="loading"
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column :label="t('common.name')">
                  <template #default="{ row }">
                    <span class="student-name">
                      {{ row.firstName || "" }} {{ row.lastName || "" }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="email" :label="t('common.email')" />
                <el-table-column :label="t('common.status')" width="140">
                  <template #default="{ row }">
                    <el-tag
                      size="small"
                      :type="getStatusTagType(row.confirmationStatus)"
                    >
                      {{ getStatusLabel(row.confirmationStatus) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('common.actions')" width="120">
                  <template #default="{ row }">
                    <el-button
                      type="danger"
                      size="small"
                      @click="handleRemoveStudent(row.email)"
                    >
                      {{ t("common.delete") }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <el-empty
                v-if="!loading && allowedStudents.length === 0"
                description="No students added yet"
              />
            </el-card>
          </el-col>

          <el-col :xs="24" :lg="8">
            <el-card class="schedule-card">
              <template #header>
                <h3>{{ t("teacher.testSchedule") }}</h3>
              </template>

              <div
                class="schedule-info"
                v-if="project?.startTime && project?.endTime"
              >
                <div class="info-row">
                  <el-icon color="#10b981"><Clock /></el-icon>
                  <div>
                    <div class="label">{{ t("teacher.availableFrom") }}</div>
                    <div class="value">
                      {{ new Date(project.startTime).toLocaleString() }}
                    </div>
                  </div>
                </div>
                <div class="info-row">
                  <el-icon color="#ef4444"><Clock /></el-icon>
                  <div>
                    <div class="label">{{ t("teacher.availableUntil") }}</div>
                    <div class="value">
                      {{ new Date(project.endTime).toLocaleString() }}
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="no-schedule">
                <el-empty
                  description="Test not scheduled yet"
                  :image-size="80"
                />
              </div>

              <el-divider />

              <div class="actions">
                <el-button
                  type="primary"
                  size="large"
                  style="width: 100%"
                  @click="showScheduleDialog = true"
                >
                  {{ t("teacher.scheduleTest") }}
                </el-button>

                <el-button
                  type="success"
                  size="large"
                  style="width: 100%; margin-top: 12px"
                  @click="handleActivateNow"
                  :disabled="allowedStudents.length === 0"
                >
                  {{ t("teacher.startTest") }}
                </el-button>
              </div>
            </el-card>

            <el-card style="margin-top: 20px">
              <template #header>
                <h3>{{ t("teacher.projectSettings") }}</h3>
              </template>

              <el-descriptions :column="1" border>
                <el-descriptions-item :label="t('teacher.totalTime')">
                  {{ project?.settings?.totalTime || 60 }} min
                </el-descriptions-item>
                <el-descriptions-item :label="t('teacher.maxStudents')">
                  {{
                    project?.settings?.maxStudents ||
                    allowedStudents.length ||
                    "-"
                  }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('teacher.questionCount')">
                  {{
                    project?.settings?.questionTypes?.reduce(
                      (sum: number, q: any) => sum + q.count,
                      0
                    ) ||
                    project?.tests?.[0]?.questions?.length ||
                    "-"
                  }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>

    <el-dialog
      v-model="showScheduleDialog"
      :title="t('teacher.scheduleTest')"
      width="500px"
    >
      <el-form :model="scheduleForm" label-position="top">
        <el-form-item :label="t('teacher.startTime')">
          <el-date-picker
            v-model="scheduleForm.startTime"
            type="datetime"
            :placeholder="t('teacher.startTime')"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="t('teacher.endTime')">
          <el-date-picker
            v-model="scheduleForm.endTime"
            type="datetime"
            :placeholder="t('teacher.endTime')"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showScheduleDialog = false">{{
          t("common.cancel")
        }}</el-button>
        <el-button type="primary" @click="handleScheduleTest">{{
          t("common.save")
        }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.lobby-view {
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

.add-student-section {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.schedule-card {
  .schedule-info {
    .info-row {
      display: flex;
      gap: var(--spacing-md);
      margin-bottom: var(--spacing-lg);

      .label {
        font-size: 0.875rem;
        color: var(--color-text-light);
      }

      .value {
        font-weight: 600;
        color: var(--color-dark);
      }
    }
  }

  .no-schedule {
    padding: var(--spacing-xl) 0;
  }
}

.contact-option {
  display: flex;
  align-items: center;
  gap: 8px;

  .contact-name {
    font-weight: 500;
  }

  .contact-email {
    color: var(--color-text-light);
    font-size: 0.85em;
    margin-left: auto;
  }
}

@media (max-width: 768px) {
  .add-student-section {
    flex-direction: column;
    align-items: stretch;

    .el-select {
      width: 100% !important;
      margin-right: 0 !important;
      margin-bottom: var(--spacing-md);
    }
  }
}
</style>
