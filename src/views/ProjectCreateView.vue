<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import type { QuestionTypeConfig } from "@/types";

const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const currentStep = ref(0);
const loading = ref(false);

const projectData = ref({
  title: "",
  groupName: "",
  description: "",
  totalTime: 60,
  timePerQuestion: 120,
  maxStudents: 30,
  questionTypes: [
    { type: "single-choice", count: 10 },
    { type: "multiple-choice", count: 5 },
    { type: "short-answer", count: 3 },
  ] as QuestionTypeConfig[],
});

const questionTypes = [
  { value: "single-choice", label: "Single Choice" },
  { value: "multiple-choice", label: "Multiple Choice" },
  { value: "true-false", label: "True/False" },
  { value: "short-answer", label: "Short Answer" },
  { value: "essay", label: "Essay" },
  { value: "matching", label: "Matching" },
];

const nextStep = () => {
  if (currentStep.value === 0 && !projectData.value.title) {
    ElMessage.warning("Please fill in project title");
    return;
  }
  if (currentStep.value < 3) {
    currentStep.value++;
  }
};

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
};

const handleGenerate = async () => {
  loading.value = true;
  try {
    const project = await projectStore.createProject({
      title: projectData.value.title,
      groupName: projectData.value.groupName,
      description: projectData.value.description,
      settings: {
        totalTime: projectData.value.totalTime,
        timePerQuestion: projectData.value.timePerQuestion,
        maxStudents: projectData.value.maxStudents,
        questionTypes: projectData.value.questionTypes,
      },
    });

    await projectStore.generateTests(project.id);

    ElMessage.success(t("wizard.testsGenerated"));
    router.push("/teacher");
  } catch (error) {
    ElMessage.error("Failed to create project");
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="wizard-container">
    <el-card class="wizard-card">
      <template #header>
        <h2>{{ t("teacher.createProject") }}</h2>
      </template>

      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step :title="t('wizard.step1')" />
        <el-step :title="t('wizard.step2')" />
        <el-step :title="t('wizard.step3')" />
        <el-step :title="t('wizard.step4')" />
      </el-steps>

      <div class="step-content">
        <!-- Step 1: Project Info -->
        <div v-show="currentStep === 0" class="step">
          <h3>{{ t("wizard.projectInfo") }}</h3>
          <el-form :model="projectData" label-position="top">
            <el-form-item :label="t('teacher.projectTitle')" required>
              <el-input v-model="projectData.title" size="large" />
            </el-form-item>
            <el-form-item :label="t('teacher.groupName')" required>
              <el-input v-model="projectData.groupName" size="large" />
            </el-form-item>
            <el-form-item :label="t('teacher.description')">
              <el-input
                v-model="projectData.description"
                type="textarea"
                :rows="4"
              />
            </el-form-item>
          </el-form>
        </div>

        <!-- Step 2: Upload Materials -->
        <div v-show="currentStep === 1" class="step">
          <h3>{{ t("wizard.uploadFiles") }}</h3>
          <el-upload
            class="upload-demo"
            drag
            multiple
            action="#"
            :auto-upload="false"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              {{ t("wizard.dragDrop") }}<br />
              <em>{{ t("wizard.orBrowse") }}</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                {{ t("wizard.supportedFormats") }}
              </div>
            </template>
          </el-upload>
        </div>

        <!-- Step 3: Configure Settings -->
        <div v-show="currentStep === 2" class="step">
          <h3>{{ t("wizard.configureSettings") }}</h3>
          <el-form :model="projectData" label-position="top">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item :label="t('teacher.totalTime')">
                  <el-input-number
                    v-model="projectData.totalTime"
                    :min="10"
                    :max="300"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item :label="t('teacher.timePerQuestion')">
                  <el-input-number
                    v-model="projectData.timePerQuestion"
                    :min="30"
                    :max="600"
                  />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item :label="t('teacher.maxStudents')">
              <el-slider
                v-model="projectData.maxStudents"
                :min="1"
                :max="100"
                show-input
              />
            </el-form-item>

            <el-divider />

            <h4>{{ t("teacher.questionTypes") }}</h4>
            <div
              v-for="(qt, index) in projectData.questionTypes"
              :key="index"
              class="question-type-row"
            >
              <el-select v-model="qt.type" style="width: 200px">
                <el-option
                  v-for="type in questionTypes"
                  :key="type.value"
                  :label="type.label"
                  :value="type.value"
                />
              </el-select>
              <el-input-number v-model="qt.count" :min="1" :max="50" />
              <el-button
                type="danger"
                :icon="Delete"
                circle
                @click="projectData.questionTypes.splice(index, 1)"
              />
            </div>

            <el-button
              type="primary"
              @click="
                projectData.questionTypes.push({
                  type: 'single-choice',
                  count: 5,
                } as QuestionTypeConfig)
              "
              style="margin-top: 16px"
            >
              Add Question Type
            </el-button>
          </el-form>
        </div>

        <!-- Step 4: Generate -->
        <div v-show="currentStep === 3" class="step">
          <div class="generate-section">
            <el-icon v-if="!loading" :size="80" color="#10b981">
              <CircleCheck />
            </el-icon>
            <div v-else>
              <el-icon class="is-loading" :size="80" color="#3b82f6">
                <Loading />
              </el-icon>
            </div>
            <h3>
              {{
                loading
                  ? t("wizard.generatingTests")
                  : t("wizard.testsGenerated")
              }}
            </h3>
            <p v-if="!loading">
              Ready to generate tests for {{ projectData.title }}
            </p>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="wizard-actions">
          <el-button @click="router.push('/teacher')">
            {{ t("common.cancel") }}
          </el-button>
          <div>
            <el-button v-if="currentStep > 0" @click="prevStep">
              {{ t("common.back") }}
            </el-button>
            <el-button v-if="currentStep < 3" type="primary" @click="nextStep">
              {{ t("common.next") }}
            </el-button>
            <el-button
              v-else
              type="success"
              :loading="loading"
              @click="handleGenerate"
            >
              {{ t("wizard.step4") }}
            </el-button>
          </div>
        </div>
      </template>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.wizard-container {
  min-height: 100vh;
  background-color: var(--color-surface);
  padding: var(--spacing-xl);
  display: flex;
  align-items: center;
  justify-content: center;
}

.wizard-card {
  width: 100%;
  max-width: 900px;
}

.el-steps {
  margin: var(--spacing-xl) 0;
}

.step-content {
  min-height: 400px;
  padding: var(--spacing-xl) 0;
}

.step {
  h3 {
    margin-bottom: var(--spacing-xl);
    color: var(--color-dark);
  }
}

.question-type-row {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.generate-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  text-align: center;

  h3 {
    margin-top: var(--spacing-lg);
  }
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
}

.upload-demo {
  width: 100%;
}

@media (max-width: 768px) {
  .wizard-container {
    padding: var(--spacing-md);
  }

  .question-type-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
