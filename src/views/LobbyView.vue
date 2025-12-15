<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Message,
  Clock,
  Refresh,
  User,
  Connection,
  View,
  Delete,
  RefreshRight,
} from "@element-plus/icons-vue";
import {
  projectService,
  type ProjectStudent,
  type StudentTestResult,
} from "@/services/project.service";
import {
  participantService,
  type Participant,
} from "@/services/participant.service";
import {
  useLobbyWebSocket,
  type LobbyStudent,
  type ConnectionStatus,
} from "@/services/websocket.service";

const route = useRoute();
const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const projectId = route.params.id as string;
// Use currentProject from store (set by fetchProject) or fallback to projects list
const project = computed(() =>
  projectStore.currentProject?.id === projectId
    ? projectStore.currentProject
    : projectStore.getProject(projectId)
);

// Real students data from backend (allowed list)
const allowedStudents = ref<ProjectStudent[]>([]);
const loading = ref(false);
const addingStudent = ref(false);
const projectLoading = ref(true);

// Test results data
const testResults = ref<StudentTestResult[]>([]);
const loadingResults = ref(false);
let resultsRefreshInterval: ReturnType<typeof setInterval> | null = null;

// Computed properties for test results stats
const completedResults = computed(() =>
  testResults.value.filter(
    (r) => r.status === "completed" || r.status === "graded"
  )
);
const inProgressResults = computed(() =>
  testResults.value.filter((r) => r.status === "in-progress")
);

// WebSocket for real-time lobby
const lobbyWs = useLobbyWebSocket();
const wsStatus = computed(() => lobbyWs.connectionStatus.value);
const onlineStudents = computed(() => lobbyWs.lobbyState.students);
const onlineCount = computed(() => lobbyWs.lobbyState.student_count);
const readyCount = computed(() => lobbyWs.readyCount);
const allReady = computed(() => lobbyWs.allReady);

// Confirmed contacts from teacher's database
const confirmedContacts = ref<Participant[]>([]);
const selectedStudentEmail = ref<string>("");
const loadingContacts = ref(false);

const showScheduleDialog = ref(false);
const scheduleForm = ref({
  startTime: new Date(),
  endTime: new Date(Date.now() + 5 * 60 * 60 * 1000), // +5 hours
});

// Setup WebSocket callbacks
lobbyWs.setCallbacks({
  onStudentJoined: (student) => {
    ElMessage.success(
      `${student.first_name} ${student.last_name} joined the lobby`
    );
  },
  onStudentLeft: (userId, name) => {
    ElMessage.info(`${name} left the lobby`);
  },
  onStudentReady: (userId, status) => {
    const student = onlineStudents.value.find((s) => s.user_id === userId);
    if (student) {
      ElMessage.info(`${student.first_name} is ${status}`);
    }
  },
  onError: (message) => {
    ElMessage.error(`WebSocket error: ${message}`);
  },
});

// Load project and students on mount
onMounted(async () => {
  await loadProject();
  await Promise.all([
    loadStudents(),
    loadConfirmedContacts(),
    loadTestResults(),
  ]);

  // Connect to WebSocket lobby as teacher
  await connectToLobby();

  // Start periodic refresh of test results (every 10 seconds)
  resultsRefreshInterval = setInterval(() => {
    loadTestResults();
  }, 10000);
});

// Cleanup on unmount
onUnmounted(() => {
  lobbyWs.disconnect();
  if (resultsRefreshInterval) {
    clearInterval(resultsRefreshInterval);
  }
});

const connectToLobby = async () => {
  const connected = await lobbyWs.connectAsTeacher(projectId);
  if (!connected) {
    console.warn("WebSocket connection failed, using REST polling fallback");
  }
};

