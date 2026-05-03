<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import ThemeToggle from "@/components/ThemeToggle.vue";
import authService from "@/services/auth.service";

const router = useRouter();
const authStore = useAuthStore();
const { t, locale } = useI18n();

// ---------------------------------------------------------------------------
// Login
// ---------------------------------------------------------------------------
const formData = ref({
  email: "",
  password: "",
  role: "student" as "teacher" | "student",
});
const loginLoading = ref(false);

const handleLogin = async () => {
  if (!formData.value.email || !formData.value.password) {
    ElMessage.error(t("common.fillAllFields") || "Please fill all fields");
    return;
  }
  loginLoading.value = true;
  try {
    const user = await authStore.login(
      formData.value.email,
      formData.value.password,
      formData.value.role
    );
    ElMessage.success(t("common.welcome"));
    router.push(user.role === "teacher" ? "/teacher" : "/student");
  } catch (err: any) {
    const msg = err.response?.data?.detail || "Login failed";
    ElMessage.error(typeof msg === "string" ? msg : "Login failed");
  } finally {
    loginLoading.value = false;
  }
};

// ---------------------------------------------------------------------------
// Language
// ---------------------------------------------------------------------------
const languages = [
  { value: "en", label: "English" },
  { value: "pl", label: "Polski" },
  { value: "ua", label: "Українська" },
  { value: "ru", label: "Русский" },
];
const changeLanguage = (lang: string) => {
  locale.value = lang;
  localStorage.setItem("locale", lang);
};

// ---------------------------------------------------------------------------
// Forgot password — 3-step modal
// ---------------------------------------------------------------------------
const resetVisible = ref(false);
const resetStep = ref<1 | 2 | 3>(1);
const resetLoading = ref(false);

const resetEmail = ref("");
const resetCode = ref("");
const resetNewPassword = ref("");
const resetConfirmPassword = ref("");

const openReset = () => {
  resetStep.value = 1;
  resetEmail.value = "";
  resetCode.value = "";
  resetNewPassword.value = "";
  resetConfirmPassword.value = "";
  resetVisible.value = true;
};

const closeReset = () => {
  resetVisible.value = false;
};

// Step 1 — send code
const handleSendCode = async () => {
  if (!resetEmail.value) {
    ElMessage.error("Enter your email");
    return;
  }
  resetLoading.value = true;
  try {
    await authService.requestPasswordReset(resetEmail.value);
    ElMessage.success(t("auth.codeSent"));
    resetStep.value = 2;
  } catch (err: any) {
    const msg = err.response?.data?.detail || "Error sending code";
    ElMessage.error(typeof msg === "string" ? msg : "Error sending code");
  } finally {
    resetLoading.value = false;
  }
};

// Step 2 — verify code, show new password form
const handleVerifyCode = () => {
  if (resetCode.value.length !== 6) {
    ElMessage.error("Enter the 6-digit code");
    return;
  }
  resetStep.value = 3;
};

// Step 3 — set new password
const handleConfirmReset = async () => {
  if (!resetNewPassword.value || resetNewPassword.value.length < 6) {
    ElMessage.error("Password must be at least 6 characters");
    return;
  }
  if (resetNewPassword.value !== resetConfirmPassword.value) {
    ElMessage.error(t("auth.passwordsDoNotMatch"));
    return;
  }
  resetLoading.value = true;
  try {
    await authService.confirmPasswordReset({
      email: resetEmail.value,
      code: resetCode.value,
      new_password: resetNewPassword.value,
    });
    ElMessage.success(t("auth.resetSuccess"));
    resetVisible.value = false;
  } catch (err: any) {
    const msg = err.response?.data?.detail || "Error resetting password";
    ElMessage.error(typeof msg === "string" ? msg : "Error resetting password");
  } finally {
    resetLoading.value = false;
  }
};
</script>

