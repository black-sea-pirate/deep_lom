<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useTestStore } from "@/stores/test";
import { useI18n } from "vue-i18n";

const route = useRoute();
const router = useRouter();
const testStore = useTestStore();
const { t } = useI18n();

const currentAnswer = ref<any>(null);
const testId = route.params.id as string;

// Initialize answer based on question type
const initializeAnswer = () => {
  const question =
    testStore.currentTest?.questions[testStore.currentQuestionIndex];
  if (!question) {
    currentAnswer.value = null;
    return;
  }

  // Check if we already have a saved answer for this question
  const existingAnswer = testStore.currentTest?.answers.find(
    (a) => a.questionId === question.id
  );

  if (existingAnswer) {
    currentAnswer.value = existingAnswer.answer;
  } else {
    // Initialize based on question type
    switch (question.type) {
      case "multiple-choice":
        currentAnswer.value = []; // ВАЖНО: массив для checkbox-group
        break;
      case "single-choice":
      case "true-false":
        currentAnswer.value = null;
        break;
      case "matching":
        // Initialize matching answer with empty selections for each left item
        const pairs = (question as any).pairs || [];
        currentAnswer.value = pairs.map((pair: any) => ({
          left: pair.left,
          right: "", // Will be selected by user
        }));
        break;
      default:
        currentAnswer.value = "";
    }
  }
};

// Watch for question changes to reinitialize answer
watch(
  () => testStore.currentQuestionIndex,
  () => {
    initializeAnswer();
  }
);

onMounted(async () => {
  if (!testStore.currentTest) {
    await testStore.startTest(testId);
  }
  initializeAnswer();
});

const currentQuestion = computed(() => {
  if (!testStore.currentTest) return null;
  return testStore.currentTest.questions[testStore.currentQuestionIndex];
});

const progress = computed(() => {
  if (!testStore.currentTest) return 0;
  return (
    ((testStore.currentQuestionIndex + 1) /
      testStore.currentTest.questions.length) *
    100
  );
});

const handleAnswer = () => {
  if (!currentQuestion.value) return;

  // Для multiple-choice проверяем что массив не пустой
  // Для matching проверяем что хотя бы одна пара выбрана
  // Для остальных типов - что значение не null/undefined/empty string
  let hasAnswer = false;
  if (currentQuestion.value.type === "multiple-choice") {
    hasAnswer =
      Array.isArray(currentAnswer.value) && currentAnswer.value.length > 0;
  } else if (currentQuestion.value.type === "matching") {
    hasAnswer =
      Array.isArray(currentAnswer.value) &&
      currentAnswer.value.some((pair: any) => pair.right !== "");
  } else {
    hasAnswer =
      currentAnswer.value !== null &&
      currentAnswer.value !== undefined &&
      currentAnswer.value !== "";
  }

  if (hasAnswer) {
    testStore.submitAnswer(currentQuestion.value.id, currentAnswer.value);
  }
};

// Matching question helpers
const shuffledRightOptions = ref<string[]>([]);

const getShuffledRightOptions = () => {
  const question = currentQuestion.value as any;
  if (!question?.pairs) return [];

  // Shuffle only once when question changes
  if (shuffledRightOptions.value.length === 0) {
    const options = question.pairs.map((p: any) => p.right);
    // Fisher-Yates shuffle
    for (let i = options.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [options[i], options[j]] = [options[j], options[i]];
    }
    shuffledRightOptions.value = options;
  }
  return shuffledRightOptions.value;
};

const isRightOptionUsed = (option: string, currentIndex: number) => {
  if (!Array.isArray(currentAnswer.value)) return false;
  return currentAnswer.value.some(
    (pair: any, idx: number) => idx !== currentIndex && pair.right === option
  );
};

// Reset shuffled options when question changes
watch(
  () => testStore.currentQuestionIndex,
  () => {
    shuffledRightOptions.value = [];
  }
);

const handleNext = () => {
  handleAnswer();
  testStore.nextQuestion();
  // initializeAnswer вызовется через watch
};

const handlePrevious = () => {
  handleAnswer();
  testStore.previousQuestion();
  // initializeAnswer вызовется через watch
};

const handleSubmitTest = async () => {
  handleAnswer();
  await testStore.submitTest();
  // Use the actual test ID from the store, not the project ID from URL
  const actualTestId = testStore.currentTest?.id;
  if (actualTestId) {
    router.push(`/student/test/${actualTestId}/results`);
  } else {
    router.push("/student/dashboard");
  }
};
</script>