const loadProject = async () => {
  projectLoading.value = true;
  try {
    await projectStore.fetchProject(projectId);
  } catch (error) {
    console.error("Error loading project:", error);
    ElMessage.error("Failed to load project");
  } finally {
    projectLoading.value = false;
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

// Load test results
const loadTestResults = async () => {
  loadingResults.value = true;
  try {
    const response = await projectService.getTestResults(projectId);
    testResults.value = response.results;
  } catch (error) {
    console.error("Error loading test results:", error);
    testResults.value = [];
  } finally {
    loadingResults.value = false;
  }
};

// Get test result for a specific student
const getStudentTestResult = (email: string): StudentTestResult | undefined => {
  return testResults.value.find(
    (r) => r.email.toLowerCase() === email.toLowerCase()
  );
};

// Format time taken (seconds to mm:ss)
const formatTimeTaken = (seconds: number | null): string => {
  if (seconds === null) return "-";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

// Get status badge type
const getTestStatusType = (
  status: string
): "success" | "warning" | "info" | "danger" | "" => {
  switch (status) {
    case "completed":
    case "graded":
      return "success";
    case "in-progress":
      return "warning";
    case "not_started":
      return "info";
    case "pending":
      return "";
    default:
      return "info";
  }
};

// Get status label
const getTestStatusLabel = (status: string): string => {
  switch (status) {
    case "completed":
      return t("lobby.completed") || "Completed";
    case "graded":
      return t("lobby.graded") || "Graded";
    case "in-progress":
      return t("lobby.inProgress") || "In Progress";
    case "not_started":
      return t("lobby.notStarted") || "Not Started";
    case "pending":
      return t("lobby.pending") || "Pending";
    default:
      return status;
  }
};

// Calculate score percentage
const getScorePercent = (
  score: number | null,
  maxScore: number | null
): string => {
  if (score === null || maxScore === null || maxScore === 0) return "-";
  return Math.round((score / maxScore) * 100) + "%";
};

// Delete student test results
const handleDeleteResults = async (email: string, name: string) => {
  try {
    await ElMessageBox.confirm(
      t("lobby.confirmDeleteResults", { name }) ||
        `Delete all test results for ${name}? This action cannot be undone.`,
      t("common.confirm") || "Confirm",
      {
        confirmButtonText: t("common.delete") || "Delete",
        cancelButtonText: t("common.cancel") || "Cancel",
        type: "warning",
      }
    );

    await projectService.deleteStudentTestResults(projectId, email);
    ElMessage.success(
      t("lobby.resultsDeleted") || "Results deleted successfully"
    );
    await loadTestResults();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("Error deleting results:", error);
      ElMessage.error(
        error.response?.data?.detail || "Failed to delete results"
      );
    }
  }
};

// Reset student test access
const handleResetAccess = async (email: string, name: string) => {
  try {
    await ElMessageBox.confirm(
      t("lobby.confirmResetAccess", { name }) ||
        `Reset test access for ${name}? This will delete their incomplete test and allow them to start fresh.`,
      t("common.confirm") || "Confirm",
      {
        confirmButtonText: t("lobby.reset") || "Reset",
        cancelButtonText: t("common.cancel") || "Cancel",
        type: "warning",
      }
    );

    const result = await projectService.resetStudentTestAccess(
      projectId,
      email
    );
    ElMessage.success(result.message);
    await loadTestResults();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("Error resetting access:", error);
      ElMessage.error(error.response?.data?.detail || "Failed to reset access");
    }
  }
};

// View student test answers
const handleViewAnswers = (testId: string) => {
  router.push(`/teacher/project/${projectId}/test/${testId}/review`);
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
    // Start test via WebSocket (notifies all connected students instantly)
    if (wsStatus.value === "connected") {
      lobbyWs.startTest();
    }

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

// Kick student from lobby (WebSocket)
const handleKickFromLobby = (userId: string) => {
  if (wsStatus.value === "connected") {
    lobbyWs.kickStudent(userId);
    ElMessage.success("Student removed from lobby");
  }
};

// Get online status for a student
const isStudentOnline = (email: string): boolean => {
  return onlineStudents.value.some(
    (s) => s.email.toLowerCase() === email.toLowerCase()
  );
};

const getOnlineStudent = (email: string): LobbyStudent | undefined => {
  return onlineStudents.value.find(
    (s) => s.email.toLowerCase() === email.toLowerCase()
  );
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
          <div class="header-right">
            <!-- WebSocket connection status -->
            <el-tag
              :type="
                wsStatus === 'connected'
                  ? 'success'
                  : wsStatus === 'connecting'
                  ? 'warning'
                  : 'danger'
              "
              effect="dark"
              size="small"
              style="margin-right: 12px"
            >
              <el-icon><Connection /></el-icon>
              {{
                wsStatus === "connected"
                  ? "Live"
                  : wsStatus === "connecting"
                  ? "Connecting..."
                  : "Offline"
              }}
            </el-tag>
            <el-button @click="router.push('/teacher')">
              {{ t("common.back") }}
            </el-button>
          </div>
        </div>
      </el-header>

      <el-main v-loading="projectLoading">
        <el-row :gutter="20" v-if="project">
          <el-col :xs="24" :lg="16">
            <!-- Online Students Card (WebSocket) -->
            <el-card
              v-if="wsStatus === 'connected'"
              class="online-card"
              style="margin-bottom: 20px"
            >
              <template #header>
                <div class="flex items-center justify-between">
                  <h2>
                    🟢 {{ t("teacher.onlineNow") }} ({{ onlineCount }}/{{
                      project.settings?.maxStudents || 30
                    }})
                  </h2>
                  <div>
                    <el-tag
                      type="success"
                      size="small"
                      style="margin-right: 8px"
                    >
                      Ready: {{ readyCount }}/{{ onlineCount }}
                    </el-tag>
                    <el-tag
                      v-if="allReady && onlineCount > 0"
                      type="success"
                      effect="dark"
                      size="small"
                    >
                      All Ready!
                    </el-tag>
                  </div>
                </div>
              </template>

              <el-table
                :data="onlineStudents"
                style="width: 100%"
                v-if="onlineStudents.length > 0"
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column :label="t('common.name')">
                  <template #default="{ row }">
                    <span class="student-name">
                      {{ row.first_name }} {{ row.last_name }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="email" :label="t('common.email')" />
                <el-table-column :label="t('common.status')" width="120">
                  <template #default="{ row }">
                    <el-tag
                      size="small"
                      :type="row.status === 'ready' ? 'success' : 'info'"
                      effect="dark"
                    >
                      {{ row.status === "ready" ? "✓ Ready" : "⏳ Waiting" }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('common.actions')" width="100">
                  <template #default="{ row }">
                    <el-button
                      type="danger"
                      size="small"
                      @click="handleKickFromLobby(row.user_id)"
                    >
                      Kick
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>

              <el-empty
                v-else
                :description="
                  t('teacher.waitingForStudents') ||
                  'No students online yet. Waiting for students to join...'
                "
                :image-size="60"
              />
            </el-card>

            <!-- Allowed Students Card (REST API managed) -->
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
                    <div class="student-name-cell">
                      <span v-if="isStudentOnline(row.email)" class="online-dot"
                        >🟢</span
                      >
                      <span v-else class="offline-dot">⚪</span>
                      <span class="student-name">
                        {{ row.firstName || "" }} {{ row.lastName || "" }}
                      </span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="email" :label="t('common.email')" />
                <el-table-column :label="'Online'" width="100">
                  <template #default="{ row }">
                    <el-tag
                      size="small"
                      :type="isStudentOnline(row.email) ? 'success' : 'info'"
                    >
                      {{ isStudentOnline(row.email) ? "Online" : "Offline" }}
                    </el-tag>
                  </template>
                </el-table-column>
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

        <!-- Test Results Section -->
        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="24">
            <el-card class="results-card">
              <template #header>
                <div class="flex items-center justify-between">
                  <h2>
                    📊 {{ t("lobby.testResults") || "Test Results" }}
                    <el-tag type="info" size="small" style="margin-left: 8px">
                      {{ completedResults.length }}
                      {{ t("lobby.completed") || "completed" }}
                    </el-tag>
                    <el-tag
                      v-if="inProgressResults.length > 0"
                      type="warning"
                      size="small"
                      style="margin-left: 4px"
                    >
                      {{ inProgressResults.length }}
                      {{ t("lobby.inProgress") || "in progress" }}
                    </el-tag>
                  </h2>
                  <el-button
                    :icon="Refresh"
                    circle
                    size="small"
                    @click="loadTestResults"
                    :loading="loadingResults"
                  />
                </div>
              </template>

              <el-table
                :data="testResults"
                style="width: 100%"
                v-loading="loadingResults"
                :row-class-name="(row: any) => row.row.status === 'in-progress' ? 'in-progress-row' : ''"
              >
                <el-table-column type="index" width="50" label="#" />
                <el-table-column :label="t('common.name')" min-width="150">
                  <template #default="{ row }">
                    <div class="student-name-cell">
                      <span v-if="isStudentOnline(row.email)" class="online-dot"
                        >🟢</span
                      >
                      <span v-else class="offline-dot">⚪</span>
                      <span class="student-name">
                        {{ row.firstName || "" }} {{ row.lastName || "" }}
                      </span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column
                  prop="email"
                  :label="t('common.email')"
                  min-width="180"
                />
                <el-table-column
                  :label="t('lobby.testStatus') || 'Test Status'"
                  width="130"
                >
                  <template #default="{ row }">
                    <el-tag
                      size="small"
                      :type="getTestStatusType(row.status)"
                      effect="dark"
                    >
                      {{ getTestStatusLabel(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('lobby.score') || 'Score'"
                  width="100"
                >
                  <template #default="{ row }">
                    <span v-if="row.score !== null" class="score-value">
                      {{ getScorePercent(row.score, row.maxScore) }}
                      <span class="score-raw"
                        >({{ row.score?.toFixed(1) }}/{{ row.maxScore }})</span
                      >
                    </span>
                    <span v-else class="score-na">-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('lobby.timeTaken') || 'Time'"
                  width="90"
                >
                  <template #default="{ row }">
                    {{ formatTimeTaken(row.timeTaken) }}
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('lobby.grading') || 'Grading'"
                  width="120"
                >
                  <template #default="{ row }">
                    <div v-if="row.totalQuestions > 0">
                      <el-progress
                        :percentage="
                          Math.round(
                            (row.gradedQuestions / row.totalQuestions) * 100
                          )
                        "
                        :stroke-width="6"
                        :show-text="false"
                        style="width: 60px; display: inline-block"
                      />
                      <span style="margin-left: 4px; font-size: 11px">
                        {{ row.gradedQuestions }}/{{ row.totalQuestions }}
                      </span>
                      <el-tooltip
                        v-if="row.pendingAiGrading > 0"
                        :content="`${row.pendingAiGrading} questions pending AI grading`"
                      >
                        <el-icon
                          style="
                            margin-left: 4px;
                            color: var(--el-color-warning);
                          "
                          ><Clock
                        /></el-icon>
                      </el-tooltip>
                    </div>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('common.actions')"
                  width="200"
                  fixed="right"
                >
                  <template #default="{ row }">
                    <div class="action-buttons">
                      <!-- View answers button -->
                      <el-tooltip
                        :content="t('lobby.viewAnswers') || 'View Answers'"
                        v-if="row.testId"
                      >
                        <el-button
                          type="primary"
                          size="small"
                          :icon="View"
                          circle
                          @click="handleViewAnswers(row.testId)"
                        />
                      </el-tooltip>

                      <!-- Reset access button (for in-progress or pending) -->
                      <el-tooltip
                        :content="t('lobby.resetAccess') || 'Reset Access'"
                        v-if="
                          row.status === 'in-progress' ||
                          row.status === 'pending'
                        "
                      >
                        <el-button
                          type="warning"
                          size="small"
                          :icon="RefreshRight"
                          circle
                          @click="
                            handleResetAccess(
                              row.email,
                              `${row.firstName} ${row.lastName}`
                            )
                          "
                        />
                      </el-tooltip>

                      <!-- Delete results button -->
                      <el-tooltip
                        :content="t('lobby.deleteResults') || 'Delete Results'"
                        v-if="row.testId"
                      >
                        <el-button
                          type="danger"
                          size="small"
                          :icon="Delete"
                          circle
                          @click="
                            handleDeleteResults(
                              row.email,
                              `${row.firstName} ${row.lastName}`
                            )
                          "
                        />
                      </el-tooltip>

                      <!-- No test yet -->
                      <span
                        v-if="!row.testId && row.status === 'not_started'"
                        class="not-started-hint"
                      >
                        {{ t("lobby.notStartedYet") || "Not started yet" }}
                      </span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>

              <el-empty
                v-if="!loadingResults && testResults.length === 0"
                :description="t('lobby.noResultsYet') || 'No test results yet'"
              />
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

    .header-right {
      display: flex;
      align-items: center;
    }
  }
}

.el-main {
  padding: var(--spacing-xl);
}

.online-card {
  border: 2px solid var(--el-color-success-light-5);

  :deep(.el-card__header) {
    background: var(--el-color-success-light-9);
  }
}

.student-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  .online-dot,
  .offline-dot {
    font-size: 10px;
  }
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

/* Test Results Section Styles */
.results-card {
  h2 {
    margin: 0;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.student-name-cell {
  display: flex;
  align-items: center;
  gap: 6px;

  .online-dot,
  .offline-dot {
    font-size: 10px;
  }

  .student-name {
    font-weight: 500;
  }
}

.score-value {
  font-weight: 600;
  color: var(--el-color-success);

  .score-raw {
    font-size: 0.8em;
    font-weight: normal;
    color: var(--el-text-color-secondary);
    margin-left: 2px;
  }
}

.score-na {
  color: var(--el-text-color-placeholder);
}

.action-buttons {
  display: flex;
  gap: 4px;
  align-items: center;
}

.not-started-hint {
  font-size: 0.8em;
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.el-table {
  .in-progress-row {
    background-color: rgba(var(--el-color-warning-rgb), 0.05);
  }
}
</style>
