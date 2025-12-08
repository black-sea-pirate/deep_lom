/**
 * Student Service
 *
 * Handles student-specific operations:
 * - Dashboard statistics
 * - Email management
 * - Test history
 * - Upcoming tests
 */

import api from "./api";

/**
 * Student email type
 */
export interface StudentEmail {
  id: string;
  email: string;
  isPrimary: boolean;
  institution?: string;
  createdAt: Date;
}

/**
 * Student statistics type
 */
export interface StudentStatistics {
  totalTests: number;
  completedTests: number;
  averageScore: number;
}

/**
 * Completed test info
 */
export interface CompletedTestInfo {
  id: string;
  title: string;
  groupName?: string;
  score: number;
  maxScore: number;
  completedAt: Date;
}

/**
 * Upcoming test info
 */
export interface UpcomingTestInfo {
  id: string;
  projectId: string;
  title: string;
  groupName?: string;
  startTime?: Date;
  endTime?: Date;
  duration: number;
  status: "scheduled" | "available" | "started";
}

/**
 * Student Service
 */
export const studentService = {
  // ========================
  // Statistics
  // ========================

  /**
   * Get student statistics
   * @returns Student statistics
   */
  async getStatistics(): Promise<StudentStatistics> {
    const response = await api.get<StudentStatistics>("/student/statistics");
    return response.data;
  },

  /**
   * Get completed tests
   * @returns List of completed tests
   */
  async getCompletedTests(): Promise<CompletedTestInfo[]> {
    const response = await api.get<CompletedTestInfo[]>(
      "/student/tests/completed"
    );
    return response.data;
  },

  /**
   * Get upcoming tests
   * @returns List of upcoming tests
   */
  async getUpcomingTests(): Promise<UpcomingTestInfo[]> {
    const response = await api.get<UpcomingTestInfo[]>(
      "/student/tests/upcoming"
    );
    return response.data;
  },

  // ========================
  // Email management
  // ========================

  /**
   * Get student emails
   * @returns List of student emails
   */
  async getEmails(): Promise<StudentEmail[]> {
    const response = await api.get<StudentEmail[]>("/student/emails");
    return response.data;
  },

  /**
   * Add new email
   * @param email - Email address
   * @param institution - Optional institution name
   * @returns Added email
   */
  async addEmail(email: string, institution?: string): Promise<StudentEmail> {
    const response = await api.post<StudentEmail>("/student/emails", {
      email,
      institution,
    });
    return response.data;
  },

  /**
   * Delete email
   * @param emailId - Email ID to delete
   */
  async deleteEmail(emailId: string): Promise<void> {
    await api.delete(`/student/emails/${emailId}`);
  },

  /**
   * Set email as primary
   * @param emailId - Email ID to set as primary
   */
  async setPrimaryEmail(emailId: string): Promise<void> {
    await api.patch(`/student/emails/${emailId}/primary`);
  },

  // ========================
  // Password
  // ========================

  /**
   * Change password
   * @param currentPassword - Current password
   * @param newPassword - New password
   */
  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    await api.post("/student/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  // ========================
  // Contact Requests
  // ========================

  /**
   * Get pending contact requests from teachers
   * @returns List of pending contact requests
   */
  async getContactRequests(): Promise<ContactRequest[]> {
    const response = await api.get<ContactRequest[]>(
      "/student/contact-requests"
    );
    return response.data;
  },

  /**
   * Get count of pending contact requests
   * @returns Number of pending requests
   */
  async getContactRequestsCount(): Promise<number> {
    const response = await api.get<{ count: number }>(
      "/student/contact-requests/count"
    );
    return response.data.count;
  },

  /**
   * Confirm a contact request
   * @param participantId - Participant ID to confirm
   */
  async confirmContactRequest(participantId: string): Promise<void> {
    await api.post(`/student/contact-requests/${participantId}/confirm`);
  },

  /**
   * Reject a contact request
   * @param participantId - Participant ID to reject
   */
  async rejectContactRequest(participantId: string): Promise<void> {
    await api.post(`/student/contact-requests/${participantId}/reject`);
  },
};

/**
 * Contact request from teacher
 */
export interface ContactRequest {
  id: string;
  teacherName: string;
  teacherEmail: string;
  studentName: string;
  studentEmail: string;
  createdAt: Date;
}

export default studentService;