<template>
  <div class="test-container">
    <div class="test-header">
      <el-progress :percentage="progress" :show-text="false" />
      <div class="header-info">
        <div>
          <h2>{{ t("student.testInProgress") }}</h2>
          <p>
            {{ t("student.question") }}
            {{ testStore.currentQuestionIndex + 1 }} {{ t("student.of") }}
            {{ testStore.currentTest?.questions.length }}
          </p>
        </div>
        <div class="timer">
          <el-icon><Timer /></el-icon>
          <span
            >{{ Math.floor(testStore.timeRemaining / 60) }}:{{
              (testStore.timeRemaining % 60).toString().padStart(2, "0")
            }}</span
          >
        </div>
      </div>
    </div>

    <div class="test-content" v-if="currentQuestion">
      <el-card class="question-card">
        <h3 class="question-text">{{ currentQuestion.text }}</h3>
        <div class="points">{{ currentQuestion.points }} points</div>

        <!-- Single Choice -->
        <div
          v-if="currentQuestion.type === 'single-choice'"
          class="answer-section"
        >
          <el-radio-group v-model="currentAnswer" size="large">
            <el-radio
              v-for="(option, index) in currentQuestion.options"
              :key="index"
              :value="index"
              border
            >
              {{ option }}
            </el-radio>
          </el-radio-group>
        </div>

        <!-- Multiple Choice -->
        <div
          v-else-if="currentQuestion.type === 'multiple-choice'"
          class="answer-section"
        >
          <el-checkbox-group v-model="currentAnswer">
            <el-checkbox
              v-for="(option, index) in currentQuestion.options"
              :key="index"
              :value="index"
              border
            >
              {{ option }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <!-- True/False -->
        <div
          v-else-if="currentQuestion.type === 'true-false'"
          class="answer-section"
        >
          <el-radio-group v-model="currentAnswer" size="large">
            <el-radio :value="true" border>True</el-radio>
            <el-radio :value="false" border>False</el-radio>
          </el-radio-group>
        </div>

        <!-- Matching -->
        <div
          v-else-if="currentQuestion.type === 'matching'"
          class="answer-section matching-section"
        >
          <div class="matching-instructions">
            {{
              t("student.matchingInstructions") ||
              "Match each item on the left with the correct item on the right"
            }}
          </div>
          <div class="matching-container">
            <div
              v-for="(pair, index) in (currentAnswer as any[])"
              :key="index"
              class="matching-row"
            >
              <div class="matching-left">
                <span class="matching-index">{{ (index as number) + 1 }}.</span>
                <span class="matching-term">{{ pair.left }}</span>
              </div>
              <div class="matching-arrow">→</div>
              <div class="matching-right">
                <el-select
                  v-model="currentAnswer[index].right"
                  :placeholder="t('student.selectMatch') || 'Select match'"
                  clearable
                  size="large"
                >
                  <el-option
                    v-for="(rightOption, rIndex) in getShuffledRightOptions()"
                    :key="rIndex"
                    :label="rightOption"
                    :value="rightOption"
                    :disabled="isRightOptionUsed(rightOption, index as number)"
                  />
                </el-select>
              </div>
            </div>
          </div>
        </div>

        <!-- Short Answer & Essay -->
        <div v-else class="answer-section">
          <el-input
            v-model="currentAnswer"
            type="textarea"
            :rows="currentQuestion.type === 'essay' ? 10 : 4"
            placeholder="Type your answer here..."
          />
        </div>
      </el-card>

      <div class="navigation-buttons">
        <el-button
          :disabled="testStore.currentQuestionIndex === 0"
          @click="handlePrevious"
        >
          {{ t("student.previousQuestion") }}
        </el-button>

        <el-button
          v-if="
            testStore.currentQuestionIndex <
            (testStore.currentTest?.questions.length || 0) - 1
          "
          type="primary"
          @click="handleNext"
        >
          {{ t("student.nextQuestion") }}
        </el-button>

        <el-button v-else type="success" @click="handleSubmitTest">
          {{ t("student.submitTest") }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.test-container {
  min-height: 100vh;
  background-color: var(--color-surface);
}

.test-header {
  background: var(--color-background);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-lg);

  .el-progress {
    :deep(.el-progress-bar__outer) {
      background-color: var(--color-border);
    }
  }

  .header-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--spacing-md);

    h2 {
      margin: 0;
      color: var(--color-text);
    }

    p {
      color: var(--color-text-light);
      margin: 0;
    }

    .timer {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--color-primary);
    }
  }
}

.test-content {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--spacing-2xl);
}

.question-card {
  margin-bottom: var(--spacing-xl);

  .question-text {
    font-size: 1.3rem;
    color: var(--color-text);
    margin-bottom: var(--spacing-md);
    line-height: 1.6;
  }

  .points {
    color: var(--color-accent);
    font-weight: 600;
    margin-bottom: var(--spacing-xl);
  }

  .answer-section {
    margin-top: var(--spacing-xl);

    .el-radio,
    .el-checkbox {
      display: block;
      width: 100%;
      margin-bottom: var(--spacing-md);
      padding: var(--spacing-lg);
    }
  }

  .matching-section {
    .matching-instructions {
      color: var(--color-text-light);
      margin-bottom: var(--spacing-lg);
      font-style: italic;
    }

    .matching-container {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .matching-row {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
      padding: var(--spacing-md);
      background: var(--color-surface);
      border-radius: var(--radius-md);
      border: 1px solid var(--color-border);
    }

    .matching-left {
      flex: 1;
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);

      .matching-index {
        font-weight: 600;
        color: var(--color-primary);
        min-width: 24px;
      }

      .matching-term {
        color: var(--color-text);
      }
    }

    .matching-arrow {
      color: var(--color-text-light);
      font-size: 1.2rem;
      padding: 0 var(--spacing-sm);
    }

    .matching-right {
      flex: 1;

      .el-select {
        width: 100%;
      }
    }
  }
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);

  .el-button {
    flex: 1;
    height: 50px;
    font-size: 1rem;
  }
}

@media (max-width: 768px) {
  .test-content {
    padding: var(--spacing-md);
  }

  .navigation-buttons {
    flex-direction: column;
  }
}
</style>
