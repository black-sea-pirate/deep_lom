<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useTestStore } from "@/stores/test";
import { useI18n } from "vue-i18n";

const route = useRoute();
const router = useRouter();
const testStore = useTestStore();
const { t } = useI18n();

const currentAnswer = ref<any>(null);
const testId = route.params.id as string;

onMounted(async () => {
  if (!testStore.currentTest) {
    await testStore.startTest(testId);
  }
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
  if (currentQuestion.value && currentAnswer.value !== null) {
    testStore.submitAnswer(currentQuestion.value.id, currentAnswer.value);
  }
};

const handleNext = () => {
  handleAnswer();
  testStore.nextQuestion();
  currentAnswer.value = null;
};

const handlePrevious = () => {
  handleAnswer();
  testStore.previousQuestion();
  currentAnswer.value = null;
};

const handleSubmitTest = async () => {
  handleAnswer();
  await testStore.submitTest();
  router.push(`/student/test/${testId}/results`);
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
  background: white;
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-lg);

  .header-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--spacing-md);

    h2 {
      margin: 0;
      color: var(--color-dark);
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
    color: var(--color-dark);
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