<template>
  <div class="login-container">
    <!-- Language & Theme -->
    <div class="theme-language-selector">
      <ThemeToggle />
      <el-select
        v-model="locale"
        @change="changeLanguage"
        size="small"
        style="margin-left: 12px"
      >
        <el-option
          v-for="lang in languages"
          :key="lang.value"
          :label="lang.label"
          :value="lang.value"
        />
      </el-select>
    </div>

    <!-- Login card -->
    <div class="login-card">
      <div class="logo-section">
        <el-icon :size="60" color="#3b82f6"><Edit /></el-icon>
        <h1>AI Test Platform</h1>
        <p class="subtitle">{{ t("common.welcome") }}</p>
      </div>

      <el-form :model="formData" class="login-form">
        <h2>{{ t("auth.loginTitle") }}</h2>

        <el-form-item :label="t('auth.role')">
          <el-radio-group v-model="formData.role" size="large">
            <el-radio-button value="teacher">{{ t("auth.teacher") }}</el-radio-button>
            <el-radio-button value="student">{{ t("auth.student") }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="formData.email"
            type="email"
            :placeholder="t('common.email')"
            size="large"
            prefix-icon="Message"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="formData.password"
            type="password"
            :placeholder="t('common.password')"
            size="large"
            prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loginLoading"
          @click="handleLogin"
          class="login-button"
        >
          {{ t("auth.signIn") }}
        </el-button>

        <div class="form-footer">
          <el-link type="primary" @click="openReset">
            {{ t("auth.forgotPassword") }}
          </el-link>
          <el-divider />
          <p class="register-link">
            {{ t("auth.noAccount") }}
            <el-link type="primary" @click="router.push('/register')">
              {{ t("auth.signUp") }}
            </el-link>
          </p>
        </div>
      </el-form>
    </div>

    <!-- ------------------------------------------------------------------ -->
    <!-- Forgot password modal                                               -->
    <!-- ------------------------------------------------------------------ -->
    <el-dialog
      v-model="resetVisible"
      :title="t('auth.resetPassword')"
      width="420px"
      :close-on-click-modal="false"
      class="reset-dialog"
    >
      <!-- Step indicators -->
      <el-steps :active="resetStep - 1" simple class="reset-steps">
        <el-step :title="'1'" />
        <el-step :title="'2'" />
        <el-step :title="'3'" />
      </el-steps>

      <!-- Step 1: Enter email -->
      <div v-if="resetStep === 1" class="reset-step">
        <p class="step-desc">{{ t("auth.resetStep1Desc") }}</p>
        <el-input
          v-model="resetEmail"
          type="email"
          :placeholder="t('common.email')"
          size="large"
          prefix-icon="Message"
          @keyup.enter="handleSendCode"
        />
        <div class="step-actions">
          <el-button @click="closeReset">{{ t("common.cancel") }}</el-button>
          <el-button
            type="primary"
            :loading="resetLoading"
            @click="handleSendCode"
          >
            {{ t("auth.sendCode") }}
          </el-button>
        </div>
      </div>

      <!-- Step 2: Enter code -->
      <div v-if="resetStep === 2" class="reset-step">
        <p class="step-desc">{{ t("auth.resetStep2Desc") }}</p>
        <el-input
          v-model="resetCode"
          :placeholder="t('auth.codeLabel')"
          size="large"
          maxlength="6"
          prefix-icon="Key"
          class="code-input"
          @keyup.enter="handleVerifyCode"
        />
        <div class="step-actions">
          <el-button @click="resetStep = 1">{{ t("common.back") }}</el-button>
          <el-button type="primary" @click="handleVerifyCode">
            {{ t("auth.verifyCode") }}
          </el-button>
        </div>
      </div>

      <!-- Step 3: New password -->
      <div v-if="resetStep === 3" class="reset-step">
        <p class="step-desc">{{ t("auth.resetStep3Title") }}</p>
        <el-input
          v-model="resetNewPassword"
          type="password"
          :placeholder="t('auth.newPassword')"
          size="large"
          prefix-icon="Lock"
          style="margin-bottom: 12px"
        />
        <el-input
          v-model="resetConfirmPassword"
          type="password"
          :placeholder="t('auth.confirmNewPassword')"
          size="large"
          prefix-icon="Lock"
          @keyup.enter="handleConfirmReset"
        />
        <div class="step-actions">
          <el-button @click="resetStep = 2">{{ t("common.back") }}</el-button>
          <el-button
            type="primary"
            :loading="resetLoading"
            @click="handleConfirmReset"
          >
            {{ t("common.confirm") }}
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--spacing-lg);
  position: relative;
}

.theme-language-selector {
  position: absolute;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.login-card {
  width: 100%;
  max-width: 450px;
  background: var(--color-background);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: var(--spacing-2xl);
  animation: fadeIn 0.5s ease-out;
}

.logo-section {
  text-align: center;
  margin-bottom: var(--spacing-2xl);

  h1 {
    font-size: 2rem;
    margin-top: var(--spacing-md);
    color: var(--color-dark);
  }

  .subtitle {
    color: var(--color-text-light);
    margin-top: var(--spacing-sm);
  }
}

.login-form {
  h2 {
    text-align: center;
    margin-bottom: var(--spacing-xl);
    color: var(--color-dark);
  }

  .el-form-item {
    margin-bottom: var(--spacing-lg);
  }

  .login-button {
    width: 100%;
    margin-top: var(--spacing-md);
    height: 45px;
    font-size: 1rem;
    font-weight: 600;
  }
}

.form-footer {
  margin-top: var(--spacing-xl);
  text-align: center;

  .register-link {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }
}

// Reset modal
.reset-steps {
  margin-bottom: 24px;
}

.reset-step {
  .step-desc {
    color: var(--color-text-light);
    margin-bottom: 16px;
    font-size: 0.9rem;
  }

  .code-input {
    font-size: 1.4rem;
    letter-spacing: 6px;
    text-align: center;

    :deep(input) {
      text-align: center;
      font-size: 1.4rem;
      letter-spacing: 6px;
    }
  }

  .step-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 20px;
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .login-card {
    padding: var(--spacing-xl);
  }

  .logo-section h1 {
    font-size: 1.5rem;
  }
}
</style>
