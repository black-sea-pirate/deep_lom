<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import ThemeToggle from "@/components/ThemeToggle.vue";
import authService from "@/services/auth.service";

const router = useRouter();
const authStore = useAuthStore();
const { t, locale } = useI18n();

// ─── Mode toggle ──────────────────────────────────────────────────────────────
const isRegister = ref(false);
const switchMode = (mode: "login" | "register") => {
  isRegister.value = mode === "register";
};

// ─── Language ─────────────────────────────────────────────────────────────────
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

// ─── Login ────────────────────────────────────────────────────────────────────
const loginForm = ref({ email: "", password: "" });
const loginLoading = ref(false);

const handleLogin = async () => {
  if (!loginForm.value.email || !loginForm.value.password) {
    ElMessage.error("Please fill all fields");
    return;
  }
  loginLoading.value = true;
  try {
    const user = await authStore.login(
      loginForm.value.email,
      loginForm.value.password,
      "student"
    );
    ElMessage.success(t("common.welcome"));
    router.push(user.role === "teacher" ? "/teacher" : "/student");
  } catch (err: any) {
    const msg = err.response?.data?.detail;
    ElMessage.error(typeof msg === "string" ? msg : "Login failed");
  } finally {
    loginLoading.value = false;
  }
};

// ─── Register ─────────────────────────────────────────────────────────────────
const regForm = ref({
  firstName: "",
  lastName: "",
  email: "",
  password: "",
  confirmPassword: "",
  role: "student" as "teacher" | "student",
});
const regLoading = ref(false);

const handleRegister = async () => {
  const f = regForm.value;
  if (!f.firstName || !f.lastName || !f.email || !f.password) {
    ElMessage.error("Please fill all fields");
    return;
  }
  if (f.password !== f.confirmPassword) {
    ElMessage.error(t("auth.passwordsDoNotMatch"));
    return;
  }
  regLoading.value = true;
  try {
    await authStore.register(f.email, f.password, f.firstName, f.lastName, f.role);
    ElMessage.success("Registration successful! Please verify your email.");
    router.push("/verify-email");
  } catch (err: any) {
    const msg = err.response?.data?.detail;
    ElMessage.error(typeof msg === "string" ? msg : "Registration failed");
  } finally {
    regLoading.value = false;
  }
};

// ─── Forgot password ──────────────────────────────────────────────────────────
const resetVisible = ref(false);
const resetStep = ref<1 | 2 | 3>(1);
const resetLoading = ref(false);
const resetEmail = ref("");
const resetCode = ref("");
const resetNewPassword = ref("");
const resetConfirmPassword = ref("");

const openReset = () => {
  resetStep.value = 1;
  resetEmail.value = loginForm.value.email;
  resetCode.value = "";
  resetNewPassword.value = "";
  resetConfirmPassword.value = "";
  resetVisible.value = true;
};

const handleSendCode = async () => {
  if (!resetEmail.value) { ElMessage.error("Enter your email"); return; }
  resetLoading.value = true;
  try {
    await authService.requestPasswordReset(resetEmail.value);
    ElMessage.success(t("auth.codeSent"));
    resetStep.value = 2;
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "Error sending code");
  } finally { resetLoading.value = false; }
};

const handleVerifyCode = () => {
  if (resetCode.value.length !== 6) { ElMessage.error("Enter the 6-digit code"); return; }
  resetStep.value = 3;
};

const handleConfirmReset = async () => {
  if (resetNewPassword.value.length < 6) { ElMessage.error("Minimum 6 characters"); return; }
  if (resetNewPassword.value !== resetConfirmPassword.value) {
    ElMessage.error(t("auth.passwordsDoNotMatch")); return;
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
    ElMessage.error(err.response?.data?.detail ?? "Error resetting password");
  } finally { resetLoading.value = false; }
};

// ─── Welcome panel slider ─────────────────────────────────────────────────────
// To add your own slides: edit the title, desc, and icon fields below.
// Icon must be a valid Element Plus icon name (https://element-plus.org/en-US/component/icon.html).
// Later you can replace icons with <img> tags by editing the slide template.
const slides = [
  {
    icon: "EditPen",
    title: "AI Test Generation",
    desc: "Generate unique test variants from your documents in minutes",
  },
  {
    icon: "DataAnalysis",
    title: "Smart Grading",
    desc: "AI evaluates essays and short answers automatically",
  },
  {
    icon: "Lock",
    title: "Anti-Cheat System",
    desc: "Each student gets a unique variant — no copying possible",
  },
];

