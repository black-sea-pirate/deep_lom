<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import ThemeToggle from "@/components/ThemeToggle.vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  studentService,
  type StudentEmail,
  type StudentStatistics,
  type CompletedTestInfo,
  type UpcomingTestInfo,
  type ContactRequest,
} from "@/services";

const router = useRouter();
const authStore = useAuthStore();
const { t, locale } = useI18n();

// Loading state
const loading = ref(false);

// Active tab for statistics modal
const activeStatTab = ref<"total" | "average" | "completed">("total");
const showStatisticsDialog = ref(false);
const showAccountDialog = ref(false);
const showPasswordDialog = ref(false);

// Languages
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

// Data from API
const upcomingTests = ref<UpcomingTestInfo[]>([]);
const completedTestsList = ref<CompletedTestInfo[]>([]);
const statistics = ref<StudentStatistics>({
  totalTests: 0,
  completedTests: 0,
  averageScore: 0,
});
const userEmails = ref<StudentEmail[]>([]);

// Contact requests (notifications)
const contactRequests = ref<ContactRequest[]>([]);
const contactRequestsCount = ref(0);
const showNotificationsDialog = ref(false);
const processingRequest = ref<string | null>(null);

// Countdown timer
const currentTime = ref(Date.now());
let countdownInterval: ReturnType<typeof setInterval> | null = null;

const formatCountdown = (
  targetTime: string | Date | null | undefined,
  isEndTime: boolean = false
): string => {
  if (!targetTime) return "";

  const target = new Date(targetTime).getTime();
  const diff = target - currentTime.value;

  if (diff <= 0) {
    return isEndTime
      ? t("student.testEnded") || "Test ended"
      : t("student.availableNow") || "Available now";
  }

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  return `${minutes}m ${seconds}s`;
};

const getTestCountdown = (test: UpcomingTestInfo) => {
  if (test.status === "available") {
    // Test is available - show time remaining until end
    if (test.endTime) {
      return {
        label: t("student.endsIn") || "Ends in",
        time: formatCountdown(test.endTime, true),
        type: "warning" as const,
      };
    }
    return null;
  } else {
    // Test is scheduled - show time until start
    if (test.startTime) {
      return {
        label: t("student.startsIn") || "Starts in",
        time: formatCountdown(test.startTime, false),
        type: "info" as const,
      };
    }
    return null;
  }
};

// Load data from API
const loadStatistics = async () => {
  try {
    const data = await studentService.getStatistics();
    statistics.value = data;
  } catch (error) {
    console.error("Failed to load statistics:", error);
  }
};

const loadCompletedTests = async () => {
  try {
    const data = await studentService.getCompletedTests();
    completedTestsList.value = data;
  } catch (error) {
    console.error("Failed to load completed tests:", error);
  }
};

const loadUpcomingTests = async () => {
  try {
    const data = await studentService.getUpcomingTests();
    upcomingTests.value = data;
  } catch (error) {
    console.error("Failed to load upcoming tests:", error);
  }
};

const loadEmails = async () => {
  try {
    const data = await studentService.getEmails();
    userEmails.value = data;
  } catch (error) {
    console.error("Failed to load emails:", error);
  }
};

const loadContactRequests = async () => {
  try {
    contactRequests.value = await studentService.getContactRequests();
    contactRequestsCount.value = await studentService.getContactRequestsCount();
  } catch (error) {
    console.error("Failed to load contact requests:", error);
    contactRequests.value = [];
    contactRequestsCount.value = 0;
  }
};

// Handle contact request actions
const handleConfirmRequest = async (participantId: string) => {
  processingRequest.value = participantId;
  try {
    await studentService.confirmContactRequest(participantId);
    ElMessage.success(t("student.requestConfirmed") || "Request confirmed");
    await loadContactRequests();
  } catch (error: any) {
    const message = error.response?.data?.detail || "Failed to confirm request";
    ElMessage.error(message);
  } finally {
    processingRequest.value = null;
  }
};

