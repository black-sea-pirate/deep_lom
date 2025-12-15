<script setup lang="ts">
/**
 * QuestionEditorView
 *
 * Allows teachers to:
 * - View AI-generated questions
 * - Edit question text and options
 * - Add/remove questions
 * - Reorder questions
 * - Regenerate specific questions
 */
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Back,
  Plus,
  Delete,
  Edit,
  Refresh,
  Check,
  Close,
  Rank,
} from "@element-plus/icons-vue";
import api from "@/services/api";

interface Question {
  id: string;
  questionType: string;
  text: string;
  points: number;
  options?: string[];
  correctAnswer?: number | number[] | string | string[] | boolean;
  expectedKeywords?: string[];
  order: number;
  variantNumber?: number;
}

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const loading = ref(true);
const saving = ref(false);
const questions = ref<Question[]>([]);
const editingQuestion = ref<Question | null>(null);
const showEditDialog = ref(false);
const projectTitle = ref("");

// Variants
const availableVariants = ref<number[]>([]);
const selectedVariant = ref<number | null>(null);

const projectId = computed(() => route.params.id as string);

// Filtered questions by variant
const filteredQuestions = computed(() => {
  if (selectedVariant.value === null) {
    return questions.value;
  }
  return questions.value.filter(
    (q) => q.variantNumber === selectedVariant.value
  );
});

// Load questions
const loadQuestions = async () => {
  loading.value = true;
  try {
    // Get project info
    const projectRes = await api.get(`/projects/${projectId.value}`);
    projectTitle.value = projectRes.data.title;

    // Get questions
    const res = await api.get(`/projects/${projectId.value}/questions`);

    // Handle both old format (array) and new format (object with questions and variants)
    if (Array.isArray(res.data)) {
      questions.value = res.data;
      availableVariants.value = [1];
    } else {
      questions.value = res.data.questions || [];
      availableVariants.value = res.data.variants || [1];
    }

    // Default to first variant if multiple exist
    if (availableVariants.value.length > 0 && selectedVariant.value === null) {
      selectedVariant.value = availableVariants.value[0] ?? null;
    }
  } catch (error: any) {
    console.error("Failed to load questions:", error);
    if (error.response?.status === 404) {
      // No questions yet - that's okay
      questions.value = [];
      availableVariants.value = [];
    } else {
      ElMessage.error(t("common.loadError") || "Failed to load questions");
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadQuestions();
});

// Check if an option is the correct answer
const isCorrectOption = (question: Question, optionIndex: number): boolean => {
  const correct = question.correctAnswer;

  // For single-choice: correctAnswer is an index (number)
  if (question.questionType === "single-choice") {
    if (typeof correct === "number") {
      return correct === optionIndex;
    }
    // Sometimes it might be a string index
    if (typeof correct === "string" && !isNaN(parseInt(correct))) {
      return parseInt(correct) === optionIndex;
    }
    // Fallback: compare with option text (legacy format)
    if (typeof correct === "string" && question.options) {
      return question.options[optionIndex] === correct;
    }
  }

  // For multiple-choice: correctAnswer is an array of indices
  if (question.questionType === "multiple-choice") {
    if (Array.isArray(correct)) {
      return (
        (correct as (number | string)[]).includes(optionIndex) ||
        (correct as (number | string)[]).includes(optionIndex.toString())
      );
    }
  }

  // For true-false: not shown in options list
  if (question.questionType === "true-false") {
    return false;
  }

  return false;
};

// Check if question has any correct option marked
const hasCorrectOption = (question: Question): boolean => {
  if (!question.options || question.options.length === 0) return true;

  for (let i = 0; i < question.options.length; i++) {
    if (isCorrectOption(question, i)) return true;
  }
  return false;
};

// Question type labels
const questionTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    "single-choice": "Single Choice",
    "multiple-choice": "Multiple Choice",
    "short-answer": "Short Answer",
    "true-false": "True/False",
    matching: "Matching",
  };
  return labels[type] || type;
};

