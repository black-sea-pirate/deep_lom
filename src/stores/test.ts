import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Test, Question, Answer } from "@/types";
import {
  testService,
  type SubmitAnswerRequest,
  type TestSubmissionResponse,
} from "@/services";

export const useTestStore = defineStore("test", () => {
  const tests = ref<Test[]>([]);
  const currentTest = ref<Test | null>(null);
  const currentQuestionIndex = ref(0);
  const timeRemaining = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const submitting = ref(false);

  // Timer interval reference
  let timerInterval: ReturnType<typeof setInterval> | null = null;

  // Computed
  const currentQuestion = computed((): Question | null => {
    if (!currentTest.value || currentTest.value.questions.length === 0) {
      return null;
    }
    return currentTest.value.questions[currentQuestionIndex.value] || null;
  });

  const totalQuestions = computed(
    () => currentTest.value?.questions.length || 0
  );

  const answeredQuestions = computed(() => {
    if (!currentTest.value) return 0;
    return currentTest.value.answers.length;
  });

  const isLastQuestion = computed(() => {
    return currentQuestionIndex.value === totalQuestions.value - 1;
  });

  const isFirstQuestion = computed(() => {
    return currentQuestionIndex.value === 0;
  });

  const progress = computed(() => {
    if (totalQuestions.value === 0) return 0;
    return Math.round((answeredQuestions.value / totalQuestions.value) * 100);
  });

  const formattedTimeRemaining = computed(() => {
    const minutes = Math.floor(timeRemaining.value / 60);
    const seconds = timeRemaining.value % 60;
    return `${minutes.toString().padStart(2, "0")}:${seconds
      .toString()
      .padStart(2, "0")}`;
  });

  /**
   * Fetch available tests for student
   */
  const fetchAvailableTests = async () => {
    loading.value = true;
    error.value = null;

    try {
      const availableTests = await testService.getAvailableTests();
      tests.value = availableTests;
      return availableTests;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to fetch tests";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Fetch completed tests for student
   */
  const fetchCompletedTests = async () => {
    loading.value = true;
    error.value = null;

    try {
      const completedTests = await testService.getCompletedTests();
      return completedTests;
    } catch (err: any) {
      error.value =
        err.response?.data?.detail || "Failed to fetch completed tests";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Start taking a test
   */
  const startTest = async (projectId: string) => {
    loading.value = true;
    error.value = null;

    try {
      const test = await testService.startTest(projectId);
      currentTest.value = test;
      currentQuestionIndex.value = 0;

      // Calculate time remaining based on timer mode
      // timerMode: 'total' - use totalTime (minutes)
      // timerMode: 'per_question' - use timePerQuestion (seconds) * number of questions
      if (test.timerMode === "per_question" && test.timePerQuestion) {
        // Time per question mode: timePerQuestion is in seconds
        timeRemaining.value = test.timePerQuestion * test.questions.length;
      } else {
        // Total time mode (default): totalTime is in minutes
        const totalMinutes = test.totalTime || 60; // Default 60 minutes
        timeRemaining.value = totalMinutes * 60; // Convert to seconds
      }

      // Start timer
      startTimer();

      return test;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to start test";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Get current test by ID
   */
  const getTest = async (testId: string) => {
    loading.value = true;
    error.value = null;

    try {
      const test = await testService.getCurrentTest(testId);
      currentTest.value = test;
      currentQuestionIndex.value = 0;
      return test;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to get test";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Submit answer for current question
   */
  const submitAnswer = async (questionId: string, answer: any) => {
    if (!currentTest.value) return;

    try {
      // Update local state immediately
      const existingAnswerIndex = currentTest.value.answers.findIndex(
        (a) => a.questionId === questionId
      );

      const newAnswer: Answer = {
        questionId,
        answer,
      };

      if (existingAnswerIndex !== -1) {
        currentTest.value.answers[existingAnswerIndex] = newAnswer;
      } else {
        currentTest.value.answers.push(newAnswer);
      }

      // Send to server
      const answerRequest: SubmitAnswerRequest = {
        questionId,
        answer,
      };

      await testService.submitAnswer(currentTest.value.id, answerRequest);
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to submit answer";
      // Don't throw - allow user to continue
    }
  };

  /**
   * Submit entire test
   */
  const submitTest = async (): Promise<TestSubmissionResponse | null> => {
    if (!currentTest.value) return null;

    submitting.value = true;
    error.value = null;

    try {
      // Stop timer
      stopTimer();

      const result = await testService.submitTest(currentTest.value.id);

      // Update current test status
      currentTest.value.status = "completed";
      currentTest.value.score = result.score;
      currentTest.value.completedAt = new Date();

      return result;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to submit test";
      throw err;
    } finally {
      submitting.value = false;
    }
  };

  /**
   * Get test results
   */
  const getTestResults = async (testId: string) => {
    loading.value = true;
    error.value = null;

    try {
      const test = await testService.getTestResults(testId);
      return test;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to get test results";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Navigate to next question
   */
  const nextQuestion = () => {
    if (
      currentTest.value &&
      currentQuestionIndex.value < currentTest.value.questions.length - 1
    ) {
      currentQuestionIndex.value++;
    }
  };

  /**
   * Navigate to previous question
   */
  const previousQuestion = () => {
    if (currentQuestionIndex.value > 0) {
      currentQuestionIndex.value--;
    }
  };

  /**
   * Navigate to specific question by index
   */
  const goToQuestion = (index: number) => {
    if (
      currentTest.value &&
      index >= 0 &&
      index < currentTest.value.questions.length
    ) {
      currentQuestionIndex.value = index;
    }
  };

  /**
   * Start the test timer
   */
  const startTimer = () => {
    stopTimer(); // Clear any existing timer

    timerInterval = setInterval(() => {
      if (timeRemaining.value > 0) {
        timeRemaining.value--;
      } else {
        // Auto-submit when time runs out
        stopTimer();
        submitTest();
      }
    }, 1000);
  };

  /**
   * Stop the test timer
   */
  const stopTimer = () => {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  };

  /**
   * Check if a question has been answered
   */
  const isQuestionAnswered = (questionId: string): boolean => {
    if (!currentTest.value) return false;
    return currentTest.value.answers.some((a) => a.questionId === questionId);
  };

  /**
   * Get answer for a specific question
   */
  const getAnswerForQuestion = (questionId: string): any => {
    if (!currentTest.value) return null;
    const answer = currentTest.value.answers.find(
      (a) => a.questionId === questionId
    );
    return answer?.answer || null;
  };

  /**
   * Clear current test state
   */
  const clearCurrentTest = () => {
    stopTimer();
    currentTest.value = null;
    currentQuestionIndex.value = 0;
    timeRemaining.value = 0;
  };

  /**
   * Clear error state
   */
  const clearError = () => {
    error.value = null;
  };

  return {
    // State
    tests,
    currentTest,
    currentQuestionIndex,
    timeRemaining,
    loading,
    error,
    submitting,
    // Getters
    currentQuestion,
    totalQuestions,
    answeredQuestions,
    isLastQuestion,
    isFirstQuestion,
    progress,
    formattedTimeRemaining,
    // Actions
    fetchAvailableTests,
    fetchCompletedTests,
    startTest,
    getTest,
    submitAnswer,
    submitTest,
    getTestResults,
    nextQuestion,
    previousQuestion,
    goToQuestion,
    startTimer,
    stopTimer,
    isQuestionAnswered,
    getAnswerForQuestion,
    clearCurrentTest,
    clearError,
  };
});
