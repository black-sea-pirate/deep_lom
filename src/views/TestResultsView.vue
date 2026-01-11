<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { testService } from "@/services";
import type {
  TestResults,
  TestResultQuestion,
  AIGradingCriterion,
} from "@/types";
import {
  Check,
  Close,
  Warning,
  Loading,
  Trophy,
  Star,
  Document,
} from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const testId = route.params.id as string;

const results = ref<TestResults | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const refreshInterval = ref<ReturnType<typeof setInterval> | null>(null);

// Computed
const scorePercentage = computed(() => {
  if (!results.value || results.value.maxScore === 0) return 0;
  return Math.round((results.value.score / results.value.maxScore) * 100);
});

const scoreIcon = computed(() => {
  if (scorePercentage.value >= 80) return "success";
  if (scorePercentage.value >= 60) return "warning";
  return "error";
});

const hasWrittenQuestions = computed(() => {
  if (!results.value) return false;
  return results.value.questions.some(
    (q) => q.type === "essay" || q.type === "short-answer"
  );
});

// Check if AI grading should be shown (only for essay/short-answer questions)
const showAiGradingPending = computed(() => {
  return results.value?.aiGradingPending && hasWrittenQuestions.value;
});

// Load results
const loadResults = async () => {
  try {
    results.value = await testService.getTestResults(testId);
    error.value = null;

    // Check if we need to keep refreshing (only if AI grading pending AND has essay/short-answer questions)
    const needsRefresh =
      results.value.aiGradingPending &&
      results.value.questions.some(
        (q) => q.type === "essay" || q.type === "short-answer"
      );

    // If AI grading is still pending for written questions, keep refreshing
    if (needsRefresh) {
      if (!refreshInterval.value) {
        refreshInterval.value = setInterval(loadResults, 5000); // Refresh every 5 seconds
      }
    } else {
      // Stop refreshing when grading is complete or no written questions
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value);
        refreshInterval.value = null;
      }
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to load test results";
  } finally {
    loading.value = false;
  }
};

// Get question type label
const getQuestionTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    "single-choice": t("results.singleChoice"),
    "multiple-choice": t("results.multipleChoice"),
    "true-false": t("results.trueFalse"),
    "short-answer": t("results.shortAnswer"),
    essay: t("results.essay"),
    matching: t("results.matching"),
  };
  return labels[type] || type;
};

// Format student answer for display
const formatStudentAnswer = (question: TestResultQuestion): string => {
  if (question.studentAnswer === null || question.studentAnswer === undefined) {
    return t("results.noAnswer");
  }

  switch (question.type) {
    case "single-choice":
      if (question.options && typeof question.studentAnswer === "number") {
        return (
          question.options[question.studentAnswer] || t("results.noAnswer")
        );
      }
      return String(question.studentAnswer);

    case "multiple-choice":
      if (question.options && Array.isArray(question.studentAnswer)) {
        return question.studentAnswer
          .map((idx: number) => question.options?.[idx])
          .filter(Boolean)
          .join(", ");
      }
      return String(question.studentAnswer);

    case "true-false":
      return question.studentAnswer ? t("results.true") : t("results.false");

    case "short-answer":
    case "essay":
      return String(question.studentAnswer);

    case "matching":
      if (Array.isArray(question.studentAnswer)) {
        return question.studentAnswer
          .map(
            (pair: { left: string; right: string }) =>
              `${pair.left} → ${pair.right}`
          )
          .join("; ");
      }
      return String(question.studentAnswer);

    default:
      return String(question.studentAnswer);
  }
};

// Format correct answer for display
const formatCorrectAnswer = (question: TestResultQuestion): string => {
  switch (question.type) {
    case "single-choice":
      if (question.options && typeof question.correctAnswer === "number") {
        return question.options[question.correctAnswer] || "-";
      }
      return "-";

    case "multiple-choice":
      if (question.options && Array.isArray(question.correctAnswer)) {
        return question.correctAnswer
          .map((idx: number) => question.options?.[idx])
          .filter(Boolean)
          .join(", ");
      }
      return "-";

    case "true-false":
      return question.correctAnswer ? t("results.true") : t("results.false");

    case "short-answer":
    case "essay":
      return t("results.aiGraded");

    case "matching":
      if (question.pairs) {
        return question.pairs
          .map((pair) => `${pair.left} → ${pair.right}`)
          .join("; ");
      }
      return "-";

    default:
      return "-";
  }
};

