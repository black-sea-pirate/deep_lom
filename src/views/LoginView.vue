<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import ThemeToggle from "@/components/ThemeToggle.vue";

const router = useRouter();
const authStore = useAuthStore();
const { t, locale } = useI18n();

const formData = ref({
  email: "",
  password: "",
  role: "student" as "teacher" | "student",
});

const loading = ref(false);

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

const handleLogin = async () => {
  if (!formData.value.email || !formData.value.password) {
    ElMessage.error(t("common.fillAllFields"));
    return;
  }

  loading.value = true;
  try {
    await authStore.login(
      formData.value.email,
      formData.value.password,
      formData.value.role
    );

    ElMessage.success(t("common.welcome"));

    // Redirect based on role
    if (formData.value.role === "teacher") {
      router.push("/teacher");
    } else {
      router.push("/student");
    }
  } catch (error) {
    ElMessage.error("Login failed");
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="login-container">
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

    <div class="login-card">
      <div class="logo-section">
        <el-icon :size="60" color="#3b82f6">
          <Edit />
        </el-icon>
        <h1>AI Test Platform</h1>
        <p class="subtitle">{{ t("common.welcome") }}</p>
      </div>

      <el-form :model="formData" class="login-form">
        <h2>{{ t("auth.loginTitle") }}</h2>

        <el-form-item :label="t('auth.role')">
          <el-radio-group v-model="formData.role" size="large">
            <el-radio-button value="teacher">
              {{ t("auth.teacher") }}
            </el-radio-button>
            <el-radio-button value="student">
              {{ t("auth.student") }}
            </el-radio-button>
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
          :loading="loading"
          @click="handleLogin"
          class="login-button"
        >
          {{ t("auth.signIn") }}
        </el-button>

        <div class="form-footer">
          <el-link type="primary">{{ t("auth.forgotPassword") }}</el-link>
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
