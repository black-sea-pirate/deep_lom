/**
 * Project Service
 *
 * Handles all project-related API calls:
 * - CRUD operations for projects
 * - Project settings management
 * - Test generation triggers
 */

import api, { type PaginatedResponse } from "./api";
import type { Project, ProjectSettings } from "@/types";

export interface ProjectStudent {
  email: string;
  firstName?: string | null;
  lastName?: string | null;
  confirmationStatus?:
    | "pending"
    | "confirmed"
    | "rejected"
    | "contact_requested"
    | "unlinked";
  participantId?: string | null;
}

/**
 * Create project request payload
 */
export interface CreateProjectRequest {
  title: string;
  description: string;
  groupName: string;
  settings: ProjectSettings;
}

/**
 * Update project request payload
 */
export interface UpdateProjectRequest {
  title?: string;
  description?: string;
  groupName?: string;
  settings?: Partial<ProjectSettings>;
  status?: "draft" | "ready" | "active" | "completed";
  startTime?: string; // ISO date string
  endTime?: string; // ISO date string
}

/**
 * Project list query parameters
 */
export interface ProjectListParams {
  page?: number;
  size?: number;
  status?: string;
  search?: string;
}

/**
 * Project Service
 */
export const projectService = {
  /**
   * Get all projects for current teacher
   * @param params - Query parameters for filtering/pagination
   * @returns Paginated list of projects
   */
  async getProjects(
    params?: ProjectListParams
  ): Promise<PaginatedResponse<Project>> {
    const response = await api.get<PaginatedResponse<Project>>("/projects", {
      params,
    });
    return response.data;
  },

  /**
   * Get single project by ID
   * @param id - Project ID
   * @returns Project details
   */
  async getProject(id: string): Promise<Project> {
    const response = await api.get<Project>(`/projects/${id}`);
    return response.data;
  },

  /**
   * Create new project
   * @param data - Project creation data
   * @returns Created project
   */
  async createProject(data: CreateProjectRequest): Promise<Project> {
    const response = await api.post<Project>("/projects", data);
    return response.data;
  },

  /**
   * Update existing project
   * @param id - Project ID
   * @param data - Updated project data
   * @returns Updated project
   */
  async updateProject(
    id: string,
    data: UpdateProjectRequest
  ): Promise<Project> {
    const response = await api.put<Project>(`/projects/${id}`, data);
    return response.data;
  },

  /**
   * Delete project
   * @param id - Project ID
   */
  async deleteProject(id: string): Promise<void> {
    await api.delete(`/projects/${id}`);
  },

  /**
   * Duplicate existing project
   * @param id - Project ID to duplicate
   * @returns New duplicated project
   */
  async duplicateProject(id: string): Promise<Project> {
    const response = await api.post<Project>(`/projects/${id}/duplicate`);
    return response.data;
  },

  /**
   * Add materials to project
   * @param id - Project ID
   * @param materialIds - Array of material IDs to add
   * @returns Updated project
   */
  async addMaterials(id: string, materialIds: string[]): Promise<Project> {
    const response = await api.post<Project>(`/projects/${id}/materials`, {
      material_ids: materialIds,
    });
    return response.data;
  },

  /**
   * Configure project settings
   * @param id - Project ID
   * @param settings - Project settings
   * @returns Updated project
   */
  async configureSettings(
    id: string,
    settings: {
      timerMode?: "total" | "per_question";
      totalTime?: number;
      timePerQuestion?: number;
      maxStudents?: number;
      numVariants?: number;
      testLanguage?: string;
      questionTypes: Array<{ type: string; count: number }>;
    },
    startTime?: Date,
    endTime?: Date
  ): Promise<Project> {
    const response = await api.put<Project>(`/projects/${id}/settings`, {
      settings: {
        timer_mode: settings.timerMode,
        total_time: settings.totalTime,
        time_per_question: settings.timePerQuestion,
        max_students: settings.maxStudents,
        num_variants: settings.numVariants,
        test_language: settings.testLanguage,
        question_types: settings.questionTypes,
      },
      start_time: startTime?.toISOString(),
      end_time: endTime?.toISOString(),
    });
    return response.data;
  },

  /**
   * Start vectorization of project materials
   * @param id - Project ID
   * @returns Vectorization status
   */
  async startVectorization(id: string): Promise<{
    status: string;
    progress: number;
    materialsTotal: number;
    materialsProcessed: number;
  }> {
    const response = await api.post(`/projects/${id}/vectorize`);
    return response.data;
  },

  /**
   * Get vectorization status
   * @param id - Project ID
   * @returns Current vectorization status
   */
  async getVectorizationStatus(id: string): Promise<{
    status: string;
    progress: number;
    error?: string;
    materialsTotal: number;
    materialsProcessed: number;
  }> {
    const response = await api.get(`/projects/${id}/vectorization-status`);
    return response.data;
  },

  /**
   * Trigger AI test generation for project
   * @param id - Project ID
   * @returns Generation job status
   */
  async generateTests(id: string): Promise<{ jobId: string; status: string }> {
    const response = await api.post<{ jobId: string; status: string }>(
      `/projects/${id}/generate-tests`
    );
    return response.data;
  },

  /**
   * Check test generation status
   * @param id - Project ID
   * @param jobId - Generation job ID
   * @returns Current generation status
   */
  async getGenerationStatus(
    id: string,
    jobId: string
  ): Promise<{
    status: "pending" | "processing" | "completed" | "failed";
    progress?: number;
    message?: string;
  }> {
    const response = await api.get(`/projects/${id}/generate-tests/${jobId}`);
    return response.data;
  },

  /**
   * Update project schedule (start/end times)
   * @param id - Project ID
   * @param startTime - Test availability start time
   * @param endTime - Test availability end time
   */
  async updateSchedule(
    id: string,
    startTime: Date,
    endTime: Date
  ): Promise<Project> {
    const response = await api.patch<Project>(`/projects/${id}/schedule`, {
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
    });
    return response.data;
  },

  /**
   * Activate project for students
   * @param id - Project ID
   * @returns Updated project with active status
   */
  async activateProject(id: string): Promise<Project> {
    const response = await api.post<Project>(`/projects/${id}/activate`);
    return response.data;
  },

  /**
   * Complete/close project
   * @param id - Project ID
   * @returns Updated project with completed status
   */
  async completeProject(id: string): Promise<Project> {
    const response = await api.post<Project>(`/projects/${id}/complete`);
    return response.data;
  },

  /**
   * Get project statistics
   * @param id - Project ID
   * @returns Project statistics and analytics
   */
  async getProjectStatistics(id: string): Promise<{
    totalStudents: number;
    completedTests: number;
    averageScore: number;
    passRate: number;
    scoreDistribution: Record<string, number>;
  }> {
    const response = await api.get(`/projects/${id}/statistics`);
    return response.data;
  },

  // ==================== Project Students Management ====================

  /**
   * Get list of allowed students for a project
   * @param id - Project ID
   * @returns Array of student emails
   */
  async getProjectStudents(id: string): Promise<ProjectStudent[]> {
    const response = await api.get<ProjectStudent[]>(
      `/projects/${id}/students`
    );
    return response.data;
  },

  /**
   * Add a student to project by email
   * @param id - Project ID
   * @param email - Student email
   * @returns Updated students list
   */
  async addStudentToProject(
    id: string,
    email: string
  ): Promise<{ message: string; students: ProjectStudent[] }> {
    const response = await api.post<{
      message: string;
      students: ProjectStudent[];
    }>(`/projects/${id}/students`, { email });
    return response.data;
  },

  /**
   * Remove a student from project
   * @param id - Project ID
   * @param email - Student email to remove
   * @returns Updated students list
   */
  async removeStudentFromProject(
    id: string,
    email: string
  ): Promise<{ message: string; students: ProjectStudent[] }> {
    const response = await api.delete<{
      message: string;
      students: ProjectStudent[];
    }>(`/projects/${id}/students/${encodeURIComponent(email)}`);
    return response.data;
  },

  /**
   * Get test results for all students in a project
   * @param id - Project ID
   * @returns Test results for each student
   */
  async getTestResults(id: string): Promise<TestResultsResponse> {
    const response = await api.get<TestResultsResponse>(
      `/projects/${id}/test-results`
    );
    return response.data;
  },

  /**
   * Delete test results for a specific student
   * @param projectId - Project ID
   * @param studentEmail - Student email
   * @returns Deletion confirmation
   */
  async deleteStudentTestResults(
    projectId: string,
    studentEmail: string
  ): Promise<{ message: string; deletedCount: number }> {
    const response = await api.delete<{
      message: string;
      deletedCount: number;
    }>(
      `/projects/${projectId}/test-results/${encodeURIComponent(studentEmail)}`
    );
    return response.data;
  },

  /**
   * Reset student test access (for technical issues)
   * @param projectId - Project ID
   * @param studentEmail - Student email
   * @returns Reset confirmation
   */
  async resetStudentTestAccess(
    projectId: string,
    studentEmail: string
  ): Promise<{ message: string; resetCount: number; studentEmail: string }> {
    const response = await api.post<{
      message: string;
      resetCount: number;
      studentEmail: string;
    }>(
      `/projects/${projectId}/reset-student/${encodeURIComponent(studentEmail)}`
    );
    return response.data;
  },
};

/**
 * Test result for a student
 */
export interface StudentTestResult {
  testId: string | null;
  studentId: string | null;
  email: string;
  firstName: string | null;
  lastName: string | null;
  status: "not_started" | "pending" | "in-progress" | "completed" | "graded";
  score: number | null;
  maxScore: number | null;
  timeTaken: number | null; // seconds
  startedAt: string | null;
  completedAt: string | null;
  variantNumber: number | null;
  totalQuestions: number;
  gradedQuestions: number;
  pendingAiGrading: number;
}

export interface TestResultsResponse {
  results: StudentTestResult[];
}

export default projectService;