const handleRejectRequest = async (participantId: string) => {
  try {
    await ElMessageBox.confirm(
      t("student.confirmRejectRequest") ||
        "Are you sure you want to reject this request?",
      t("common.confirm") || "Confirm",
      { type: "warning" }
    );

    processingRequest.value = participantId;
    await studentService.rejectContactRequest(participantId);
    ElMessage.success(t("student.requestRejected") || "Request rejected");
    await loadContactRequests();
  } catch (error: any) {
    if (error !== "cancel") {
      const message =
        error.response?.data?.detail || "Failed to reject request";
      ElMessage.error(message);
    }
  } finally {
    processingRequest.value = null;
  }
};

// Initialize on mount
onMounted(async () => {
  loading.value = true;
  try {
    await Promise.all([
      loadStatistics(),
      loadCompletedTests(),
      loadUpcomingTests(),
      loadEmails(),
      loadContactRequests(),
    ]);
  } finally {
    loading.value = false;
  }

  // Start countdown timer update
  countdownInterval = setInterval(() => {
    currentTime.value = Date.now();
  }, 1000);
});

// Cleanup on unmount
onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
  }
});

const newEmailForm = ref({
  email: "",
  institution: "",
});

const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

// Open statistics dialog
const openStatistics = (tab: "total" | "average" | "completed") => {
  activeStatTab.value = tab;
  showStatisticsDialog.value = true;
};

// Add new email
const addEmail = async () => {
  if (!newEmailForm.value.email || !newEmailForm.value.institution) {
    ElMessage.warning(t("common.fillAllFields") || "Please fill all fields");
    return;
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(newEmailForm.value.email)) {
    ElMessage.warning(
      t("studentAccount.invalidEmail") || "Invalid email format"
    );
    return;
  }

  try {
    await studentService.addEmail(
      newEmailForm.value.email,
      newEmailForm.value.institution
    );
    newEmailForm.value = { email: "", institution: "" };
    ElMessage.success(t("studentAccount.emailAdded") || "Email added");
    await loadEmails();
  } catch (error: any) {
    const message = error.response?.data?.detail || "Failed to add email";
    ElMessage.error(message);
  }
};

// Remove email
const removeEmail = async (emailId: string) => {
  const email = userEmails.value.find((e) => e.id === emailId);
  if (email?.isPrimary) {
    ElMessage.warning(
      t("studentAccount.cannotRemovePrimary") || "Cannot remove primary email"
    );
    return;
  }

  try {
    await ElMessageBox.confirm(
      t("studentAccount.confirmRemoveEmail") || "Remove this email?",
      t("common.delete") || "Delete",
      { type: "warning" }
    );

    await studentService.deleteEmail(emailId);
    ElMessage.success(t("studentAccount.emailRemoved") || "Email removed");
    await loadEmails();
  } catch (error: any) {
    if (error !== "cancel") {
      const message = error.response?.data?.detail || "Failed to remove email";
      ElMessage.error(message);
    }
  }
};

// Set primary email
const setPrimaryEmail = async (emailId: string) => {
  try {
    await studentService.setPrimaryEmail(emailId);
    ElMessage.success(
      t("studentAccount.primaryChanged") || "Primary email changed"
    );
    await loadEmails();
  } catch (error: any) {
    const message =
      error.response?.data?.detail || "Failed to change primary email";
    ElMessage.error(message);
  }
};

// Change password
const changePassword = async () => {
  if (
    !passwordForm.value.currentPassword ||
    !passwordForm.value.newPassword ||
    !passwordForm.value.confirmPassword
  ) {
    ElMessage.warning(t("common.fillAllFields") || "Please fill all fields");
    return;
  }

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.error(
      t("studentAccount.passwordMismatch") || "Passwords do not match"
    );
    return;
  }

  if (passwordForm.value.newPassword.length < 6) {
    ElMessage.error(
      t("studentAccount.passwordTooShort") ||
        "Password must be at least 6 characters"
    );
    return;
  }

  try {
    await studentService.changePassword(
      passwordForm.value.currentPassword,
      passwordForm.value.newPassword
    );
    ElMessage.success(
      t("studentAccount.passwordChanged") || "Password changed successfully"
    );
    passwordForm.value = {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    };
    showPasswordDialog.value = false;
  } catch (error: any) {
    const message = error.response?.data?.detail || "Failed to change password";
    ElMessage.error(message);
  }
};

