/**
 * Services Index
 *
 * Central export point for all API services.
 * Import services from here for cleaner imports throughout the app.
 */

export { default as api } from "./api";
export type { ApiResponse, PaginatedResponse } from "./api";

export { default as authService } from "./auth.service";
export type {
  LoginRequest,
  RegisterRequest,
  AuthResponse,
} from "./auth.service";

export { default as projectService } from "./project.service";
export type {
  CreateProjectRequest,
  UpdateProjectRequest,
  ProjectListParams,
} from "./project.service";

export { default as testService } from "./test.service";
export type {
  SubmitAnswerRequest,
  TestSubmissionResponse,
  TestListParams,
} from "./test.service";

export { default as materialService } from "./material.service";
export type {
  MaterialListParams,
  UploadProgressCallback,
} from "./material.service";

export { default as participantService } from "./participant.service";
export type {
  Participant,
  Group,
  CreateGroupRequest,
  AddStudentRequest,
  BulkImportRequest,
} from "./participant.service";
