/**
 * Test Service
 *
 * Handles all test-related API calls:
 * - Test CRUD operations
 * - Question management
 * - Student test attempts
 * - Grading and results
 */

import api, { type PaginatedResponse } from "./api";
import type { Test, Question, Answer } from "@/types";

/**
 * Submit answer request
 */
export interface SubmitAnswerRequest {
  questionId: string;
  answer: any; // Type varies by question type
}

/**
 * Test submission response
 */
export interface TestSubmissionResponse {
  testId: string;
  score: number;
  maxScore: number;
  correctAnswers: number;
  totalQuestions: number;
  passed: boolean;
  feedback?: string;
}

/**
 * Test list query parameters
 */
export interface TestListParams {
  page?: number;
  size?: number;
  projectId?: string;
  status?: string;
  studentId?: string;
}

/**
 * Test Service
 */
export const testService = {
  // ========================
  // Teacher-side operations
  // ========================

  /**
   * Get all tests for a project (teacher view)
   * @param projectId - Project ID
   * @param params - Query parameters
   * @returns Paginated list of tests
   */
  async getProjectTests(
    projectId: string,
    params?: TestListParams
  ): Promise<PaginatedResponse<Test>> {
    const response = await api.get<PaginatedResponse<Test>>(
      `/projects/${projectId}/tests`,
      { params }
    );
    return response.data;
  },

  /**
   * Get test details with questions (teacher view)
   * @param testId - Test ID
   * @returns Test with all questions and answers
   */
  async getTest(testId: string): Promise<Test> {
    const response = await api.get<Test>(`/tests/${testId}`);
    return response.data;
  },

  /**
   * Update test questions
   * @param testId - Test ID
   * @param questions - Updated questions array
   * @returns Updated test
   */
  async updateQuestions(testId: string, questions: Question[]): Promise<Test> {
    const response = await api.put<Test>(`/tests/${testId}/questions`, {
      questions,
    });
    return response.data;
  },

  /**
   * Add single question to test
   * @param testId - Test ID
   * @param question - New question
   * @returns Updated test
   */
  async addQuestion(
    testId: string,
    question: Omit<Question, "id">
  ): Promise<Test> {
    const response = await api.post<Test>(
      `/tests/${testId}/questions`,
      question
    );
    return response.data;
  },

  /**
   * Update single question
   * @param testId - Test ID
   * @param questionId - Question ID
   * @param question - Updated question data
   * @returns Updated test
   */
  async updateQuestion(
    testId: string,
    questionId: string,
    question: Partial<Question>
  ): Promise<Test> {
    const response = await api.patch<Test>(
      `/tests/${testId}/questions/${questionId}`,
      question
    );
    return response.data;
  },

  /**
   * Delete question from test
   * @param testId - Test ID
   * @param questionId - Question ID
   */
  async deleteQuestion(testId: string, questionId: string): Promise<void> {
    await api.delete(`/tests/${testId}/questions/${questionId}`);
  },

  /**
   * Grade student's test manually
   * @param testId - Test ID
   * @param grades - Array of question grades
   * @returns Updated test with grades
   */
  async gradeTest(
    testId: string,
    grades: { questionId: string; score: number; feedback?: string }[]
  ): Promise<Test> {
    const response = await api.post<Test>(`/tests/${testId}/grade`, { grades });
    return response.data;
  },

  // ========================
  // Student-side operations
  // ========================

  /**
   * Get available tests for student
   * @returns List of available tests
   */
  async getAvailableTests(): Promise<Test[]> {
    const response = await api.get<Test[]>("/student/tests/available");
    return response.data;
  },

  /**
   * Get student's completed tests
   * @returns List of completed tests
   */
  async getCompletedTests(): Promise<Test[]> {
    const response = await api.get<Test[]>("/student/tests/completed");
    return response.data;
  },

  /**
   * Start taking a test (creates test attempt)
   * @param projectId - Project ID
   * @returns Test instance for student
   */
  async startTest(projectId: string): Promise<Test> {
    const response = await api.post<Test>(`/student/tests/${projectId}/start`);
    return response.data;
  },

  /**
   * Get current test attempt
   * @param testId - Test ID
   * @returns Current test with questions (without correct answers)
   */
  async getCurrentTest(testId: string): Promise<Test> {
    const response = await api.get<Test>(`/student/tests/${testId}`);
    return response.data;
  },

  /**
   * Submit answer for a question
   * @param testId - Test ID
   * @param answer - Answer data
   * @returns Updated answer with validation (if applicable)
   */
  async submitAnswer(
    testId: string,
    answer: SubmitAnswerRequest
  ): Promise<Answer> {
    const response = await api.post<Answer>(
      `/student/tests/${testId}/answers`,
      answer
    );
    return response.data;
  },

  /**
   * Submit entire test
   * @param testId - Test ID
   * @returns Test submission results
   */
  async submitTest(testId: string): Promise<TestSubmissionResponse> {
    const response = await api.post<TestSubmissionResponse>(
      `/student/tests/${testId}/submit`
    );
    return response.data;
  },

  /**
   * Get test results (after completion)
   * @param testId - Test ID
   * @returns Full test results with feedback
   */
  async getTestResults(testId: string): Promise<Test> {
    const response = await api.get<Test>(`/student/tests/${testId}/results`);
    return response.data;
  },

  // ========================
  // Lobby operations
  // ========================

  /**
   * Get lobby status for a project
   * @param projectId - Project ID
   * @returns Lobby status with connected students
   */
  async getLobbyStatus(projectId: string): Promise<{
    projectId: string;
    status: "waiting" | "active" | "completed";
    connectedStudents: {
      id: string;
      name: string;
      email: string;
      joinedAt: Date;
    }[];
    maxStudents: number;
  }> {
    const response = await api.get(`/projects/${projectId}/lobby`);
    return response.data;
  },

  /**
   * Join test lobby as student
   * @param projectId - Project ID
   * @returns Lobby join confirmation
   */
  async joinLobby(
    projectId: string
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/student/lobby/${projectId}/join`);
    return response.data;
  },

  /**
   * Leave test lobby
   * @param projectId - Project ID
   */
  async leaveLobby(projectId: string): Promise<void> {
    await api.post(`/student/lobby/${projectId}/leave`);
  },
};

export default testService;
