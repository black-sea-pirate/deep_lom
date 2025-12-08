/**
 * Analytics Service
 *
 * Handles teacher analytics and reporting:
 * - Overview statistics
 * - Score distribution
 * - Recent test results
 * - Top performing students
 * - Project performance
 */

import api from "./api";

/**
 * Overview statistics type
 */
export interface OverviewStats {
  totalTests: number;
  totalStudents: number;
  avgScore: number;
  completionRate: number;
  avgTimeMinutes: number;
  testsThisMonth: number;
  scoreChange: number;
  studentsChange: number;
}

/**
 * Score distribution bucket
 */
export interface ScoreDistributionItem {
  range: string;
  count: number;
  percentage: number;
}

/**
 * Recent test info
 */
export interface RecentTest {
  id: string;
  projectName: string;
  date: Date;
  participants: number;
  avgScore: number;
  passRate: number;
}

/**
 * Top student info
 */
export interface TopStudent {
  id: string;
  name: string;
  avgScore: number;
  testsCompleted: number;
}

/**
 * Project performance info
 */
export interface ProjectPerformance {
  name: string;
  avgScore: number;
  tests: number;
  students: number;
  trend: "up" | "down" | "stable";
}

/**
 * Full analytics response
 */
export interface AnalyticsResponse {
  overview: OverviewStats;
  scoreDistribution: ScoreDistributionItem[];
  recentTests: RecentTest[];
  topStudents: TopStudent[];
  projectPerformance: ProjectPerformance[];
}

/**
 * Analytics Service
 */
export const analyticsService = {
  /**
   * Get teacher analytics overview
   * @param period - Time period filter
   * @returns Analytics data
   */
  async getAnalytics(period: string = "month"): Promise<AnalyticsResponse> {
    const response = await api.get<AnalyticsResponse>("/analytics", {
      params: { period },
    });
    return response.data;
  },

  /**
   * Get overview statistics
   * @param period - Time period filter
   * @returns Overview stats
   */
  async getOverviewStats(period: string = "month"): Promise<OverviewStats> {
    const response = await api.get<OverviewStats>("/analytics/overview", {
      params: { period },
    });
    return response.data;
  },

  /**
   * Get score distribution
   * @param period - Time period filter
   * @returns Score distribution buckets
   */
  async getScoreDistribution(
    period: string = "month"
  ): Promise<ScoreDistributionItem[]> {
    const response = await api.get<ScoreDistributionItem[]>(
      "/analytics/score-distribution",
      {
        params: { period },
      }
    );
    return response.data;
  },

  /**
   * Get recent tests
   * @param limit - Number of tests to return
   * @returns Recent tests
   */
  async getRecentTests(limit: number = 10): Promise<RecentTest[]> {
    const response = await api.get<RecentTest[]>("/analytics/recent-tests", {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Get top performing students
   * @param limit - Number of students to return
   * @returns Top students
   */
  async getTopStudents(limit: number = 10): Promise<TopStudent[]> {
    const response = await api.get<TopStudent[]>("/analytics/top-students", {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Get project performance comparison
   * @returns Project performance data
   */
  async getProjectPerformance(): Promise<ProjectPerformance[]> {
    const response = await api.get<ProjectPerformance[]>(
      "/analytics/project-performance"
    );
    return response.data;
  },

  /**
   * Export analytics report
   * @param period - Time period filter
   * @param format - Export format (pdf, csv, xlsx)
   * @returns Blob for download
   */
  async exportReport(
    period: string = "month",
    format: "pdf" | "csv" | "xlsx" = "pdf"
  ): Promise<Blob> {
    const response = await api.get(`/analytics/export`, {
      params: { period, format },
      responseType: "blob",
    });
    return response.data;
  },
};

export default analyticsService;