const currentSlide = ref(0);
let slideTimer: ReturnType<typeof setInterval> | null = null;

const goToSlide = (i: number) => { currentSlide.value = i; };
const nextSlide = () => { currentSlide.value = (currentSlide.value + 1) % slides.length; };

onMounted(() => { slideTimer = setInterval(nextSlide, 4000); });
onUnmounted(() => { if (slideTimer) clearInterval(slideTimer); });
</script>

<template>
  <div class="auth-page">

    <!-- Top-right controls -->
    <div class="page-controls">
      <ThemeToggle />
      <el-select v-model="locale" @change="changeLanguage" size="small" style="width: 120px">
        <el-option v-for="l in languages" :key="l.value" :label="l.label" :value="l.value" />
      </el-select>
    </div>

    <!-- ── Auth card ──────────────────────────────────────────────────────── -->
    <div class="auth-card" :class="{ 'is-register': isRegister }">

      <!-- Login form (left half) -->
      <div class="form-panel" :class="{ 'form-hidden': isRegister }">
        <div class="form-inner">
          <h2 class="form-title">{{ t("auth.loginTitle") }}</h2>

          <div class="field">
            <el-input
              v-model="loginForm.email"
              type="email"
              :placeholder="t('common.email')"
              size="large"
              prefix-icon="Message"
            />
          </div>
          <div class="field">
            <el-input
              v-model="loginForm.password"
              type="password"
              :placeholder="t('common.password')"
              size="large"
              prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </div>

          <el-link type="primary" class="forgot-link" @click="openReset">
            {{ t("auth.forgotPassword") }}
          </el-link>

          <el-button
            type="primary"
            size="large"
            :loading="loginLoading"
            class="submit-btn"
            @click="handleLogin"
          >
            {{ t("auth.signIn") }}
          </el-button>

          <!-- Mobile-only switch -->
          <p class="mobile-switch">
            {{ t("auth.noAccount") }}
            <el-link type="primary" @click="switchMode('register')">{{ t("auth.signUp") }}</el-link>
          </p>
        </div>
      </div>

      <!-- Register form (right half) -->
      <div class="form-panel register-side" :class="{ 'form-visible': isRegister }">
        <div class="form-inner">
          <h2 class="form-title">{{ t("auth.registerTitle") }}</h2>

          <div class="field name-row">
            <el-input
              v-model="regForm.firstName"
              :placeholder="t('common.firstName')"
              size="large"
              prefix-icon="User"
            />
            <el-input
              v-model="regForm.lastName"
              :placeholder="t('common.lastName')"
              size="large"
              prefix-icon="User"
            />
          </div>
          <div class="field">
            <el-input
              v-model="regForm.email"
              type="email"
              :placeholder="t('common.email')"
              size="large"
              prefix-icon="Message"
            />
          </div>
          <div class="field">
            <el-input
              v-model="regForm.password"
              type="password"
              :placeholder="t('common.password')"
              size="large"
              prefix-icon="Lock"
              show-password
            />
          </div>
          <div class="field">
            <el-input
              v-model="regForm.confirmPassword"
              type="password"
              :placeholder="t('auth.confirmNewPassword')"
              size="large"
              prefix-icon="Lock"
              show-password
              @keyup.enter="handleRegister"
            />
          </div>

          <div class="role-row">
            <el-radio-group v-model="regForm.role" size="small">
              <el-radio-button value="student">{{ t("auth.student") }}</el-radio-button>
              <el-radio-button value="teacher">{{ t("auth.teacher") }}</el-radio-button>
            </el-radio-group>
          </div>

          <el-button
            type="primary"
            size="large"
            :loading="regLoading"
            class="submit-btn"
            @click="handleRegister"
          >
            {{ t("auth.signUp") }}
          </el-button>

          <!-- Mobile-only switch -->
          <p class="mobile-switch">
            {{ t("auth.hasAccount") }}
            <el-link type="primary" @click="switchMode('login')">{{ t("auth.signIn") }}</el-link>
          </p>
        </div>
      </div>

      <!-- ── Sliding welcome panel ─────────────────────────────────────────── -->
      <div class="overlay-panel">

        <!-- Brand -->
        <div class="panel-brand">
          <el-icon :size="28" color="rgba(255,255,255,0.9)"><Edit /></el-icon>
          <span>Mentis</span>
        </div>

        <!-- Slider -->
        <div class="panel-slider">
          <div
            v-for="(slide, i) in slides"
            :key="i"
            class="slide"
            :class="{ 'slide-active': currentSlide === i }"
          >
            <div class="slide-icon-wrap">
              <el-icon :size="48" color="rgba(255,255,255,0.95)">
                <component :is="slide.icon" />
              </el-icon>
            </div>
            <h3>{{ slide.title }}</h3>
            <p>{{ slide.desc }}</p>
          </div>
        </div>

        <!-- Dots -->
        <div class="slide-dots">
          <button
            v-for="(_, i) in slides"
            :key="i"
            class="dot"
            :class="{ 'dot-active': currentSlide === i }"
            @click="goToSlide(i)"
          />
        </div>

        <!-- CTA -->
        <div class="panel-cta">
          <p>{{ isRegister ? t("auth.hasAccount") : t("auth.noAccount") }}</p>
          <button
            class="panel-btn"
            @click="switchMode(isRegister ? 'login' : 'register')"
          >
            {{ isRegister ? t("auth.signIn") : t("auth.signUp") }}
          </button>
        </div>

      </div>
      <!-- ─────────────────────────────────────────────────────────────────── -->

    </div>
    <!-- ───────────────────────────────────────────────────────────────────── -->

    <!-- Forgot password modal -->
    <el-dialog
      v-model="resetVisible"
      :title="t('auth.resetPassword')"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-steps :active="resetStep - 1" simple style="margin-bottom: 24px">
        <el-step title="1" /><el-step title="2" /><el-step title="3" />
      </el-steps>

      <!-- Step 1 -->
      <div v-if="resetStep === 1" class="reset-step">
        <p class="reset-desc">{{ t("auth.resetStep1Desc") }}</p>
        <el-input v-model="resetEmail" type="email" :placeholder="t('common.email')" size="large" prefix-icon="Message" @keyup.enter="handleSendCode" />
        <div class="reset-actions">
          <el-button @click="resetVisible = false">{{ t("common.cancel") }}</el-button>
          <el-button type="primary" :loading="resetLoading" @click="handleSendCode">{{ t("auth.sendCode") }}</el-button>
        </div>
      </div>

      <!-- Step 2 -->
      <div v-if="resetStep === 2" class="reset-step">
        <p class="reset-desc">{{ t("auth.resetStep2Desc") }}</p>
        <el-input v-model="resetCode" :placeholder="t('auth.codeLabel')" size="large" maxlength="6" prefix-icon="Key" class="code-input" @keyup.enter="handleVerifyCode" />
        <div class="reset-actions">
          <el-button @click="resetStep = 1">{{ t("common.back") }}</el-button>
          <el-button type="primary" @click="handleVerifyCode">{{ t("auth.verifyCode") }}</el-button>
        </div>
      </div>

      <!-- Step 3 -->
      <div v-if="resetStep === 3" class="reset-step">
        <p class="reset-desc">{{ t("auth.resetStep3Title") }}</p>
        <el-input v-model="resetNewPassword" type="password" :placeholder="t('auth.newPassword')" size="large" prefix-icon="Lock" show-password style="margin-bottom: 12px" />
        <el-input v-model="resetConfirmPassword" type="password" :placeholder="t('auth.confirmNewPassword')" size="large" prefix-icon="Lock" show-password @keyup.enter="handleConfirmReset" />
        <div class="reset-actions">
          <el-button @click="resetStep = 2">{{ t("common.back") }}</el-button>
          <el-button type="primary" :loading="resetLoading" @click="handleConfirmReset">{{ t("common.confirm") }}</el-button>
        </div>
      </div>
    </el-dialog>

  </div>