// Question type tag type
const questionTypeTag = (type: string): string => {
  const types: Record<string, string> = {
    "single-choice": "primary",
    "multiple-choice": "success",
    "short-answer": "warning",
    "true-false": "info",
    matching: "danger",
  };
  return types[type] || "info";
};

// Edit question
const openEditDialog = (question: Question) => {
  editingQuestion.value = { ...question };
  showEditDialog.value = true;
};

const saveQuestion = async () => {
  if (!editingQuestion.value) return;

  saving.value = true;
  try {
    await api.put(
      `/projects/${projectId.value}/questions/${editingQuestion.value.id}`,
      editingQuestion.value
    );

    // Update local state
    const index = questions.value.findIndex(
      (q) => q.id === editingQuestion.value!.id
    );
    if (index !== -1) {
      questions.value[index] = { ...editingQuestion.value };
    }

    showEditDialog.value = false;
    ElMessage.success(t("common.saved") || "Question saved");
  } catch (error) {
    console.error("Failed to save question:", error);
    ElMessage.error(t("common.saveError") || "Failed to save question");
  } finally {
    saving.value = false;
  }
};

// Delete question
const deleteQuestion = async (question: Question) => {
  try {
    await ElMessageBox.confirm(
      t("question.confirmDelete") || "Delete this question?",
      t("common.delete") || "Delete",
      {
        confirmButtonText: t("common.delete") || "Delete",
        cancelButtonText: t("common.cancel") || "Cancel",
        type: "warning",
      }
    );

    await api.delete(`/projects/${projectId.value}/questions/${question.id}`);
    questions.value = questions.value.filter((q) => q.id !== question.id);
    ElMessage.success(t("question.deleted") || "Question deleted");
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(t("common.deleteError") || "Failed to delete question");
    }
  }
};

// Add new question
const addQuestion = () => {
  editingQuestion.value = {
    id: "",
    questionType: "single-choice",
    text: "",
    points: 1,
    options: ["", "", "", ""],
    correctAnswer: "",
    order: questions.value.length,
  };
  showEditDialog.value = true;
};

const createQuestion = async () => {
  if (!editingQuestion.value) return;

  saving.value = true;
  try {
    const res = await api.post(
      `/projects/${projectId.value}/questions`,
      editingQuestion.value
    );

    questions.value.push(res.data);
    showEditDialog.value = false;
    ElMessage.success(t("question.created") || "Question created");
  } catch (error) {
    console.error("Failed to create question:", error);
    ElMessage.error(t("common.createError") || "Failed to create question");
  } finally {
    saving.value = false;
  }
};

// Add/remove option for multiple choice
const addOption = () => {
  if (editingQuestion.value && editingQuestion.value.options) {
    editingQuestion.value.options.push("");
  }
};

const removeOption = (index: number) => {
  if (editingQuestion.value && editingQuestion.value.options) {
    editingQuestion.value.options.splice(index, 1);
  }
};

const goBack = () => {
  router.push(`/teacher/project/${projectId.value}`);
};
</script>

