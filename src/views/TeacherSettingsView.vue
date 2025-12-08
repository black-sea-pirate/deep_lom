<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import ThemeToggle from "@/components/ThemeToggle.vue";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

// Profile edit form
const profileForm = reactive({
  firstName: "",
  lastName: "",
});
const profileLoading = ref(false);
const isEditingProfile = ref(false);
const profileFormRef = ref();

// Profile form rules
const profileRules = {
  firstName: [
    {
      required: true,
      message: t("teacherSettings.firstName"),
      trigger: "blur",
    },
  ],
  lastName: [
    { required: true, message: t("teacherSettings.lastName"), trigger: "blur" },
  ],
};

// Initialize profile form with current user data
onMounted(() => {
  if (authStore.user) {
    profileForm.firstName = authStore.user.firstName || "";
    profileForm.lastName = authStore.user.lastName || "";
  }
});

const startEditingProfile = () => {
  if (authStore.user) {
    profileForm.firstName = authStore.user.firstName || "";
    profileForm.lastName = authStore.user.lastName || "";
  }
  isEditingProfile.value = true;
};

const cancelEditingProfile = () => {
  isEditingProfile.value = false;
  if (authStore.user) {
    profileForm.firstName = authStore.user.firstName || "";
    profileForm.lastName = authStore.user.lastName || "";
  }
};

const handleUpdateProfile = async () => {
  if (!profileFormRef.value) return;

  try {
    await profileFormRef.value.validate();
  } catch {
    return;
  }

  profileLoading.value = true;
  try {
    await authStore.updateProfile({
      firstName: profileForm.firstName,
      lastName: profileForm.lastName,
    });
    ElMessage.success(t("teacherSettings.profileUpdated"));
    isEditingProfile.value = false;
  } catch (err: any) {
    const message = err.response?.data?.detail || "Failed to update profile";
    ElMessage.error(message);
  } finally {
    profileLoading.value = false;
  }
};

// Password change form
const passwordForm = reactive({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});
const passwordLoading = ref(false);

// Password form rules
const passwordRules = {
  currentPassword: [
    {
      required: true,
      message: t("teacherSettings.currentPassword"),
      trigger: "blur",
    },
  ],
  newPassword: [
    {
      required: true,
      message: t("teacherSettings.newPassword"),
      trigger: "blur",
    },
    { min: 6, message: t("teacherSettings.passwordTooShort"), trigger: "blur" },
  ],
  confirmPassword: [
    {
      required: true,
      message: t("teacherSettings.confirmNewPassword"),
      trigger: "blur",
    },
  ],
};

const passwordFormRef = ref();

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return;

  try {
    await passwordFormRef.value.validate();
  } catch {
    return;
  }

  // Check passwords match
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.error(t("teacherSettings.passwordMismatch"));
    return;
  }

  passwordLoading.value = true;
  try {
    await authStore.changePassword(
      passwordForm.currentPassword,
      passwordForm.newPassword
    );
    ElMessage.success(t("teacherSettings.passwordChanged"));

    // Clear form
    passwordForm.currentPassword = "";
    passwordForm.newPassword = "";
    passwordForm.confirmPassword = "";
  } catch (err: any) {
    const message =
      err.response?.data?.detail || t("teacherSettings.wrongCurrentPassword");
    ElMessage.error(message);
  } finally {
    passwordLoading.value = false;
  }
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
          <h1>{{ t("teacherSettings.title") }}</h1>
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
        <div class="settings-container">
          <!-- Profile Info Card -->
          <el-card class="settings-card">
            <template #header>
              <div class="card-header">
                <div class="card-title">
                  <el-icon><User /></el-icon>
                  <span>{{ t("teacherSettings.profile") }}</span>
                </div>
                <el-button
                  v-if="!isEditingProfile"
                  type="primary"
                  link
                  @click="startEditingProfile"
                >
                  <el-icon><Edit /></el-icon>
                  {{ t("common.edit") }}
                </el-button>
              </div>
            </template>

            <!-- View Mode -->
            <el-descriptions v-if="!isEditingProfile" :column="1" border>
              <el-descriptions-item :label="t('teacherSettings.firstName')">
                {{ authStore.user?.firstName }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('teacherSettings.lastName')">
                {{ authStore.user?.lastName }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('teacherSettings.email')">
                {{ authStore.user?.email }}
              </el-descriptions-item>
            </el-descriptions>

            <!-- Edit Mode -->
            <el-form
              v-else
              ref="profileFormRef"
              :model="profileForm"
              :rules="profileRules"
              label-position="top"
              class="profile-form"
            >
              <el-form-item
                :label="t('teacherSettings.firstName')"
                prop="firstName"
              >
                <el-input
                  v-model="profileForm.firstName"
                  :placeholder="t('teacherSettings.firstName')"
                />
              </el-form-item>

              <el-form-item
                :label="t('teacherSettings.lastName')"
                prop="lastName"
              >
                <el-input
                  v-model="profileForm.lastName"
                  :placeholder="t('teacherSettings.lastName')"
                />
              </el-form-item>

              <el-form-item :label="t('teacherSettings.email')">
                <el-input :model-value="authStore.user?.email" disabled />
                <div class="form-hint">
                  {{ t("teacherSettings.emailCannotChange") }}
                </div>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="profileLoading"
                  @click="handleUpdateProfile"
                >
                  {{ t("teacherSettings.updateProfile") }}
                </el-button>
                <el-button @click="cancelEditingProfile">
                  {{ t("common.cancel") }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <!-- Change Password Card -->
          <el-card class="settings-card">
            <template #header>
              <div class="card-header">
                <el-icon><Lock /></el-icon>
                <span>{{ t("teacherSettings.changePassword") }}</span>
              </div>
            </template>

            <el-form
              ref="passwordFormRef"
              :model="passwordForm"
              :rules="passwordRules"
              label-position="top"
              class="password-form"
            >
              <el-form-item
                :label="t('teacherSettings.currentPassword')"
                prop="currentPassword"
              >
                <el-input
                  v-model="passwordForm.currentPassword"
                  type="password"
                  show-password
                  :placeholder="t('teacherSettings.currentPassword')"
                />
              </el-form-item>

              <el-form-item
                :label="t('teacherSettings.newPassword')"
                prop="newPassword"
              >
                <el-input
                  v-model="passwordForm.newPassword"
                  type="password"
                  show-password
                  :placeholder="t('teacherSettings.newPassword')"
                />
              </el-form-item>

              <el-form-item
                :label="t('teacherSettings.confirmNewPassword')"
                prop="confirmPassword"
              >
                <el-input
                  v-model="passwordForm.confirmPassword"
                  type="password"
                  show-password
                  :placeholder="t('teacherSettings.confirmNewPassword')"
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="passwordLoading"
                  @click="handleChangePassword"
                >
                  {{ t("teacherSettings.updatePassword") }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script lang="ts">
import { User, Lock, Edit } from "@element-plus/icons-vue";

export default {
  components: { User, Lock, Edit },
};
</script>

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

.settings-container {
  max-width: 600px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.settings-card {
  margin-bottom: var(--spacing-lg);

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .card-title {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-weight: 600;
      font-size: 1.1rem;
    }
  }
}

.profile-form,
.password-form {
  max-width: 400px;
}

.form-hint {
  font-size: 0.8rem;
  color: var(--color-text-light);
  margin-top: 4px;
}

:deep(.el-descriptions) {
  .el-descriptions__label {
    width: 150px;
  }
}
</style>
