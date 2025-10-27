<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

const formData = ref({
  email: "",
  password: "",
  confirmPassword: "",
  firstName: "",
  lastName: "",
  role: "student" as "teacher" | "student",
});

const loading = ref(false);

const handleRegister = async () => {
  if (formData.value.password !== formData.value.confirmPassword) {
    ElMessage.error("Passwords do not match");
    return;
  }

  loading.value = true;
  try {
    await authStore.register(
      formData.value.email,
      formData.value.password,
      formData.value.firstName,
      formData.value.lastName,
      formData.value.role
    );

    ElMessage.success("Registration successful!");
    router.push(formData.value.role === "teacher" ? "/teacher" : "/student");
  } catch (error) {
    ElMessage.error("Registration failed");
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="register-container">
    <div class="register-card">
      <div class="logo-section">
        <el-icon :size="50" color="#3b82f6">
          <UserFilled />
        </el-icon>
        <h2>{{ t("auth.registerTitle") }}</h2>
      </div>

      <el-form :model="formData">
        <el-form-item :label="t('auth.role')">
          <el-radio-group v-model="formData.role" size="large">
            <el-radio-button value="teacher">{{
              t("auth.teacher")
            }}</el-radio-button>
            <el-radio-button value="student">{{
              t("auth.student")
            }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item :label="t('common.firstName')">
              <el-input v-model="formData.firstName" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('common.lastName')">
              <el-input v-model="formData.lastName" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item :label="t('common.email')">
          <el-input v-model="formData.email" type="email" />
        </el-form-item>

        <el-form-item :label="t('common.password')">
          <el-input v-model="formData.password" type="password" />
        </el-form-item>

        <el-form-item label="Confirm Password">
          <el-input v-model="formData.confirmPassword" type="password" />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="handleRegister"
          style="width: 100%"
        >
          {{ t("auth.signUp") }}
        </el-button>

        <div class="form-footer">
          <p>
            {{ t("auth.hasAccount") }}
            <el-link type="primary" @click="router.push('/login')">{{
              t("auth.signIn")
            }}</el-link>
          </p>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped lang="scss">
.register-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: var(--spacing-lg);
}

.register-card {
  width: 100%;
  max-width: 500px;
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  padding: var(--spacing-2xl);
}

.logo-section {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.form-footer {
  margin-top: var(--spacing-lg);
  text-align: center;
}
</style>
