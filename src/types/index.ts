// User types
export interface User {
  id: string;
  email: string;
  role: "teacher" | "student";
  firstName: string;
  lastName: string;
  createdAt: Date;
}

// Project types
export interface Project {
  id: string;
  teacherId: string;
  title: string;
  description: string;
  groupName: string;
  settings: ProjectSettings;
  status:
    | "draft"
    | "ready"
    | "active"
    | "completed"
    | "generating"
    | "vectorizing";
  createdAt: Date;
  materials: Material[];
  tests: Test[];
  // New fields for scheduling
  startTime?: Date;
  endTime?: Date;
  allowedStudents?: string[]; // email addresses
  // Vectorization status
  vectorizationStatus?: string;
  vectorizationProgress?: number;
}

export interface ProjectSettings {
  totalTime: number; // minutes
  timePerQuestion: number; // seconds
  questionTypes: QuestionTypeConfig[];
  maxStudents: number;
  numVariants?: number; // Number of unique test variants (1-30)
  testLanguage?: string; // Language for generated questions (en, ru, ua, pl)
}

export interface QuestionTypeConfig {
  type: QuestionType;
  count: number;
}

// Question types
export type QuestionType =
  | "single-choice"
  | "multiple-choice"
  | "true-false"
  | "short-answer"
  | "essay"
  | "matching";

export interface BaseQuestion {
  id: string;
  type: QuestionType;
  text: string;
  points: number;
}

export interface SingleChoiceQuestion extends BaseQuestion {
  type: "single-choice";
  options: string[];
  correctAnswer: number;
}

export interface MultipleChoiceQuestion extends BaseQuestion {
  type: "multiple-choice";
  options: string[];
  correctAnswers: number[];
}

export interface TrueFalseQuestion extends BaseQuestion {
  type: "true-false";
  correctAnswer: boolean;
}

export interface ShortAnswerQuestion extends BaseQuestion {
  type: "short-answer";
  expectedKeywords: string[];
}

export interface EssayQuestion extends BaseQuestion {
  type: "essay";
  rubric: string[];
}

export interface MatchingQuestion extends BaseQuestion {
  type: "matching";
  pairs: MatchingPair[];
}

export interface MatchingPair {
  left: string;
  right: string;
}

export type Question =
  | SingleChoiceQuestion
  | MultipleChoiceQuestion
  | TrueFalseQuestion
  | ShortAnswerQuestion
  | EssayQuestion
  | MatchingQuestion;

// Test types
export interface Test {
  id: string;
  projectId: string;
  studentId?: string;
  questions: Question[];
  answers: Answer[];
  score?: number;
  maxScore: number;
  status: "pending" | "in-progress" | "completed" | "graded";
  startedAt?: Date;
  completedAt?: Date;
}

export interface Answer {
  questionId: string;
  answer: any;
  isCorrect?: boolean;
  score?: number;
  feedback?: string;
}

// Material types
export interface Material {
  id: string;
  projectId?: string;
  folderId?: string; // Reference to folder
  fileName: string; // UUID-based filename for storage
  originalName: string; // Original user-friendly filename
  fileType: string;
  filePath: string;
  fileSize: number;
  uploadedAt: Date;
}

// Material Folder types
export interface MaterialFolder {
  id: string;
  name: string;
  description?: string;
  teacherId: string;
  materialsCount: number;
  createdAt: Date;
}

// Participant types
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

// Participant Group types
export interface ParticipantGroup {
  id: string;
  name: string;
  description?: string;
  teacherId: string;
  membersCount: number;
  createdAt: Date;
}

// Contact Request (for student notifications)
export interface ContactRequest {
  id: string;
  teacherId: string;
  teacherName: string;
  teacherEmail: string;
  status: "pending" | "confirmed" | "rejected";
  createdAt: Date;
}

// Student Lookup Response
export interface StudentLookup {
  found: boolean;
  email: string;
  firstName?: string;
  lastName?: string;
  userId?: string;
}

// Statistics types
export interface StudentStatistics {
  totalTests: number;
  completedTests: number;
  averageScore: number;
  testHistory: TestResult[];
}

export interface TestResult {
  testId: string;
  projectTitle: string;
  score: number;
  maxScore: number;
  completedAt: Date;
}

// Lobby types
export interface LobbyStudent {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  status: "waiting" | "ready";
  joinedAt: Date;
}