<template>
  <div class="question-editor-view" v-loading="loading">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <el-button :icon="Back" @click="goBack">
          {{ t("common.back") || "Back" }}
        </el-button>
        <h1>{{ projectTitle }}</h1>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="addQuestion">
          {{ t("question.add") || "Add Question" }}
        </el-button>
      </div>
    </div>

    <!-- Variant Selector -->
    <div v-if="availableVariants.length > 1" class="variant-selector">
      <span class="variant-label"
        >{{ t("question.variant") || "Test Variant" }}:</span
      >
      <el-radio-group v-model="selectedVariant" size="default">
        <el-radio-button
          v-for="variant in availableVariants"
          :key="variant"
          :value="variant"
        >
          {{
            t("question.variantNumber", { n: variant }) || `Variant ${variant}`
          }}
        </el-radio-button>
      </el-radio-group>
      <span class="variant-info">
        ({{ filteredQuestions.length }}
        {{ t("question.questionsCount") || "questions" }})
      </span>
    </div>

    <!-- Questions List -->
    <div class="questions-container">
      <el-empty
        v-if="filteredQuestions.length === 0 && !loading"
        :description="
          t('question.noQuestions') ||
          'No questions yet. Add questions manually or generate them with AI.'
        "
      >
        <el-button type="primary" :icon="Plus" @click="addQuestion">
          {{ t("question.add") || "Add Question" }}
        </el-button>
      </el-empty>

      <div v-else class="questions-list">
        <el-card
          v-for="(question, index) in filteredQuestions"
          :key="question.id"
          class="question-card"
        >
          <div class="question-header">
            <div class="question-number">{{ index + 1 }}</div>
            <el-tag :type="questionTypeTag(question.questionType)" size="small">
              {{ questionTypeLabel(question.questionType) }}
            </el-tag>
            <el-tag type="info" size="small">
              {{ question.points }}
              {{ question.points === 1 ? "point" : "points" }}
            </el-tag>
            <div class="question-actions">
              <el-button
                size="small"
                :icon="Edit"
                @click="openEditDialog(question)"
              />
              <el-button
                size="small"
                type="danger"
                :icon="Delete"
                @click="deleteQuestion(question)"
              />
            </div>
          </div>

          <div class="question-text">{{ question.text }}</div>

          <!-- Options for choice questions -->
          <div v-if="question.options?.length" class="question-options">
            <div
              v-for="(option, optIndex) in question.options"
              :key="optIndex"
              class="option-item"
              :class="{
                correct: isCorrectOption(question, optIndex),
              }"
            >
              <span class="option-letter">{{
                String.fromCharCode(65 + optIndex)
              }}</span>
              <span class="option-text">{{ option }}</span>
              <el-icon
                v-if="isCorrectOption(question, optIndex)"
                class="correct-icon"
              >
                <Check />
              </el-icon>
            </div>
          </div>

          <!-- True/False correct answer -->
          <div
            v-if="question.questionType === 'true-false'"
            class="true-false-answer"
          >
            <span class="answer-label">Correct Answer:</span>
            <el-tag
              :type="question.correctAnswer === true ? 'success' : 'danger'"
              size="default"
            >
              {{
                question.correctAnswer === true
                  ? "True"
                  : question.correctAnswer === false
                  ? "False"
                  : "Not set"
              }}
            </el-tag>
          </div>

          <!-- Debug: Show raw correctAnswer if no options marked correct -->
          <div
            v-if="question.options?.length && !hasCorrectOption(question)"
            class="debug-answer"
          >
            <el-alert type="warning" :closable="false" show-icon>
              <template #title>
                <span
                  >No correct answer marked. Raw value:
                  {{ JSON.stringify(question.correctAnswer) }}</span
                >
              </template>
            </el-alert>
          </div>

          <!-- Expected keywords for short answer -->
          <div
            v-if="question.expectedKeywords?.length"
            class="expected-keywords"
          >
            <span class="keywords-label">Expected keywords:</span>
            <el-tag
              v-for="keyword in question.expectedKeywords"
              :key="keyword"
              size="small"
              type="success"
            >
              {{ keyword }}
            </el-tag>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Edit/Create Dialog -->
    <el-dialog
      v-model="showEditDialog"
      :title="
        editingQuestion?.id
          ? t('question.edit') || 'Edit Question'
          : t('question.add') || 'Add Question'
      "
      width="700px"
    >
      <el-form
        v-if="editingQuestion"
        :model="editingQuestion"
        label-position="top"
      >
        <el-form-item :label="t('question.type') || 'Question Type'">
          <el-select v-model="editingQuestion.questionType" style="width: 100%">
            <el-option value="single-choice" label="Single Choice" />
            <el-option value="multiple-choice" label="Multiple Choice" />
            <el-option value="short-answer" label="Short Answer" />
            <el-option value="true-false" label="True/False" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('question.text') || 'Question Text'" required>
          <el-input
            v-model="editingQuestion.text"
            type="textarea"
            :rows="3"
            :placeholder="
              t('question.textPlaceholder') || 'Enter question text...'
            "
          />
        </el-form-item>

        <el-form-item :label="t('question.points') || 'Points'">
          <el-input-number
            v-model="editingQuestion.points"
            :min="1"
            :max="10"
          />
        </el-form-item>

        <!-- Options for choice questions -->
        <el-form-item
          v-if="
            ['single-choice', 'multiple-choice'].includes(
              editingQuestion.questionType
            )
          "
          :label="t('question.options') || 'Options'"
        >
          <div class="options-editor">
            <div
              v-for="(option, index) in editingQuestion.options"
              :key="index"
              class="option-row"
            >
              <el-input
                v-model="editingQuestion.options![index]"
                :placeholder="`Option ${String.fromCharCode(65 + index)}`"
              />
              <el-button
                type="danger"
                :icon="Delete"
                circle
                size="small"
                @click="removeOption(index)"
                :disabled="(editingQuestion.options?.length || 0) <= 2"
              />
            </div>
            <el-button type="primary" :icon="Plus" @click="addOption">
              {{ t("question.addOption") || "Add Option" }}
            </el-button>
          </div>
        </el-form-item>

        <!-- Correct answer -->
        <el-form-item
          v-if="editingQuestion.questionType === 'single-choice'"
          :label="t('question.correctAnswer') || 'Correct Answer'"
        >
          <el-select
            v-model="editingQuestion.correctAnswer"
            style="width: 100%"
          >
            <el-option
              v-for="(option, index) in editingQuestion.options"
              :key="index"
              :value="option"
              :label="`${String.fromCharCode(65 + index)}: ${
                option || '(empty)'
              }`"
            />
          </el-select>
        </el-form-item>

        <!-- Expected keywords for short answer -->
        <el-form-item
          v-if="editingQuestion.questionType === 'short-answer'"
          :label="t('question.expectedKeywords') || 'Expected Keywords'"
        >
          <el-input
            :model-value="editingQuestion.expectedKeywords?.join(', ')"
            @update:model-value="
              editingQuestion.expectedKeywords = $event
                .split(',')
                .map((k: string) => k.trim())
                .filter(Boolean)
            "
            :placeholder="
              t('question.keywordsPlaceholder') ||
              'Enter keywords separated by commas'
            "
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEditDialog = false">
          {{ t("common.cancel") || "Cancel" }}
        </el-button>
        <el-button
          type="primary"
          @click="editingQuestion?.id ? saveQuestion() : createQuestion()"
          :loading="saving"
        >
          {{ t("common.save") || "Save" }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.question-editor-view {
  min-height: 100vh;
  background: var(--color-surface);
  padding: var(--spacing-xl);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
  gap: var(--spacing-md);

  .header-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);

    h1 {
      margin: 0;
      font-size: 1.5rem;
    }
  }
}

.variant-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-background);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;

  .variant-label {
    font-weight: 600;
    color: var(--color-text);
    white-space: nowrap;
  }

  .variant-info {
    color: var(--color-text-light);
    font-size: 0.9rem;
    margin-left: auto;
  }
}

.questions-container {
  max-width: 900px;
  margin: 0 auto;
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.question-card {
  .question-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);

    .question-number {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--color-primary);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
    }

    .question-actions {
      margin-left: auto;
      display: flex;
      gap: var(--spacing-xs);
    }
  }

  .question-text {
    font-size: 1.1rem;
    line-height: 1.6;
    margin-bottom: var(--spacing-md);
  }

  .question-options {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);

    .option-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      padding: var(--spacing-sm) var(--spacing-md);
      background: var(--color-surface);
      border-radius: var(--radius-sm);
      border: 1px solid var(--color-border);

      &.correct {
        background: rgba(103, 194, 58, 0.1);
        border-color: var(--color-success);
      }

      .option-letter {
        font-weight: 600;
        color: var(--color-primary);
      }

      .option-text {
        flex: 1;
      }

      .correct-icon {
        color: var(--color-success);
      }
    }
  }

  .expected-keywords {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-md);

    .keywords-label {
      font-size: 0.9rem;
      color: var(--color-text-light);
    }
  }
}

.options-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);

  .option-row {
    display: flex;
    gap: var(--spacing-sm);
  }
}

@media (max-width: 768px) {
  .question-editor-view {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
