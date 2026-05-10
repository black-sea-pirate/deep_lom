<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { Check } from "@element-plus/icons-vue";
import api from "@/services/api";

interface Question {
  id: string;
  questionType: string;
  text: string;
  points: number;
  options?: string[];
  correctAnswer?: number | number[] | string | string[] | boolean;
  expectedKeywords?: string[];
  pairs?: { left: string; right: string }[];
  order: number;
  variantNumber?: number;
}

interface PreviewQuestion {
  questionType: string;
  text: string;
  points: number;
  options?: string[];
  correctAnswer?: number | number[] | string | string[] | boolean;
  expectedKeywords?: string[];
  pairs?: { left: string; right: string }[];
}

const props = defineProps<{
  modelValue: boolean;
  question: Question | null;
  projectId: string;
  language?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "regenerated", question: PreviewQuestion): void;
}>();

const { t } = useI18n();

const loading = ref(false);
const selectedPreset = ref<string | null>(null);
const customInstruction = ref("");
const previewQuestion = ref<PreviewQuestion | null>(null);
const selectedLanguage = ref(props.language || "en");

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selectedLanguage.value = props.language || "en";
    } else {
      selectedPreset.value = null;
      customInstruction.value = "";
      previewQuestion.value = null;
      loading.value = false;
    }
  }
);

const presets = computed(() => [
  { key: "rephrase", label: t("regen.presetRephrase") },
  { key: "harder", label: t("regen.presetHarder") },
  { key: "easier", label: t("regen.presetEasier") },
  { key: "different_topic", label: t("regen.presetDifferent") },
]);

const selectPreset = (key: string) => {
  selectedPreset.value = selectedPreset.value === key ? null : key;
};

const handleGenerate = async () => {
  if (!props.question) return;

  loading.value = true;
  previewQuestion.value = null;

  try {
    const res = await api.post(
      `/projects/${props.projectId}/questions/${props.question.id}/regenerate`,
      {
        preset: selectedPreset.value,
        instruction: customInstruction.value.trim() || null,
        language: selectedLanguage.value,
      }
    );
    previewQuestion.value = res.data;
  } catch (err: any) {
    const detail = err.response?.data?.detail;
    ElMessage.error(detail || t("regen.error"));
  } finally {
    loading.value = false;
  }
};

const handleApply = () => {
  if (!previewQuestion.value) return;
  emit("regenerated", previewQuestion.value);
  emit("update:modelValue", false);
};

const handleClose = () => {
  emit("update:modelValue", false);
};

const isCorrectOption = (q: PreviewQuestion, idx: number): boolean => {
  const correct = q.correctAnswer;
  if (q.questionType === "single-choice") {
    return typeof correct === "number" && correct === idx;
  }
  if (q.questionType === "multiple-choice" && Array.isArray(correct)) {
    return (correct as number[]).includes(idx);
  }
  return false;
};
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="t('regen.title')"
    width="600px"
    :close-on-click-modal="false"
    @update:model-value="handleClose"
  >
    <div v-if="question" class="regen-dialog">
      <!-- Current question info -->
      <div class="current-question">
        <span class="current-label">{{ t("regen.currentQuestion") }}</span>
        <p class="current-text">{{ question.text }}</p>
      </div>

      <el-divider />

      <!-- Preset buttons -->
      <div class="presets-section">
        <p class="section-label">{{ t("regen.choosePreset") }}</p>
        <div class="preset-buttons">
          <el-button
            v-for="preset in presets"
            :key="preset.key"
            :type="selectedPreset === preset.key ? 'primary' : 'default'"
            size="small"
            @click="selectPreset(preset.key)"
          >
            {{ preset.label }}
          </el-button>
        </div>
      </div>

      <!-- Custom instruction -->
      <div class="custom-section">
        <p class="section-label">{{ t("regen.customInstruction") }}</p>
        <el-input
          v-model="customInstruction"
          type="textarea"
          :rows="3"
          :placeholder="t('regen.customPlaceholder')"
          :disabled="loading"
        />
      </div>

      <!-- Language selector -->
      <div class="language-section">
        <p class="section-label">{{ t("regen.language") }}</p>
        <el-select v-model="selectedLanguage" :disabled="loading" style="width: 200px">
          <el-option value="en" label="English" />
          <el-option value="ru" label="Русский" />
          <el-option value="ua" label="Українська" />
          <el-option value="pl" label="Polski" />
        </el-select>
      </div>

      <!-- Preview -->
      <div v-if="previewQuestion" class="preview-section">
        <el-divider />
        <p class="section-label">{{ t("regen.preview") }}</p>
        <div class="preview-card">
          <p class="preview-text">{{ previewQuestion.text }}</p>

          <!-- Options -->
          <div v-if="previewQuestion.options?.length" class="preview-options">
            <div
              v-for="(opt, idx) in previewQuestion.options"
              :key="idx"
              class="preview-option"
              :class="{ correct: isCorrectOption(previewQuestion, idx) }"
            >
              <span class="option-letter">{{ String.fromCharCode(65 + idx) }}</span>
              <span>{{ opt }}</span>
              <el-icon v-if="isCorrectOption(previewQuestion, idx)" class="correct-icon">
                <Check />
              </el-icon>
            </div>
          </div>

          <!-- True/False -->
          <div v-if="previewQuestion.questionType === 'true-false'" class="preview-tf">
            <span>{{ t("regen.correctAnswer") }}: </span>
            <el-tag :type="previewQuestion.correctAnswer ? 'success' : 'danger'" size="small">
              {{ previewQuestion.correctAnswer ? "True" : "False" }}
            </el-tag>
          </div>

          <!-- Keywords -->
          <div v-if="previewQuestion.expectedKeywords?.length" class="preview-keywords">
            <span class="keywords-label">{{ t("regen.keywords") }}: </span>
            <el-tag
              v-for="kw in previewQuestion.expectedKeywords"
              :key="kw"
              size="small"
              type="success"
              style="margin-right: 4px"
            >{{ kw }}</el-tag>
          </div>

          <!-- Matching pairs -->
          <div v-if="previewQuestion.pairs?.length" class="preview-pairs">
            <div
              v-for="(pair, i) in previewQuestion.pairs"
              :key="i"
              class="pair-item"
            >
              <span>{{ pair.left }}</span>
              <span class="pair-arrow">→</span>
              <span>{{ pair.right }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">{{ t("common.cancel") }}</el-button>
        <template v-if="!previewQuestion">
          <el-button
            type="primary"
            :loading="loading"
            :disabled="!selectedPreset && !customInstruction.trim()"
            @click="handleGenerate"
          >
            {{ loading ? t("regen.generating") : t("regen.generate") }}
          </el-button>
        </template>
        <template v-else>
          <el-button :loading="loading" @click="handleGenerate">
            {{ t("regen.tryAgain") }}
          </el-button>
          <el-button type="success" @click="handleApply">
            {{ t("regen.apply") }}
          </el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.regen-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.current-question {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 12px;
}

.current-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: block;
  margin-bottom: 6px;
}

.current-text {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  margin: 0 0 8px 0;
}

.preset-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.preview-card {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preview-text {
  margin: 0;
  font-weight: 500;
}

.preview-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 14px;
}

.preview-option.correct {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.option-letter {
  font-weight: 600;
  min-width: 18px;
}

.correct-icon {
  margin-left: auto;
}

.pair-item {
  display: flex;
  gap: 8px;
  font-size: 14px;
  align-items: center;
}

.pair-arrow {
  color: var(--el-text-color-secondary);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
