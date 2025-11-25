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

const router = useRouter();
const projectStore = useProjectStore();
const { t } = useI18n();

const currentStep = ref(0);
const loading = ref(false);

// Material selection state
const browsingFolderId = ref<string | null>(null);
const selectedMaterialIds = ref<string[]>([]);
const selectedFolderIds = ref<string[]>([]);

// Mock folders data (would come from API in production)
const folders = ref<MaterialFolder[]>([
  {
    id: "folder-1",
    name: "Mathematics",
    description: "Linear algebra and calculus materials",
    teacherId: "teacher-1",
    materialsCount: 2,
    createdAt: new Date("2024-11-01"),
  },
  {
    id: "folder-2",
    name: "Physics",
    description: "Quantum mechanics and thermodynamics",
    teacherId: "teacher-1",
    materialsCount: 1,
    createdAt: new Date("2024-11-05"),
  },
  {
    id: "folder-3",
    name: "Chemistry",
    description: "Organic chemistry notes",
    teacherId: "teacher-1",
    materialsCount: 0,
    createdAt: new Date("2024-11-10"),
  },
]);

// Mock materials data (would come from API in production)
const materials = ref<Material[]>([
  {
    id: "1",
    projectId: "",
    fileName: "Linear_Algebra_Chapter_1.pdf",
    fileType: "application/pdf",
    filePath: "/uploads/linear_algebra.pdf",
    uploadedAt: new Date("2024-11-20"),
    folderId: "folder-1",
  },
  {
    id: "2",
    projectId: "",
    fileName: "Quantum_Mechanics_Notes.docx",
    fileType:
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    filePath: "/uploads/quantum.docx",
    uploadedAt: new Date("2024-11-18"),
    folderId: "folder-2",
  },
  {
    id: "3",
    projectId: "proj-1",
    fileName: "Formulas_Reference.png",
    fileType: "image/png",
    filePath: "/uploads/formulas.png",
    uploadedAt: new Date("2024-11-15"),
    folderId: "folder-1",
  },
  {
    id: "4",
    projectId: "",
    fileName: "General_Notes.txt",
    fileType: "text/plain",
    filePath: "/uploads/general_notes.txt",
    uploadedAt: new Date("2024-11-22"),
    folderId: undefined,
  },
]);

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

        <!-- Step 2: Select Materials -->
        <div v-show="currentStep === 1" class="step">
          <h3>{{ t("wizard.selectMaterials") || "Select Materials" }}</h3>
          <p class="step-description">
            {{
              t("wizard.selectMaterialsHint") ||
              "Choose materials from your library to use for test generation"
            }}
          </p>

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
              <el-icon :size="48" class="empty-icon"><FolderOpened /></el-icon>
              <p>
                {{
                  t("wizard.noMaterialsHere") || "No materials in this location"
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
                  <div class="material-name">{{ material.fileName }}</div>
                </div>
              </div>
            </div>
          </div>
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
