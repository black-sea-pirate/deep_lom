<script setup lang="ts">
import { ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { Message, Clock } from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const projectId = route.params.id as string;
const project = computed(() => projectStore.getProject(projectId));

// Mock students data
const waitingStudents = ref([
  {
    id: "1",
    firstName: "Alice",
    lastName: "Johnson",
    email: "alice@uni.edu",
    status: "ready",
  },
  {
    id: "2",
    firstName: "Bob",
    lastName: "Smith",
    email: "bob@uni.edu",
    status: "waiting",
  },
  {
    id: "3",
    firstName: "Carol",
    lastName: "Williams",
    email: "carol@uni.edu",
    status: "ready",
  },
]);

const newStudentEmail = ref("");
const showScheduleDialog = ref(false);
const scheduleForm = ref({
  startTime: new Date(),
  endTime: new Date(Date.now() + 5 * 60 * 60 * 1000), // +5 hours
});

const handleAddStudent = () => {
  if (!newStudentEmail.value) {
    ElMessage.warning(t("teacher.studentEmail") + " required");
    return;
  }

  const exists = waitingStudents.value.some(
    (s) => s.email === newStudentEmail.value
  );
  if (exists) {
    ElMessage.warning("Student already in lobby");
    return;
  }

  waitingStudents.value.push({
    id: Date.now().toString(),
    firstName: "New",
    lastName: "Student",
    email: newStudentEmail.value,
    status: "waiting",
  });

  ElMessage.success("Student added successfully");
  newStudentEmail.value = "";
};

const handleRemoveStudent = (studentId: string) => {
  waitingStudents.value = waitingStudents.value.filter(
    (s) => s.id !== studentId
  );
  ElMessage.success("Student removed from lobby");
};

const handleStartTest = () => {
  ElMessage.success("Test started! All students can now begin.");
  if (project.value) {
    projectStore.updateProject(projectId, { status: "active" });
  }
};

const handleScheduleTest = async () => {
  if (!project.value) return;

  await projectStore.updateProject(projectId, {
    startTime: scheduleForm.value.startTime,
    endTime: scheduleForm.value.endTime,
    status: "ready",
  });

  showScheduleDialog.value = false;
  ElMessage.success("Test scheduled successfully!");
};

const handleActivateNow = async () => {
  if (!project.value) return;

  await projectStore.updateProject(projectId, {
    startTime: new Date(),
    endTime: new Date(
      Date.now() + project.value.settings.totalTime * 60 * 1000
    ),
    status: "active",
  });

  ElMessage.success("Test activated!");
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
                <h2>
                  {{ t("teacher.waitingStudents") }} ({{
                    waitingStudents.length
                  }})
                </h2>
              </template>

              <div class="add-student-section">
                <el-input
                  v-model="newStudentEmail"
                  :placeholder="t('teacher.studentEmail')"
                  style="width: 300px; margin-right: 12px"
                >
                  <template #prefix>
                    <el-icon><Message /></el-icon>
                  </template>
                </el-input>
                <el-button type="primary" @click="handleAddStudent">
                  {{ t("teacher.addStudent") }}
                </el-button>
              </div>

              <el-divider />

              <el-table :data="waitingStudents" style="width: 100%">
                <el-table-column
                  prop="firstName"
                  :label="t('common.firstName')"
                />
                <el-table-column
                  prop="lastName"
                  :label="t('common.lastName')"
                />
                <el-table-column prop="email" label="Email" />
                <el-table-column prop="status" :label="t('teacher.status')">
                  <template #default="{ row }">
                    <el-tag
                      :type="row.status === 'ready' ? 'success' : 'warning'"
                    >
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('common.actions')" width="120">
                  <template #default="{ row }">
                    <el-button
                      type="danger"
                      size="small"
                      @click="handleRemoveStudent(row.id)"
                    >
                      {{ t("common.delete") }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
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
                >
                  {{ t("teacher.activateTest") }}
                </el-button>

                <el-button
                  type="warning"
                  size="large"
                  style="width: 100%; margin-top: 12px"
                  @click="handleStartTest"
                  :disabled="waitingStudents.length === 0"
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
                  {{ project?.settings.totalTime }} min
                </el-descriptions-item>
                <el-descriptions-item :label="t('teacher.maxStudents')">
                  {{ project?.settings.maxStudents }}
                </el-descriptions-item>
                <el-descriptions-item :label="t('teacher.questionCount')">
                  {{
                    project?.settings.questionTypes.reduce(
                      (sum: number, q: any) => sum + q.count,
                      0
                    )
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

@media (max-width: 768px) {
  .add-student-section {
    flex-direction: column;
    align-items: stretch;

    .el-input {
      width: 100% !important;
      margin-right: 0 !important;
      margin-bottom: var(--spacing-md);
    }
  }
}
</style>
