<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useTestStore } from "@/stores/test";

const route = useRoute();
const router = useRouter();
const testStore = useTestStore();

const testId = route.params.id as string;

const results = computed(
  () =>
    testStore.currentTest || {
      score: 85,
      maxScore: 100,
      questions: [
        {
          id: "q1",
          text: "What is 2 + 2?",
          type: "single-choice",
          points: 10,
          correctAnswer: 0,
          userAnswer: 0,
          isCorrect: true,
        },
      ],
    }
);
</script>

<template>
  <div class="results-view">
    <el-container>
      <el-header>
        <h1>Test Results</h1>
      </el-header>
      <el-main>
        <el-card class="score-card">
          <el-result
            icon="success"
            :title="`Your Score: ${results.score}/${results.maxScore}`"
            :sub-title="`${Math.round(
              (results.score / results.maxScore) * 100
            )}%`"
          >
            <template #extra>
              <el-button type="primary" @click="router.push('/student')">
                Back to Dashboard
              </el-button>
            </template>
          </el-result>
        </el-card>

        <el-card style="margin-top: 2rem">
          <template #header>
            <h2>Detailed Results</h2>
          </template>
          <p>
            Detailed breakdown of each question will be shown here with feedback
            from AI.
          </p>
        </el-card>
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
  background: white;
  box-shadow: var(--shadow-sm);
}

.el-main {
  padding: 2rem;
  max-width: 900px;
  margin: 0 auto;
}

.score-card {
  text-align: center;
}
</style>