// Get criterion score color
const getCriterionScoreColor = (score: number): string => {
  if (score >= 4) return "#67c23a"; // Green
  if (score >= 3) return "#e6a23c"; // Orange
  return "#f56c6c"; // Red
};

// Get grading status tag type
const getGradingStatusType = (
  status?: string
): "success" | "warning" | "info" | "danger" => {
  switch (status) {
    case "completed":
      return "success";
    case "in_progress":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "info";
  }
};

onMounted(() => {
  loadResults();
});

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
});
</script>

<template>
  <div class="results-view">
    <el-container>
      <el-header>
        <h1>{{ t("results.title") }}</h1>
      </el-header>

      <el-main>
        <!-- Loading State -->
        <div v-if="loading" class="loading-container">
          <el-icon class="is-loading" :size="48"><Loading /></el-icon>
          <p>{{ t("results.loading") }}</p>
        </div>

        <!-- Error State -->
        <el-alert
          v-else-if="error"
          :title="error"
          type="error"
          show-icon
          :closable="false"
        />

        <!-- Results Content -->
        <template v-else-if="results">
          <!-- Score Card -->
          <el-card class="score-card">
            <el-result
              :icon="scoreIcon"
              :title="`${t('results.yourScore')}: ${results.score}/${
                results.maxScore
              }`"
              :sub-title="`${scorePercentage}%`"
            >
              <template #icon>
                <el-icon
                  :size="64"
                  :color="results.passed ? '#67c23a' : '#f56c6c'"
                >
                  <Trophy />
                </el-icon>
              </template>
              <template #extra>
                <div class="score-details">
                  <el-tag
                    :type="results.passed ? 'success' : 'danger'"
                    size="large"
                  >
                    {{
                      results.passed ? t("results.passed") : t("results.failed")
                    }}
                  </el-tag>

                  <!-- AI Grading Pending Alert -->
                  <el-alert
                    v-if="showAiGradingPending"
                    :title="t('results.aiGradingInProgress')"
                    type="warning"
                    show-icon
                    :closable="false"
                    style="margin-top: 1rem"
                  >
                    <template #default>
                      <p>{{ t("results.aiGradingPendingDesc") }}</p>
                      <el-icon class="is-loading"><Loading /></el-icon>
                    </template>
                  </el-alert>
                </div>

                <el-button
                  type="primary"
                  style="margin-top: 1rem"
                  @click="router.push('/student')"
                >
                  {{ t("results.backToDashboard") }}
                </el-button>
              </template>
            </el-result>
          </el-card>

          <!-- Test Info -->
          <el-card class="info-card">
            <el-descriptions :title="t('results.testInfo')" :column="2" border>
              <el-descriptions-item :label="t('results.projectTitle')">
                {{ results.projectTitle }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('results.status')">
                <el-tag>{{ results.status }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="t('results.startedAt')">
                {{
                  results.startedAt
                    ? new Date(results.startedAt).toLocaleString()
                    : "-"
                }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('results.completedAt')">
                {{
                  results.completedAt
                    ? new Date(results.completedAt).toLocaleString()
                    : "-"
                }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- Detailed Results -->
          <el-card class="questions-card">
            <template #header>
              <div class="card-header">
                <h2>{{ t("results.detailedResults") }}</h2>
                <el-tag type="info">
                  {{ results.questions.length }} {{ t("results.questions") }}
                </el-tag>
              </div>
            </template>

            <!-- Questions List -->
            <div class="questions-list">
              <el-collapse accordion>
                <el-collapse-item
                  v-for="(question, index) in results.questions"
                  :key="question.id"
                  :name="question.id"
                >
                  <template #title>
                    <div class="question-header">
                      <span class="question-number">{{ index + 1 }}.</span>
                      <el-icon
                        :color="question.isCorrect ? '#67c23a' : '#f56c6c'"
                        class="status-icon"
                      >
                        <Check v-if="question.isCorrect" />
                        <Close v-else />
                      </el-icon>
                      <span class="question-text-preview">
                        {{ question.text.substring(0, 80)
                        }}{{ question.text.length > 80 ? "..." : "" }}
                      </span>
                      <el-tag size="small" class="question-type-tag">
                        {{ getQuestionTypeLabel(question.type) }}
                      </el-tag>
                      <span class="question-score">
                        {{ question.score }}/{{ question.points }}
                      </span>
                    </div>
                  </template>

                  <div class="question-details">
                    <!-- Question Text -->
                    <div class="detail-section">
                      <h4>{{ t("results.question") }}</h4>
                      <p class="question-full-text">{{ question.text }}</p>
                    </div>

                    <!-- Your Answer -->
                    <div class="detail-section">
                      <h4>{{ t("results.yourAnswer") }}</h4>
                      <div
                        class="answer-box"
                        :class="{
                          correct: question.isCorrect,
                          incorrect: !question.isCorrect,
                        }"
                      >
                        <el-icon v-if="question.isCorrect" color="#67c23a"
                          ><Check
                        /></el-icon>
                        <el-icon v-else color="#f56c6c"><Close /></el-icon>
                        <span>{{ formatStudentAnswer(question) }}</span>
                      </div>
                    </div>

                    <!-- Correct Answer (for objective questions) -->
                    <div
                      v-if="!['essay', 'short-answer'].includes(question.type)"
                      class="detail-section"
                    >
                      <h4>{{ t("results.correctAnswer") }}</h4>
                      <div class="answer-box correct">
                        <el-icon color="#67c23a"><Check /></el-icon>
                        <span>{{ formatCorrectAnswer(question) }}</span>
                      </div>
                    </div>

                    <!-- AI Grading Section (for written questions) -->
                    <div
                      v-if="
                        ['essay', 'short-answer', 'matching'].includes(
                          question.type
                        )
                      "
                      class="ai-grading-section"
                    >
                      <h4>
                        <el-icon><Star /></el-icon>
                        {{ t("results.aiGrading") }}
                      </h4>

                      <!-- Grading Status -->
                      <div class="grading-status">
                        <el-tag
                          :type="getGradingStatusType(question.gradingStatus)"
                        >
                          {{
                            t(
                              `results.gradingStatus.${
                                question.gradingStatus || "pending"
                              }`
                            )
                          }}
                        </el-tag>
                        <span v-if="question.gradedBy" class="graded-by">
                          {{ t("results.gradedBy") }}: {{ question.gradedBy }}
                        </span>
                      </div>

                      <!-- Feedback -->
                      <div v-if="question.feedback" class="feedback-box">
                        <el-icon><Document /></el-icon>
                        <p>{{ question.feedback }}</p>
                      </div>

                      <!-- AI Grading Details -->
                      <template v-if="question.aiGrading">
                        <!-- Criteria Scores -->
                        <div
                          v-if="question.aiGrading.criteria?.length"
                          class="criteria-section"
                        >
                          <h5>{{ t("results.criteriaScores") }}</h5>
                          <div class="criteria-list">
                            <div
                              v-for="criterion in question.aiGrading.criteria"
                              :key="criterion.name"
                              class="criterion-item"
                            >
                              <div class="criterion-header">
                                <span class="criterion-name">{{
                                  criterion.name
                                }}</span>
                                <el-progress
                                  :percentage="(criterion.score / 5) * 100"
                                  :stroke-width="10"
                                  :color="
                                    getCriterionScoreColor(criterion.score)
                                  "
                                  :format="() => `${criterion.score}/5`"
                                  style="width: 120px"
                                />
                              </div>
                              <p class="criterion-feedback">
                                {{ criterion.feedback }}
                              </p>
                            </div>
                          </div>
                        </div>

                        <!-- Key Strengths -->
                        <div
                          v-if="question.aiGrading.keyStrengths?.length"
                          class="strengths-section"
                        >
                          <h5>{{ t("results.keyStrengths") }}</h5>
                          <ul class="strengths-list">
                            <li
                              v-for="(strength, idx) in question.aiGrading
                                .keyStrengths"
                              :key="idx"
                            >
                              <el-icon color="#67c23a"><Check /></el-icon>
                              {{ strength }}
                            </li>
                          </ul>
                        </div>

                        <!-- Areas for Improvement -->
                        <div
                          v-if="question.aiGrading.areasForImprovement?.length"
                          class="improvements-section"
                        >
                          <h5>{{ t("results.areasForImprovement") }}</h5>
                          <ul class="improvements-list">
                            <li
                              v-for="(area, idx) in question.aiGrading
                                .areasForImprovement"
                              :key="idx"
                            >
                              <el-icon color="#e6a23c"><Warning /></el-icon>
                              {{ area }}
                            </li>
                          </ul>
                        </div>

                        <!-- Detected Keywords -->
                        <div
                          v-if="question.aiGrading.detectedKeywords?.length"
                          class="keywords-section"
                        >
                          <h5>{{ t("results.detectedKeywords") }}</h5>
                          <div class="keywords-tags">
                            <el-tag
                              v-for="keyword in question.aiGrading
                                .detectedKeywords"
                              :key="keyword"
                              size="small"
                              type="success"
                            >
                              {{ keyword }}
                            </el-tag>
                          </div>
                        </div>
                      </template>

                      <!-- Pending Grading -->
                      <div
                        v-else-if="
                          question.gradingStatus === 'pending' ||
                          question.gradingStatus === 'in_progress'
                        "
                        class="pending-grading"
                      >
                        <el-icon class="is-loading"><Loading /></el-icon>
                        <span>{{ t("results.gradingInProgress") }}</span>
                      </div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-card>
        </template>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.results-view {
  min-height: 100vh;
  background-color: var(--color-surface);
}

.el-header {
  display: flex;
  align-items: center;
  background: var(--color-background);
  box-shadow: var(--shadow-sm);
  padding: 0 2rem;
}

.el-header h1 {
  margin: 0;
  color: var(--color-text);
}

.el-main {
  padding: 2rem;
  max-width: 1000px;
  margin: 0 auto;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--color-text-light);
}

.loading-container p {
  margin-top: 1rem;
}

.score-card {
  text-align: center;
  margin-bottom: 1.5rem;
}

.score-details {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.info-card {
  margin-bottom: 1.5rem;
}

.questions-card {
  margin-bottom: 2rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.questions-list {
  margin-top: 1rem;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding-right: 1rem;
}

.question-number {
  font-weight: 600;
  color: var(--color-text-light);
  min-width: 24px;
}

.status-icon {
  flex-shrink: 0;
}

.question-text-preview {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.question-type-tag {
  flex-shrink: 0;
}

.question-score {
  font-weight: 600;
  color: var(--color-primary);
  min-width: 50px;
  text-align: right;
}

.question-details {
  padding: 1rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
}

.detail-section {
  margin-bottom: 1.5rem;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  margin: 0 0 0.5rem;
  color: var(--color-text-light);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.question-full-text {
  margin: 0;
  line-height: 1.6;
  color: var(--color-text);
}

.answer-box {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: var(--radius-sm);
  background: var(--el-fill-color-light);
}

.answer-box.correct {
  background: rgba(103, 194, 58, 0.1);
  border: 1px solid rgba(103, 194, 58, 0.3);
}

.answer-box.incorrect {
  background: rgba(245, 108, 108, 0.1);
  border: 1px solid rgba(245, 108, 108, 0.3);
}

.answer-box span {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-word;
}

/* AI Grading Styles */
.ai-grading-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--el-border-color);
}

.ai-grading-section > h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  color: var(--color-primary);
}

.grading-status {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.graded-by {
  color: var(--color-text-light);
  font-size: 0.875rem;
}

.feedback-box {
  display: flex;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--el-fill-color-light);
  border-radius: var(--radius-sm);
  margin-bottom: 1rem;
}

.feedback-box p {
  margin: 0;
  flex: 1;
  line-height: 1.6;
}

.criteria-section,
.strengths-section,
.improvements-section,
.keywords-section {
  margin-top: 1rem;
}

.criteria-section h5,
.strengths-section h5,
.improvements-section h5,
.keywords-section h5 {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  color: var(--color-text);
}

.criteria-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.criterion-item {
  padding: 0.75rem;
  background: var(--el-fill-color-lighter);
  border-radius: var(--radius-sm);
}

.criterion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.criterion-name {
  font-weight: 500;
  text-transform: capitalize;
}

.criterion-feedback {
  margin: 0;
  font-size: 0.875rem;
  color: var(--color-text-light);
}

.strengths-list,
.improvements-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.strengths-list li,
.improvements-list li {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0;
}

.strengths-list li .el-icon,
.improvements-list li .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

.keywords-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pending-grading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: rgba(230, 162, 60, 0.1);
  border-radius: var(--radius-sm);
  color: #e6a23c;
}

/* Dark theme adjustments */
:global(.dark) .answer-box.correct {
  background: rgba(103, 194, 58, 0.15);
}

:global(.dark) .answer-box.incorrect {
  background: rgba(245, 108, 108, 0.15);
}

/* Responsive */
@media (max-width: 768px) {
  .el-main {
    padding: 1rem;
  }

  .question-header {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .question-text-preview {
    order: 10;
    width: 100%;
    flex: none;
  }

  .criterion-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
