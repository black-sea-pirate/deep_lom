<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import type { QuestionTypeConfig, Material, MaterialFolder } from "@/types";
import {
  Delete,
  CircleCheck,
  Loading,
  Folder,
  Document,
  Picture,
  FolderOpened,
  Back,
} from "@element-plus/icons-vue";
import { materialService } from "@/services/material.service";
import { projectService } from "@/services/project.service";

const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const currentStep = ref(0);
const loading = ref(false);
const loadingMaterials = ref(false);

// Progress tracking
const progressStep = ref("");
const progressPercent = ref(0);
const progressDetails = ref("");

// Material selection state
const browsingFolderId = ref<string | null>(null);
const selectedMaterialIds = ref<string[]>([]);
const selectedFolderIds = ref<string[]>([]);

// Data from API
const folders = ref<MaterialFolder[]>([]);
const materials = ref<Material[]>([]);

// Load materials and folders from API
const loadMaterialsData = async () => {
  loadingMaterials.value = true;
  try {
    const [foldersData, materialsData] = await Promise.all([
      materialService.getFolders(),
      materialService.getMaterials({ size: 1000 }),
    ]);
    folders.value = foldersData || [];
    materials.value = materialsData.items || [];
  } catch (error) {
    console.error("Failed to load materials:", error);
    ElMessage.error(t("materialsPage.loadError") || "Failed to load materials");
  } finally {
    loadingMaterials.value = false;
  }
};

const projectData = ref({
  title: "",
  groupName: "",
  description: "",
  timerMode: "total" as "total" | "per_question", // Timer mode selector
  totalTime: 60,
  timePerQuestion: 120,
  maxStudents: 30,
  numVariants: 3,
  testLanguage: "en", // Language for generated questions
  questionTypes: [
    { type: "single-choice", count: 10 },
    { type: "multiple-choice", count: 5 },
    { type: "short-answer", count: 3 },
  ] as QuestionTypeConfig[],
});

// Available languages for test generation
const testLanguages = computed(() => [
  { value: "en", label: t("teacher.langEnglish") || "English" },
  { value: "ru", label: t("teacher.langRussian") || "Russian" },
  { value: "ua", label: t("teacher.langUkrainian") || "Ukrainian" },
  { value: "pl", label: t("teacher.langPolish") || "Polish" },
]);

// Computed: current folder
const currentFolder = computed(() => {
  if (!browsingFolderId.value) return null;
  return folders.value.find((f) => f.id === browsingFolderId.value) || null;
});

// Computed: filtered materials by current folder view
const filteredMaterials = computed(() => {
  if (browsingFolderId.value) {
    return materials.value.filter((m) => m.folderId === browsingFolderId.value);
  }
  return materials.value.filter((m) => !m.folderId);
});

// Computed: count selected items
const selectedCount = computed(() => {
  const materialCount = selectedMaterialIds.value.length;
  const folderCount = selectedFolderIds.value.length;

  // Count materials in selected folders
  let folderMaterialsCount = 0;
  selectedFolderIds.value.forEach((folderId) => {
    folderMaterialsCount += materials.value.filter(
      (m) => m.folderId === folderId
    ).length;
  });

  return {
    materials: materialCount + folderMaterialsCount,
    folders: folderCount,
  };
});

// Computed: all selected materials (individual + from folders)
const allSelectedMaterials = computed(() => {
  const fromIndividual = materials.value.filter((m) =>
    selectedMaterialIds.value.includes(m.id)
  );
  const fromFolders = materials.value.filter(
    (m) => m.folderId && selectedFolderIds.value.includes(m.folderId)
  );

  // Deduplicate
  const allIds = new Set([
    ...fromIndividual.map((m) => m.id),
    ...fromFolders.map((m) => m.id),
  ]);
  return materials.value.filter((m) => allIds.has(m.id));
});

const questionTypes = computed(() => [
  { value: "single-choice", label: t("teacher.singleChoice") },
  { value: "multiple-choice", label: t("teacher.multipleChoice") },
  { value: "true-false", label: t("teacher.trueFalse") },
  { value: "short-answer", label: t("teacher.shortAnswer") },
  { value: "essay", label: t("teacher.essay") },
  { value: "matching", label: t("teacher.matching") },
]);