</template>

<style scoped lang="scss">
// ─── Page ──────────────────────────────────────────────────────────────────────
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(160deg, #1a1a2e 0%, #16213e 55%, #0f3460 100%);
  padding: 24px;
  position: relative;
}

.page-controls {
  position: fixed;
  top: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 200;
}

// ─── Card ──────────────────────────────────────────────────────────────────────
.auth-card {
  position: relative;
  width: 920px;
  min-height: 560px;
  background: var(--color-background);
  border-radius: 24px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  display: flex;
}

// ─── Form panels ───────────────────────────────────────────────────────────────
.form-panel {
  width: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 40px;
  transition: opacity 0.25s ease;

  &.form-hidden {
    opacity: 0;
    pointer-events: none;
  }
}

// Register panel starts as the right half but hidden until is-register
.register-side {
  opacity: 0;
  pointer-events: none;

  &.form-visible {
    opacity: 1;
    pointer-events: auto;
  }
}

.form-inner {
  width: 100%;
  max-width: 320px;
}

.form-title {
  text-align: center;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-dark);
  margin-bottom: 28px;
  letter-spacing: -0.3px;
}

// ─── Fields ────────────────────────────────────────────────────────────────────
.field {
  margin-bottom: 14px;
}

.name-row {
  display: flex;
  gap: 10px;

  .el-input { flex: 1; }
}

