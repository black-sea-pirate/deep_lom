/**
 * Participant Service
 *
 * Handles participant (students/groups) management:
 * - Group CRUD operations
 * - Student management within groups
 * - Project participant associations
 */

import api, { type PaginatedResponse } from "./api";
import type { StudentLookup } from "@/types";

/**
 * Student/Participant type
 */
export interface Participant {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  type: "individual" | "group-member";
  groupId?: string;
  confirmationStatus: "pending" | "confirmed" | "rejected";
  studentUserId?: string;
  createdAt: Date;
}

/**
 * Group type
 */
export interface Group {
  id: string;
  name: string;
  description?: string;
  teacherId: string;
  membersCount: number;
  createdAt: Date;
}

/**
 * Create participant request (uses camelCase - Pydantic populate_by_name handles conversion)
 */
export interface CreateParticipantRequest {
  email: string;
  firstName: string;
  lastName: string;
  type?: "individual" | "group-member";
  groupId?: string;
  autoFill?: boolean; // If true, auto-fill name from database
}

/**
 * Create group request
 */
export interface CreateGroupRequest {
  name: string;
  description?: string;
}

/**
 * Add student to group request
 */
export interface AddStudentRequest {
  email: string;
  firstName?: string;
  lastName?: string;
}

/**
 * Bulk import students request
 */
export interface BulkImportRequest {
  groupId: string;
  students: AddStudentRequest[];
}

/**
 * Participant Service
 */
export const participantService = {
  // ========================
  // Participant operations
  // ========================

  /**
   * Get all participants for current teacher
   * @param params - Query parameters
   * @returns Paginated list of participants
   */
  async getParticipants(params?: {
    page?: number;
    size?: number;
    groupId?: string;
    search?: string;
  }): Promise<PaginatedResponse<Participant>> {
    const response = await api.get<PaginatedResponse<Participant>>(
      "/participants",
      { params }
    );
    return response.data;
  },

  /**
   * Lookup student by email to auto-fill name
   * @param email - Email to lookup
   * @returns Student info if found
   */
  async lookupStudent(email: string): Promise<StudentLookup> {
    const response = await api.get<StudentLookup>("/participants/lookup", {
      params: { email },
    });
    return response.data;
  },

  /**
   * Get only confirmed participants (for Lobby selection)
   * @returns List of confirmed participants
   */
  async getConfirmedParticipants(): Promise<Participant[]> {
    const response = await api.get<PaginatedResponse<Participant>>(
      "/participants",
      { params: { page: 1, size: 100 } }
    );
    return response.data.items.filter(
      (p) => p.confirmationStatus === "confirmed"
    );
  },

  /**
   * Create new participant
   * @param data - Participant creation data
   * @returns Created participant
   */
  async createParticipant(
    data: CreateParticipantRequest
  ): Promise<Participant> {
    const response = await api.post<Participant>("/participants", data);
    return response.data;
  },

  /**
   * Update participant
   * @param id - Participant ID
   * @param data - Updated participant data
   * @returns Updated participant
   */
  async updateParticipant(
    id: string,
    data: Partial<CreateParticipantRequest>
  ): Promise<Participant> {
    const response = await api.put<Participant>(`/participants/${id}`, data);
    return response.data;
  },

  /**
   * Delete participant
   * @param id - Participant ID
   */
  async deleteParticipant(id: string): Promise<void> {
    await api.delete(`/participants/${id}`);
  },

  // ========================
  // Group operations
  // ========================

  /**
   * Get all groups for current teacher
   * @returns List of groups
   */
  async getGroups(): Promise<Group[]> {
    const response = await api.get<Group[]>("/participants/groups");
    return response.data;
  },

  /**
   * Get single group by ID
   * @param id - Group ID
   * @returns Group details
   */
  async getGroup(id: string): Promise<Group> {
    const response = await api.get<Group>(`/participants/groups/${id}`);
    return response.data;
  },

  /**
   * Create new group
   * @param data - Group creation data
   * @returns Created group
   */
  async createGroup(data: CreateGroupRequest): Promise<Group> {
    const response = await api.post<Group>("/participants/groups", data);
    return response.data;
  },

  /**
   * Update group
   * @param id - Group ID
   * @param data - Updated group data
   * @returns Updated group
   */
  async updateGroup(
    id: string,
    data: Partial<CreateGroupRequest>
  ): Promise<Group> {
    const response = await api.put<Group>(`/participants/groups/${id}`, data);
    return response.data;
  },

  /**
   * Delete group
   * @param id - Group ID
   */
  async deleteGroup(id: string): Promise<void> {
    await api.delete(`/participants/groups/${id}`);
  },

  // ========================
  // Project participant operations
  // ========================

  /**
   * Get allowed participants for a project
   * @param projectId - Project ID
   * @returns List of allowed participants
   */
  async getProjectParticipants(projectId: string): Promise<Participant[]> {
    const response = await api.get<Participant[]>(
      `/projects/${projectId}/participants`
    );
    return response.data;
  },

  /**
   * Add participant to project allowed list
   * @param projectId - Project ID
   * @param email - Student email
   * @returns Updated participant list
   */
  async addProjectParticipant(
    projectId: string,
    email: string
  ): Promise<Participant> {
    const response = await api.post<Participant>(
      `/projects/${projectId}/participants`,
      { email }
    );
    return response.data;
  },

  /**
   * Remove participant from project
   * @param projectId - Project ID
   * @param studentId - Student ID
   */
  async removeProjectParticipant(
    projectId: string,
    studentId: string
  ): Promise<void> {
    await api.delete(`/projects/${projectId}/participants/${studentId}`);
  },

  /**
   * Add entire group to project
   * @param projectId - Project ID
   * @param groupId - Group ID
   * @returns Number of added participants
   */
  async addGroupToProject(
    projectId: string,
    groupId: string
  ): Promise<{ added: number }> {
    const response = await api.post(
      `/projects/${projectId}/participants/group/${groupId}`
    );
    return response.data;
  },
};

export default participantService;