const handleLogout = () => {
  authStore.logout();
  router.push("/login");
};

// Get score color
const getScoreType = (score: number) => {
  if (score >= 90) return "success";
  if (score >= 70) return "primary";
  if (score >= 60) return "warning";
  return "danger";
};
</script>

<template>
  <div class="student-dashboard">
    <!-- Header -->
    <el-header class="header">
      <div class="header-content">
        <h1>{{ t("student.dashboard") }}</h1>

        <div class="header-right">
          <!-- Navigation Menu -->
          <el-menu mode="horizontal" class="nav-menu">
            <el-menu-item index="dashboard" @click="router.push('/student')">
              <el-icon><House /></el-icon>
              <span>{{ t("nav.dashboard") }}</span>
            </el-menu-item>
            <el-menu-item index="tests" @click="openStatistics('completed')">
              <el-icon><Document /></el-icon>
              <span>{{ t("student.myStatistics") }}</span>
            </el-menu-item>
            <el-menu-item
              index="notifications"
              @click="showNotificationsDialog = true"
            >
              <el-badge
                :value="contactRequestsCount"
                :hidden="contactRequestsCount === 0"
                :max="99"
              >
                <el-icon><Bell /></el-icon>
                <span>{{ t("student.notifications") || "Notifications" }}</span>
              </el-badge>
            </el-menu-item>
          </el-menu>

          <!-- Theme Toggle -->
          <ThemeToggle />

          <!-- Language Selector -->
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

          <!-- Account Dropdown -->
          <el-dropdown trigger="click">
            <el-button class="account-btn">
              <el-avatar :size="28" style="margin-right: 8px">
                {{ authStore.user?.firstName?.charAt(0) || "S" }}
              </el-avatar>
              <span
                >{{ authStore.user?.firstName }}
                {{ authStore.user?.lastName }}</span
              >
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showAccountDialog = true">
                  <el-icon><User /></el-icon>
                  {{ t("studentAccount.manageEmails") || "Manage Emails" }}
                </el-dropdown-item>
                <el-dropdown-item @click="showPasswordDialog = true">
                  <el-icon><Lock /></el-icon>
                  {{ t("studentAccount.changePassword") || "Change Password" }}
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  {{ t("common.logout") }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-header>

    <!-- Main Content -->
    <el-main class="main-content">
      <div class="dashboard-content">
        <!-- Statistics Cards (Clickable) -->
        <el-row :gutter="20" class="stats-row">
          <el-col :xs="24" :sm="8">
            <el-card
              shadow="hover"
              class="stat-card"
              @click="openStatistics('total')"
            >
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
            <el-card
              shadow="hover"
              class="stat-card"
              @click="openStatistics('average')"
            >
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
            <el-card
              shadow="hover"
              class="stat-card"
              @click="openStatistics('completed')"
            >
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
                <el-tag
                  :type="test.status === 'available' ? 'success' : 'warning'"
                >
                  {{
                    test.status === "available"
                      ? t("student.available") || "Available"
                      : t("student.scheduled") || "Scheduled"
                  }}
                </el-tag>
              </div>

              <div class="test-info">
                <div class="info-item">
                  <el-icon><Timer /></el-icon>
                  <span>{{ test.duration }} min</span>
                </div>
                <div class="info-item" v-if="test.startTime">
                  <el-icon><Calendar /></el-icon>
                  <span>{{
                    new Date(test.startTime).toLocaleDateString()
                  }}</span>
                </div>
              </div>

              <!-- Countdown Timer -->
              <div v-if="getTestCountdown(test)" class="countdown-section">
                <div class="countdown-label">
                  {{ getTestCountdown(test)?.label }}
                </div>
                <div
                  class="countdown-timer"
                  :class="getTestCountdown(test)?.type"
                >
                  {{ getTestCountdown(test)?.time }}
                </div>
              </div>

              <el-button
                type="primary"
                size="large"
                @click="router.push(`/student/test/${test.id}`)"
                style="width: 100%; margin-top: 16px"
                :disabled="test.status !== 'available'"
              >
                {{
                  test.status === "available"
                    ? t("student.takeTest")
                    : t("student.waitingForStart") || "Waiting for start"
                }}
              </el-button>
            </el-card>

            <el-empty
              v-if="upcomingTests.length === 0"
              :description="t('student.noUpcomingTests') || 'No upcoming tests'"
            />
          </div>
        </div>
      </div>
    </el-main>

    <!-- Statistics Dialog -->
    <el-dialog
      v-model="showStatisticsDialog"
      :title="t('student.myStatistics')"
      width="700px"
    >
      <el-tabs v-model="activeStatTab">
        <el-tab-pane :label="t('student.totalTests')" name="total">
          <div class="stat-summary">
            <el-statistic
              :title="t('student.totalTests')"
              :value="statistics.totalTests"
            />
            <p class="stat-description">
              {{
                t("studentStats.totalDescription") ||
                "Total number of tests assigned to you across all courses."
              }}
            </p>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="t('student.averageScore')" name="average">
          <div class="stat-summary">
            <el-statistic
              :title="t('student.averageScore')"
              :value="statistics.averageScore"
              suffix="%"
            />
            <el-progress
              :percentage="statistics.averageScore"
              :status="statistics.averageScore >= 60 ? 'success' : 'exception'"
              :stroke-width="20"
              style="margin-top: 20px"
            />
            <p class="stat-description">
              {{
                t("studentStats.averageDescription") ||
                "Your average score across all completed tests."
              }}
            </p>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="t('student.completedTests')" name="completed">
          <el-table :data="completedTestsList" stripe style="width: 100%">
            <el-table-column
              prop="title"
              :label="t('studentStats.testName') || 'Test Name'"
            />
            <el-table-column
              prop="groupName"
              :label="t('studentStats.course') || 'Course'"
              width="120"
            />
            <el-table-column :label="t('results.score') || 'Score'" width="120">
              <template #default="{ row }">
                <el-tag
                  :type="
                    getScoreType(Math.round((row.score / row.maxScore) * 100))
                  "
                  size="large"
                >
                  {{ Math.round((row.score / row.maxScore) * 100) }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              :label="t('studentStats.date') || 'Date'"
              width="120"
            >
              <template #default="{ row }">
                {{ new Date(row.completedAt).toLocaleDateString() }}
              </template>
            </el-table-column>
            <el-table-column width="100">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  size="small"
                  link
                  @click="router.push(`/student/test/${row.id}/results`)"
                >
                  {{ t("student.viewResults") }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- Account / Emails Dialog -->
    <el-dialog
      v-model="showAccountDialog"
      :title="t('studentAccount.manageEmails') || 'Manage Emails'"
      width="600px"
    >
      <div class="emails-section">
        <h4>{{ t("studentAccount.yourEmails") || "Your Emails" }}</h4>
        <p class="section-hint">
          {{
            t("studentAccount.emailsHint") ||
            "Add emails from different institutions to receive test invitations."
          }}
        </p>

        <div class="email-list">
          <div v-for="email in userEmails" :key="email.id" class="email-item">
            <div class="email-info">
              <div class="email-address">
                {{ email.email }}
                <el-tag
                  v-if="email.isPrimary"
                  size="small"
                  type="success"
                  style="margin-left: 8px"
                >
                  {{ t("studentAccount.primary") || "Primary" }}
                </el-tag>
              </div>
              <div class="email-institution">{{ email.institution }}</div>
            </div>
            <div class="email-actions">
              <el-button
                v-if="!email.isPrimary"
                size="small"
                @click="setPrimaryEmail(email.id)"
              >
                {{ t("studentAccount.makePrimary") || "Make Primary" }}
              </el-button>
              <el-button
                v-if="!email.isPrimary"
                type="danger"
                size="small"
                link
                @click="removeEmail(email.id)"
              >
                {{ t("common.delete") }}
              </el-button>
            </div>
          </div>
        </div>

        <el-divider />

        <h4>{{ t("studentAccount.addNewEmail") || "Add New Email" }}</h4>
        <el-form :model="newEmailForm" label-position="top">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item :label="t('common.email')">
                <el-input
                  v-model="newEmailForm.email"
                  :placeholder="
                    t('studentAccount.emailPlaceholder') || 'your@email.com'
                  "
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                :label="t('studentAccount.institution') || 'Institution'"
              >
                <el-input
                  v-model="newEmailForm.institution"
                  :placeholder="
                    t('studentAccount.institutionPlaceholder') ||
                    'University name'
                  "
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-button type="primary" @click="addEmail">
            {{ t("studentAccount.addEmail") || "Add Email" }}
          </el-button>
        </el-form>
      </div>
    </el-dialog>

    <!-- Change Password Dialog -->
    <el-dialog
      v-model="showPasswordDialog"
      :title="t('studentAccount.changePassword') || 'Change Password'"
      width="400px"
    >
      <el-form :model="passwordForm" label-position="top">
        <el-form-item
          :label="t('studentAccount.currentPassword') || 'Current Password'"
        >
          <el-input
            v-model="passwordForm.currentPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item
          :label="t('studentAccount.newPassword') || 'New Password'"
        >
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item
          :label="
            t('studentAccount.confirmNewPassword') || 'Confirm New Password'
          "
        >
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">{{
          t("common.cancel")
        }}</el-button>
        <el-button type="primary" @click="changePassword">
          {{ t("studentAccount.changePassword") || "Change Password" }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Notifications Dialog -->
    <el-dialog
      v-model="showNotificationsDialog"
      :title="t('student.notifications') || 'Notifications'"
      width="600px"
    >
      <div v-if="contactRequests.length === 0" class="empty-notifications">
        <el-empty
          :description="
            t('student.noNotifications') || 'No pending notifications'
          "
          :image-size="100"
        />
      </div>

      <div v-else class="notifications-list">
        <el-alert
          :title="
            t('student.contactRequestsInfo') ||
            'Teachers want to add you to their contacts'
          "
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />

        <div
          v-for="request in contactRequests"
          :key="request.id"
          class="notification-item"
        >
          <div class="notification-content">
            <div class="notification-header">
              <el-icon size="20"><User /></el-icon>
              <span class="teacher-name">{{ request.teacherName }}</span>
            </div>
            <div class="notification-details">
              <div class="detail-row">
                <span class="label"
                  >{{ t("student.teacherEmail") || "Teacher email" }}:</span
                >
                <span class="value">{{ request.teacherEmail }}</span>
              </div>
              <div class="detail-row">
                <span class="label"
                  >{{
                    t("student.yourNameInRequest") || "Your name in request"
                  }}:</span
                >
                <span class="value">{{ request.studentName }}</span>
              </div>
              <div class="detail-row">
                <span class="label"
                  >{{
                    t("student.yourEmailInRequest") || "Your email in request"
                  }}:</span
                >
                <span class="value">{{ request.studentEmail }}</span>
              </div>
            </div>
          </div>
          <div class="notification-actions">
            <el-button
              type="success"
              size="small"
              @click="handleConfirmRequest(request.id)"
              :loading="processingRequest === request.id"
            >
              <el-icon><Check /></el-icon>
              {{ t("common.confirm") || "Confirm" }}
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleRejectRequest(request.id)"
              :loading="processingRequest === request.id"
            >
              <el-icon><Close /></el-icon>
              {{ t("common.reject") || "Reject" }}
            </el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showNotificationsDialog = false">
          {{ t("common.close") || "Close" }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.student-dashboard {
  min-height: 100vh;
  background-color: var(--color-surface);
}

.header {
  background: var(--color-background);
  border-bottom: 1px solid var(--color-border);
  height: auto !important;
  padding: 0 var(--spacing-lg);

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 60px;

    h1 {
      font-size: 1.5rem;
      color: var(--color-primary);
      margin: 0;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
    }
  }
}

.nav-menu {
  background: transparent;
  border: none;

  .el-menu-item {
    height: 50px;
    line-height: 50px;
  }
}

.account-btn {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  height: auto;
}

.main-content {
  padding: 0;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

.stats-row {
  margin-bottom: var(--spacing-2xl);
}

.stat-card {
  cursor: pointer;
  transition: transform var(--transition-base),
    box-shadow var(--transition-base);

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
  }
}

.section {
  margin-bottom: var(--spacing-2xl);

  h2 {
    margin-bottom: var(--spacing-lg);
    color: var(--color-text);
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
      color: var(--color-text);
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

  .countdown-section {
    background: var(--color-background);
    border-radius: var(--border-radius);
    padding: var(--spacing-md);
    text-align: center;
    margin-top: var(--spacing-md);

    .countdown-label {
      font-size: 0.85rem;
      color: var(--color-text-light);
      margin-bottom: var(--spacing-xs);
    }

    .countdown-timer {
      font-size: 1.5rem;
      font-weight: 700;
      font-family: "Roboto Mono", monospace;

      &.info {
        color: #409eff;
      }

      &.warning {
        color: #e6a23c;
      }

      &.success {
        color: #67c23a;
      }
    }
  }
}

/* Statistics Dialog */
.stat-summary {
  text-align: center;
  padding: var(--spacing-xl);

  .stat-description {
    margin-top: var(--spacing-lg);
    color: var(--color-text-light);
  }
}

/* Emails Section */
.emails-section {
  h4 {
    margin-bottom: var(--spacing-sm);
    color: var(--color-text);
  }

  .section-hint {
    color: var(--color-text-light);
    font-size: 0.9rem;
    margin-bottom: var(--spacing-lg);
  }
}

.email-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.email-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);

  .email-info {
    .email-address {
      font-weight: 500;
      color: var(--color-text);
    }

    .email-institution {
      font-size: 0.85rem;
      color: var(--color-text-light);
      margin-top: 2px;
    }
  }

  .email-actions {
    display: flex;
    gap: var(--spacing-sm);
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-wrap: wrap;
    height: auto !important;
    padding: var(--spacing-md) 0;

    h1 {
      width: 100%;
      margin-bottom: var(--spacing-sm);
    }

    .header-right {
      flex-wrap: wrap;
    }
  }

  .nav-menu {
    display: none;
  }

  .tests-list {
    grid-template-columns: 1fr;
  }

  .stats-row .el-col {
    margin-bottom: var(--spacing-md);
  }

  .email-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }
}

// Notifications styles
.empty-notifications {
  padding: var(--spacing-xl);
}

.notifications-list {
  .notification-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
    background: var(--color-background);

    &:last-child {
      margin-bottom: 0;
    }

    .notification-content {
      flex: 1;

      .notification-header {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        margin-bottom: var(--spacing-sm);

        .teacher-name {
          font-weight: 600;
          font-size: 1.1rem;
          color: var(--color-text);
        }
      }

      .notification-details {
        .detail-row {
          display: flex;
          gap: var(--spacing-sm);
          margin-bottom: 4px;
          font-size: 0.9rem;

          .label {
            color: var(--color-text-light);
          }

          .value {
            color: var(--color-text);
          }
        }
      }
    }

    .notification-actions {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-sm);
      margin-left: var(--spacing-md);
    }
  }
}
</style>
