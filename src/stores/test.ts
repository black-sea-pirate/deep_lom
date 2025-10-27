import { defineStore } from "pinia";
import { ref } from "vue";
import type { Test, Question, Answer } from "@/types";

export const useTestStore = defineStore("test", () => {
  const tests = ref<Test[]>([]);
  const currentTest = ref<Test | null>(null);
  const currentQuestionIndex = ref(0);
  const timeRemaining = ref(0);
  const loading = ref(false);

  // Mock questions for demo
  const mockQuestions: Question[] = [
    {
      id: "q1",
      type: "single-choice",
      text: "What is the solution to the equation 2x + 5 = 15?",
      points: 10,
      options: ["x = 5", "x = 10", "x = 7.5", "x = 2.5"],
      correctAnswer: 0,
    },
    {
      id: "q2",
      type: "multiple-choice",
      text: "Which of the following are properties of linear equations?",
      points: 15,
      options: [
        "Has degree 1",
        "Forms a straight line",
        "Has at most one solution",
        "Can have multiple solutions",
      ],
      correctAnswers: [0, 1],
    },
    {
      id: "q3",
      type: "true-false",
      text: "Every linear equation has exactly one solution.",
      points: 5,
      correctAnswer: false,
    },
    {
      id: "q4",
      type: "short-answer",
      text: "Explain the slope-intercept form of a linear equation.",
      points: 20,
      expectedKeywords: ["y = mx + b", "slope", "intercept", "coefficient"],
    },
  ];

  const startTest = async (projectId: string) => {
    loading.value = true;
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const newTest: Test = {
      id: Date.now().toString(),
      projectId,
      questions: mockQuestions,
      answers: [],
      maxScore: mockQuestions.reduce((sum, q) => sum + q.points, 0),
      status: "in-progress",
      startedAt: new Date(),
    };

    currentTest.value = newTest;
    tests.value.push(newTest);
    currentQuestionIndex.value = 0;
    timeRemaining.value = 60 * 60; // 60 minutes in seconds

    loading.value = false;
    return newTest;
  };

  const submitAnswer = async (questionId: string, answer: any) => {
    if (!currentTest.value) return;

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
  };

  const submitTest = async () => {
    if (!currentTest.value) return;

    loading.value = true;
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Mock grading
    currentTest.value.status = "graded";
    currentTest.value.completedAt = new Date();
    currentTest.value.score = Math.floor(Math.random() * 40) + 60; // Random score 60-100

    loading.value = false;
    return currentTest.value;
  };

  const nextQuestion = () => {
    if (
      currentTest.value &&
      currentQuestionIndex.value < currentTest.value.questions.length - 1
    ) {
      currentQuestionIndex.value++;
    }
  };

  const previousQuestion = () => {
    if (currentQuestionIndex.value > 0) {
      currentQuestionIndex.value--;
    }
  };

  const goToQuestion = (index: number) => {
    if (
      currentTest.value &&
      index >= 0 &&
      index < currentTest.value.questions.length
    ) {
      currentQuestionIndex.value = index;
    }
  };

  return {
    tests,
    currentTest,
    currentQuestionIndex,
    timeRemaining,
    loading,
    startTest,
    submitAnswer,
    submitTest,
    nextQuestion,
    previousQuestion,
    goToQuestion,
  };
});
