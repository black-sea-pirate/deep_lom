// User types
export interface User {
  id: string;
  email: string;
  role: "teacher" | "student";
  firstName: string;
  lastName: string;
  createdAt: Date;
  isVerified?: boolean;
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
  timerMode: "total" | "per_question"; // 'total' uses totalTime, 'per_question' uses timePerQuestion
  totalTime: number; // minutes (used when timerMode='total')
  timePerQuestion: number; // seconds (used when timerMode='per_question')
  questionTypes: QuestionTypeConfig[];
  maxStudents: number;
  numVariants?: number; // Number of unique test variants (1-30)
  testLanguage?: string; // Language for generated questions (en, ru, ua, pl)
}

export interface QuestionTypeConfig {
  type: QuestionType;
  count: number;
  timePerQuestion: number; // seconds per question for this type (used when timerMode='per_question')
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
export interface QuestionTypeTime {
  type: QuestionType;
  timePerQuestion: number; // seconds
}

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
  // Timer settings from project
  timerMode?: "total" | "per_question"; // 'total' or 'per_question'
  totalTime?: number; // minutes (used when timerMode='total')
  timePerQuestion?: number; // seconds (legacy default)
  questionTypeTimes?: QuestionTypeTime[]; // time per question for each type
}

export interface Answer {
  questionId: string;
  answer: any;
  isCorrect?: boolean;
  score?: number;
  feedback?: string;
  gradedBy?: "ai" | "system" | "teacher" | "pending_manual_review";
  gradingStatus?: "pending" | "in_progress" | "completed" | "failed";
  aiGrading?: AIGradingDetails;
}

// AI Grading types
export interface AIGradingCriterion {
  name: string;
  score: number; // 1-5
  feedback: string;
}

export interface AIGradingDetails {
  criteria: AIGradingCriterion[];
  keyStrengths: string[];
  areasForImprovement: string[];
  detectedKeywords: string[];
  percentage: number;
}

// Test Results (extended for results view)
export interface TestResultQuestion {
  id: string;
  type: QuestionType;
  text: string;
  points: number;
  options?: string[];
  pairs?: MatchingPair[];
  correctAnswer?: number | boolean | number[];
  studentAnswer: any;
  isCorrect: boolean;
  score: number;
  feedback?: string;
  gradedBy?: string;
  gradingStatus?: string;
  aiGrading?: AIGradingDetails;
}

export interface TestResults {
  id: string;
  projectId: string;
  projectTitle: string;
  status: string;
  startedAt?: Date;
  completedAt?: Date;
  score: number;
  maxScore: number;
  passed: boolean;
  aiGradingPending: boolean;
  questions: TestResultQuestion[];
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