.role-row {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.forgot-link {
  display: block;
  text-align: right;
  font-size: 0.82rem;
  margin-bottom: 20px;
  margin-top: -4px;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 22px !important;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.4px;
}

.mobile-switch {
  display: none;
  text-align: center;
  margin-top: 20px;
  font-size: 0.88rem;
  color: var(--color-text-light);
}

// ─── Overlay / welcome panel ───────────────────────────────────────────────────
.overlay-panel {
  position: absolute;
  top: 0;
  left: 50%;          // anchored at the midpoint
  width: 50%;
  height: 100%;
  background: linear-gradient(145deg, #667eea 0%, #764ba2 100%);
  border-radius: 24px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 44px 36px;
  color: #fff;
  // Default (login mode): panel sits on the RIGHT half — no transform needed
  transform: translateX(0);
  transition: transform 0.65s cubic-bezier(0.77, 0, 0.18, 1);
}

// Register mode: panel slides fully to the LEFT half
.auth-card.is-register .overlay-panel {
  transform: translateX(-100%);
}

// ─── Brand inside panel ────────────────────────────────────────────────────────
.panel-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 32px;
  opacity: 0.95;
}

// ─── Slider ────────────────────────────────────────────────────────────────────
.panel-slider {
  position: relative;
  width: 100%;
  height: 180px;
  margin-bottom: 16px;
}

.slide {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.5s ease, transform 0.5s ease;
  pointer-events: none;

  &.slide-active {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }

  h3 {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 14px 0 8px;
    line-height: 1.3;
  }

  p {
    font-size: 0.85rem;
    opacity: 0.82;
    line-height: 1.55;
    max-width: 260px;
  }
}

.slide-icon-wrap {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

// ─── Dots ──────────────────────────────────────────────────────────────────────
.slide-dots {
  display: flex;
  gap: 6px;
  margin-bottom: 28px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.35);
  border: none;
  cursor: pointer;
  padding: 0;
  transition: width 0.3s ease, background 0.3s ease;

  &.dot-active {
    width: 22px;
    background: #fff;
  }
}

// ─── CTA ───────────────────────────────────────────────────────────────────────
.panel-cta {
  text-align: center;
  width: 100%;

  p {
    font-size: 0.88rem;
    opacity: 0.82;
    margin-bottom: 14px;
  }
}

.panel-btn {
  background: transparent;
  border: 2px solid rgba(255, 255, 255, 0.85);
  color: #fff;
  border-radius: 22px;
  padding: 10px 36px;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: background 0.25s, color 0.25s, border-color 0.25s;

  &:hover {
    background: #fff;
    border-color: #fff;
    color: #764ba2;
  }
}

// ─── Forgot password modal ─────────────────────────────────────────────────────
.reset-step {
  .reset-desc {
    color: var(--color-text-light);
    font-size: 0.9rem;
    margin-bottom: 16px;
    line-height: 1.5;
  }

  .code-input :deep(input) {
    text-align: center;
    font-size: 1.5rem;
    letter-spacing: 8px;
    font-weight: 600;
  }

  .reset-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 20px;
  }
}

// ─── Mobile ────────────────────────────────────────────────────────────────────
@media (max-width: 800px) {
  .auth-card {
    width: 100%;
    max-width: 400px;
    min-height: auto;
    display: block;
  }

  .form-panel {
    width: 100%;
    padding: 40px 28px;

    &.form-hidden { display: none; }
  }

  .register-side {
    display: none;
    &.form-visible { display: flex; opacity: 1; pointer-events: auto; }
  }

  .overlay-panel { display: none; }

  .mobile-switch { display: block; }
}
</style>
