<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import api from "@/services/api";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

const code = ref("");
const loading = ref(false);

// Resend cooldown
const COOLDOWN = 60;
const cooldown = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

const startCooldown = () => {
  cooldown.value = COOLDOWN;
  timer = setInterval(() => {
    cooldown.value--;
    if (cooldown.value <= 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  }, 1000);
};

onMounted(() => startCooldown());
onUnmounted(() => { if (timer) clearInterval(timer); });

const handleVerify = async () => {
  if (code.value.length !== 6) {
    ElMessage.error("Enter the 6-digit code");
    return;
  }
  loading.value = true;
  try {
    await api.post("/auth/verify-email", { code: code.value });
    // Refresh user info to get is_verified=true
    await authStore.checkAuth();
    ElMessage.success(t("auth.verifyEmailSuccess"));
    router.push(authStore.isTeacher ? "/teacher" : "/student");
  } catch (err: any) {
    const msg = err.response?.data?.detail || "Invalid code";
    ElMessage.error(typeof msg === "string" ? msg : "Invalid code");
  } finally {
    loading.value = false;
  }
};

const handleResend = async () => {
  if (cooldown.value > 0) return;
  try {
    await api.post("/auth/resend-verification");
    ElMessage.success(t("auth.codeSent"));
    startCooldown();
  } catch (err: any) {
    const msg = err.response?.data?.detail || "Error resending code";
    ElMessage.error(typeof msg === "string" ? msg : "Error resending code");
  }
};

</script>

<template>
  <div class="verify-container">
    <div class="verify-card">
      <div class="icon-section">
        <el-icon :size="64" color="#3b82f6"><Message /></el-icon>
      </div>

      <h2>{{ t("auth.verifyEmailTitle") }}</h2>
      <p class="desc">
        {{
          t("auth.verifyEmailDesc", { email: authStore.user?.email ?? "" })
        }}
      </p>

      <el-input
        v-model="code"
        :placeholder="t('auth.verifyEmailCode')"
        size="large"
        maxlength="6"
        class="code-input"
        @keyup.enter="handleVerify"
      />

      <el-button
        type="primary"
        size="large"
        :loading="loading"
        class="verify-btn"
        @click="handleVerify"
      >
        {{ t("auth.verifyEmailBtn") }}
      </el-button>

      <div class="footer-actions">
        <el-button
          link
          type="primary"
          :disabled="cooldown > 0"
          @click="handleResend"
        >
          {{
            cooldown > 0
              ? t("auth.verifyEmailResendWait", { sec: cooldown })
              : t("auth.verifyEmailResend")
          }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.verify-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
}

.verify-card {
  width: 100%;
  max-width: 420px;
  background: var(--color-background);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: 48px 40px;
  text-align: center;
  animation: fadeIn 0.4s ease-out;

  h2 {
    font-size: 1.6rem;
    margin: 16px 0 8px;
    color: var(--color-dark);
  }

  .desc {
    color: var(--color-text-light);
    font-size: 0.95rem;
    margin-bottom: 28px;
    line-height: 1.5;
  }
}

.icon-section {
  margin-bottom: 8px;
}

.code-input {
  margin-bottom: 16px;

  :deep(input) {
    text-align: center;
    font-size: 1.6rem;
    letter-spacing: 10px;
    font-weight: 600;
  }
}

.verify-btn {
  width: 100%;
  height: 46px;
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 20px;
}

.footer-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 0.9rem;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-16px); }
  to   { opacity: 1; transform: translateY(0); }
}
</style>
