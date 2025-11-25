/**
 * Participant Service
 *
 * Handles participant (students/groups) management:
 * - Group CRUD operations
 * - Student management within groups
 * - Project participant associations
 */

import api, { type PaginatedResponse } from "./api";

/**
 * Student/Participant type
 */
export interface Participant {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  groupId?: string;
  groupName?: string;
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
  studentsCount: number;
  createdAt: Date;
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
  // Group operations
  // ========================

  /**
   * Get all groups for current teacher
   * @returns List of groups
   */
  async getGroups(): Promise<Group[]> {
    const response = await api.get<Group[]>("/groups");
    return response.data;
  },

  /**
   * Get single group by ID
   * @param id - Group ID
   * @returns Group details
   */
  async getGroup(id: string): Promise<Group> {
    const response = await api.get<Group>(`/groups/${id}`);
    return response.data;
  },

  /**
   * Create new group
   * @param data - Group creation data
   * @returns Created group
   */
  async createGroup(data: CreateGroupRequest): Promise<Group> {
    const response = await api.post<Group>("/groups", data);
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
    const response = await api.patch<Group>(`/groups/${id}`, data);
    return response.data;
  },

  /**
   * Delete group
   * @param id - Group ID
   */
  async deleteGroup(id: string): Promise<void> {
    await api.delete(`/groups/${id}`);
  },

  // ========================
  // Student operations
  // ========================

  /**
   * Get students in a group
   * @param groupId - Group ID
   * @returns List of students
   */
  async getGroupStudents(groupId: string): Promise<Participant[]> {
    const response = await api.get<Participant[]>(
      `/groups/${groupId}/students`
    );
    return response.data;
  },

  /**
   * Get all students (all groups)
   * @param params - Query parameters
   * @returns Paginated list of students
   */
  async getAllStudents(params?: {
    page?: number;
    size?: number;
    search?: string;
  }): Promise<PaginatedResponse<Participant>> {
    const response = await api.get<PaginatedResponse<Participant>>(
      "/students",
      { params }
    );
    return response.data;
  },

  /**
   * Add student to group
   * @param groupId - Group ID
   * @param data - Student data
   * @returns Added student
   */
  async addStudent(
    groupId: string,
    data: AddStudentRequest
  ): Promise<Participant> {
    const response = await api.post<Participant>(
      `/groups/${groupId}/students`,
      data
    );
    return response.data;
  },

  /**
   * Remove student from group
   * @param groupId - Group ID
   * @param studentId - Student ID
   */
  async removeStudent(groupId: string, studentId: string): Promise<void> {
    await api.delete(`/groups/${groupId}/students/${studentId}`);
  },

  /**
   * Move student to different group
   * @param studentId - Student ID
   * @param newGroupId - New group ID
   * @returns Updated student
   */
  async moveStudent(
    studentId: string,
    newGroupId: string
  ): Promise<Participant> {
    const response = await api.patch<Participant>(
      `/students/${studentId}/group`,
      {
        group_id: newGroupId,
      }
    );
    return response.data;
  },

  /**
   * Bulk import students from CSV
   * @param groupId - Target group ID
   * @param file - CSV file
   * @returns Import result
   */
  async importStudentsFromCsv(
    groupId: string,
    file: File
  ): Promise<{
    imported: number;
    failed: number;
    errors: string[];
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await api.post(`/groups/${groupId}/import`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  /**
   * Bulk add students to group
   * @param data - Bulk import data
   * @returns Import result
   */
  async bulkAddStudents(data: BulkImportRequest): Promise<{
    imported: number;
    failed: number;
    errors: string[];
  }> {
    const response = await api.post(`/groups/${data.groupId}/students/bulk`, {
      students: data.students,
    });
    return response.data;
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