// Material selection helpers
const getFileIcon = (fileType: string) => {
  if (fileType.includes("image")) return Picture;
  return Document;
};

const isMaterialSelected = (materialId: string) => {
  return selectedMaterialIds.value.includes(materialId);
};

const isFolderSelected = (folderId: string) => {
  return selectedFolderIds.value.includes(folderId);
};

const toggleMaterialSelection = (materialId: string) => {
  const index = selectedMaterialIds.value.indexOf(materialId);
  if (index > -1) {
    selectedMaterialIds.value.splice(index, 1);
  } else {
    selectedMaterialIds.value.push(materialId);
  }
};

const toggleFolderSelection = (folderId: string, event: Event) => {
  event.stopPropagation();
  const index = selectedFolderIds.value.indexOf(folderId);
  if (index > -1) {
    selectedFolderIds.value.splice(index, 1);
  } else {
    selectedFolderIds.value.push(folderId);
  }
};

const openFolder = (folder: MaterialFolder) => {
  browsingFolderId.value = folder.id;
};

const goBack = () => {
  browsingFolderId.value = null;
};

const nextStep = () => {
  if (currentStep.value === 0 && !projectData.value.title) {
    ElMessage.warning("Please fill in project title");
    return;
  }
  if (currentStep.value === 1 && allSelectedMaterials.value.length === 0) {
    ElMessage.warning(
      t("wizard.selectMaterials") || "Please select at least one material"
    );
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
  // Validate materials selected
  if (selectedMaterialIds.value.length === 0) {
    ElMessage.warning(
      t("wizard.selectMaterialsFirst") || "Please select at least one material"
    );
    return;
  }

  loading.value = true;
  progressStep.value = "";
  progressPercent.value = 0;
  progressDetails.value = "";

  try {
    // Step 1: Create project
    progressStep.value = "Creating project...";
    progressPercent.value = 5;
    const project = await projectStore.createProject({
      title: projectData.value.title,
      groupName: projectData.value.groupName,
      description: projectData.value.description,
      settings: {
        timerMode: projectData.value.timerMode,
        totalTime: projectData.value.totalTime,
        timePerQuestion: projectData.value.timePerQuestion,
        maxStudents: projectData.value.maxStudents,
        numVariants: projectData.value.numVariants,
        testLanguage: projectData.value.testLanguage,
        questionTypes: projectData.value.questionTypes,
      },
    });

    // Step 2: Add materials to project
    progressStep.value = "Adding materials...";
    progressPercent.value = 10;
    progressDetails.value = `${selectedMaterialIds.value.length} materials`;
    await projectService.addMaterials(project.id, selectedMaterialIds.value);

    // Step 3: Configure settings (question types)
    progressStep.value = "Configuring settings...";
    progressPercent.value = 15;
    progressDetails.value = "";
    await projectService.configureSettings(project.id, {
      timerMode: projectData.value.timerMode,
      totalTime: projectData.value.totalTime,
      timePerQuestion: projectData.value.timePerQuestion,
      maxStudents: projectData.value.maxStudents,
      numVariants: projectData.value.numVariants,
      testLanguage: projectData.value.testLanguage,
      questionTypes: projectData.value.questionTypes,
    });

    // Step 4: Start vectorization
    progressStep.value = "Vectorizing materials...";
    progressPercent.value = 20;
    progressDetails.value = "Starting...";
    await projectService.startVectorization(project.id);

    // Poll vectorization status until complete
    let vectorizationComplete = false;
    let attempts = 0;
    const maxAttempts = 180; // 15 minutes max (5 sec intervals)

    while (!vectorizationComplete && attempts < maxAttempts) {
      await new Promise((resolve) => setTimeout(resolve, 5000)); // Wait 5 seconds
      const status = await projectService.getVectorizationStatus(project.id);

      // Update progress display
      progressPercent.value = 20 + Math.floor((status.progress || 0) * 0.5); // 20-70%
      progressDetails.value = `${status.materialsProcessed || 0}/${
        status.materialsTotal || 0
      } materials processed`;

      if (status.status === "completed") {
        vectorizationComplete = true;
        progressPercent.value = 70;
      } else if (status.status === "failed") {
        throw new Error(status.error || "Vectorization failed");
      }

      attempts++;
    }

    if (!vectorizationComplete) {
      // Don't throw error, just continue - AI can work with partial data
      console.warn(
        "Vectorization taking long, continuing with available data..."
      );
    }

    // Step 5: Generate tests
    progressStep.value = "Generating test questions with AI...";
    progressPercent.value = 75;
    progressDetails.value = "This may take 1-2 minutes";
    await projectStore.generateTests(project.id);

    progressPercent.value = 100;
    progressStep.value = "Complete!";
    progressDetails.value = "";

    ElMessage.success(t("wizard.testsGenerated"));
    router.push("/teacher");
  } catch (error: any) {
    console.error("Project creation error:", error);
    const message =
      error.response?.data?.detail ||
      error.message ||
      "Failed to create project";
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
};

// Load materials data on mount
onMounted(() => {
  loadMaterialsData();
});
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

        <!-- Step 2: Select Materials -->
        <div
          v-show="currentStep === 1"
          class="step"
          v-loading="loadingMaterials"
        >
          <h3>{{ t("wizard.selectMaterials") || "Select Materials" }}</h3>
          <p class="step-description">
            {{
              t("wizard.selectMaterialsHint") ||
              "Choose materials from your library to use for test generation"
            }}
          </p>

          <!-- Empty State -->
          <div
            v-if="
              !loadingMaterials &&
              materials.length === 0 &&
              folders.length === 0
            "
            class="empty-materials"
          >
            <el-empty
              :description="
                t('materialsPage.noMaterials') || 'No materials yet'
              "
            >
              <el-button
                type="primary"
                @click="router.push('/teacher/materials')"
              >
                {{ t("materialsPage.uploadFirst") || "Upload Materials" }}
              </el-button>
            </el-empty>
          </div>

          <template v-else>
            <!-- Selection Summary -->
            <div
              v-if="selectedCount.materials > 0 || selectedCount.folders > 0"
              class="selection-summary"
            >
              <el-tag type="success" size="large">
                {{ selectedCount.materials }}
                {{ selectedCount.materials === 1 ? "file" : "files" }}
                <span v-if="selectedCount.folders > 0">
                  ({{ selectedCount.folders }}
                  {{ selectedCount.folders === 1 ? "folder" : "folders" }})
                </span>
                {{ t("wizard.selected") || "selected" }}
              </el-tag>
            </div>

            <!-- Breadcrumb / Back Button -->
            <div v-if="currentFolder" class="folder-breadcrumb">
              <el-button :icon="Back" size="small" @click="goBack">
                {{ t("common.back") || "Back" }}
              </el-button>
              <span class="current-path">
                <el-icon><Folder /></el-icon>
                {{ currentFolder.name }}
              </span>
            </div>

            <!-- Folders Grid (only at root level) -->
            <div
              v-if="!browsingFolderId && folders.length > 0"
              class="folders-section"
            >
              <h4>{{ t("materialsPage.folders") || "Folders" }}</h4>
              <div class="folders-grid">
                <div
                  v-for="folder in folders"
                  :key="folder.id"
                  class="folder-item"
                  :class="{ selected: isFolderSelected(folder.id) }"
                  @click="openFolder(folder)"
                >
                  <el-checkbox
                    :model-value="isFolderSelected(folder.id)"
                    @click="toggleFolderSelection(folder.id, $event)"
                    class="folder-checkbox"
                  />
                  <div class="folder-icon">
                    <el-icon :size="32"><Folder /></el-icon>
                  </div>
                  <div class="folder-info">
                    <div class="folder-name">{{ folder.name }}</div>
                    <div class="folder-meta">
                      {{ folder.materialsCount }}
                      {{ folder.materialsCount === 1 ? "file" : "files" }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Materials List -->
            <div class="materials-section">
              <h4 v-if="!browsingFolderId">
                {{ t("materialsPage.files") || "Files" }} ({{
                  t("wizard.rootLevel") || "Root Level"
                }})
              </h4>
              <h4 v-else>{{ t("materialsPage.files") || "Files" }}</h4>

              <div v-if="filteredMaterials.length === 0" class="empty-state">
                <el-icon :size="48" class="empty-icon"
                  ><FolderOpened
                /></el-icon>
                <p>
                  {{
                    t("wizard.noMaterialsHere") ||
                    "No materials in this location"
                  }}
                </p>
                <el-button
                  v-if="!browsingFolderId"
                  type="primary"
                  @click="router.push('/teacher/materials')"
                >
                  {{ t("wizard.goToMaterials") || "Go to Materials" }}
                </el-button>
              </div>

              <div v-else class="materials-grid">
                <div
                  v-for="material in filteredMaterials"
                  :key="material.id"
                  class="material-item"
                  :class="{ selected: isMaterialSelected(material.id) }"
                  @click="toggleMaterialSelection(material.id)"
                >
                  <el-checkbox
                    :model-value="isMaterialSelected(material.id)"
                    class="material-checkbox"
                  />
                  <el-icon :size="24" class="material-icon">
                    <component :is="getFileIcon(material.fileType)" />
                  </el-icon>
                  <div class="material-info">
                    <div class="material-name">
                      {{ material.originalName || material.fileName }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Step 3: Configure Settings -->
        <div v-show="currentStep === 2" class="step">
          <h3>{{ t("wizard.configureSettings") }}</h3>
          <el-form :model="projectData" label-position="top">
            <!-- Timer Mode Selection -->
            <el-form-item :label="t('teacher.timerMode') || 'Timer Mode'">
              <el-radio-group
                v-model="projectData.timerMode"
                class="timer-mode-selector"
              >
                <el-radio-button value="total">
                  {{ t("teacher.totalTimeMode") || "Total Time" }}
                </el-radio-button>
                <el-radio-button value="per_question">
                  {{ t("teacher.perQuestionMode") || "Time Per Question" }}
                </el-radio-button>
              </el-radio-group>
              <div class="timer-mode-hint">
                {{
                  projectData.timerMode === "total"
                    ? t("teacher.totalTimeModeHint") ||
                      "Set a single time limit for the entire test"
                    : t("teacher.perQuestionModeHint") ||
                      "Set time limit for each question individually"
                }}
              </div>
            </el-form-item>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item
                  :label="t('teacher.totalTime')"
                  :class="{
                    'timer-disabled': projectData.timerMode !== 'total',
                  }"
                >
                  <el-input-number
                    v-model="projectData.totalTime"
                    :min="10"
                    :max="300"
                    :disabled="projectData.timerMode !== 'total'"
                  />
                  <span class="time-unit">{{
                    t("teacher.minutes") || "min"
                  }}</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item
                  :label="t('teacher.timePerQuestion')"
                  :class="{
                    'timer-disabled': projectData.timerMode !== 'per_question',
                  }"
                >
                  <el-input-number
                    v-model="projectData.timePerQuestion"
                    :min="30"
                    :max="600"
                    :disabled="projectData.timerMode !== 'per_question'"
                  />
                  <span class="time-unit">{{
                    t("teacher.seconds") || "sec"
                  }}</span>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item :label="t('teacher.maxStudents')">
                  <el-slider
                    v-model="projectData.maxStudents"
                    :min="1"
                    :max="100"
                    show-input
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item
                  :label="t('teacher.numVariants') || 'Test Variants'"
                >
                  <el-slider
                    v-model="projectData.numVariants"
                    :min="1"
                    :max="30"
                    show-input
                  />
                  <div class="setting-hint">
                    {{
                      t("teacher.numVariantsHint") ||
                      "Number of unique test versions to generate"
                    }}
                  </div>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item
                  :label="t('teacher.testLanguage') || 'Test Language'"
                >
                  <el-select
                    v-model="projectData.testLanguage"
                    size="large"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="lang in testLanguages"
                      :key="lang.value"
                      :label="lang.label"
                      :value="lang.value"
                    />
                  </el-select>
                  <div class="setting-hint">
                    {{
                      t("teacher.testLanguageHint") ||
                      "Language for generated questions"
                    }}
                  </div>
                </el-form-item>
              </el-col>
            </el-row>

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
            <div v-else class="loading-container">
              <el-progress
                :percentage="progressPercent"
                :stroke-width="8"
                :width="160"
                type="circle"
                class="progress-circle"
              >
                <template #default>
                  <el-icon class="is-loading" :size="48" color="#3b82f6">
                    <Loading />
                  </el-icon>
                </template>
              </el-progress>
            </div>
            <h3 class="progress-title">
              {{
                loading
                  ? progressStep || t("wizard.generatingTests")
                  : t("wizard.testsGenerated")
              }}
            </h3>
            <p v-if="loading && progressDetails" class="progress-details">
              {{ progressDetails }}
            </p>
            <p v-if="loading" class="progress-hint">
              Please wait, do not close this page
            </p>
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

.setting-hint {
  font-size: 0.8rem;
  color: var(--color-text-light);
  margin-top: var(--spacing-xs);
}

.generate-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  text-align: center;

  .loading-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .progress-circle {
    :deep(.el-progress__text) {
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  .progress-title {
    margin-top: var(--spacing-lg);
    color: var(--color-text);
  }

  .progress-details {
    color: var(--color-primary);
    font-size: 1rem;
    margin-top: var(--spacing-sm);
  }

  .progress-hint {
    color: var(--color-text-light);
    font-size: 0.875rem;
    margin-top: var(--spacing-xs);
  }
}

.wizard-actions {
  display: flex;
  justify-content: space-between;
}

.upload-demo {
  width: 100%;
}

// Step 2: Material Selection Styles
.step-description {
  color: var(--color-text-light);
  margin-bottom: var(--spacing-lg);
}

.selection-summary {
  margin-bottom: var(--spacing-lg);
}

.folder-breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-border);

  .current-path {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    color: var(--color-text);
    font-weight: 500;

    .el-icon {
      color: var(--color-warning);
    }
  }
}

.folders-section,
.materials-section {
  margin-bottom: var(--spacing-xl);

  h4 {
    margin-bottom: var(--spacing-md);
    color: var(--color-text);
    font-size: 0.95rem;
  }
}

.folders-grid,
.materials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.folder-item,
.material-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
  background: var(--color-background);

  &:hover {
    border-color: var(--color-primary);
    background: var(--color-surface);
  }

  &.selected {
    border-color: var(--color-primary);
    background: var(--color-primary-light);
  }

  .folder-checkbox,
  .material-checkbox {
    flex-shrink: 0;
  }
}

.folder-item {
  .folder-icon {
    color: var(--color-warning);
    flex-shrink: 0;
  }

  .folder-info {
    flex: 1;
    min-width: 0;

    .folder-name {
      font-weight: 500;
      color: var(--color-text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .folder-meta {
      font-size: 0.8rem;
      color: var(--color-text-light);
    }
  }
}

.material-item {
  .material-icon {
    color: var(--color-primary);
    flex-shrink: 0;
  }

  .material-info {
    flex: 1;
    min-width: 0;

    .material-name {
      font-weight: 500;
      color: var(--color-text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: 0.9rem;
    }
  }
}

.empty-state {
  text-align: center;
  padding: var(--spacing-2xl);
  color: var(--color-text-light);

  .empty-icon {
    color: var(--color-neutral);
    margin-bottom: var(--spacing-md);
  }

  p {
    margin-bottom: var(--spacing-md);
  }
}

.loading-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  margin: 0 auto;

  .el-icon {
    position: absolute;
  }

  .progress-circle {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
  }
}

.progress-details {
  font-size: 1rem;
  color: var(--color-primary);
  margin-top: var(--spacing-sm);
  font-weight: 500;
}

.progress-hint {
  font-size: 0.85rem;
  color: var(--color-text-light);
  margin-top: var(--spacing-xs);
}

/* Timer Mode Styles */
.timer-mode-selector {
  margin-bottom: var(--spacing-sm);
}

.timer-mode-hint {
  font-size: 0.85rem;
  color: var(--color-text-light);
  margin-top: var(--spacing-xs);
  font-style: italic;
}

.timer-disabled {
  opacity: 0.5;

  .el-input-number {
    background-color: var(--el-fill-color-light);
  }
}

.time-unit {
  margin-left: var(--spacing-xs);
  color: var(--color-text-light);
  font-size: 0.9rem;
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
