import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { Project } from "@/types";
import {
  projectService,
  type CreateProjectRequest,
  type UpdateProjectRequest,
} from "@/services";

export const useProjectStore = defineStore("project", () => {
  const projects = ref<Project[]>([]);
  const currentProject = ref<Project | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const totalProjects = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(20);

  // Computed
  const hasProjects = computed(() => projects.value.length > 0);
  const totalPages = computed(() =>
    Math.ceil(totalProjects.value / pageSize.value)
  );

  /**
   * Fetch all projects for current teacher
   */
  const fetchProjects = async (params?: {
    page?: number;
    status?: string;
    search?: string;
  }) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await projectService.getProjects({
        page: params?.page || currentPage.value,
        size: pageSize.value,
        status: params?.status,
        search: params?.search,
      });

      projects.value = response.items;
      totalProjects.value = response.total;
      currentPage.value = response.page;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to fetch projects";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Fetch single project by ID
   */
  const fetchProject = async (id: string) => {
    loading.value = true;
    error.value = null;

    try {
      const project = await projectService.getProject(id);
      currentProject.value = project;

      // Update in projects list if exists
      const index = projects.value.findIndex((p) => p.id === id);
      if (index !== -1) {
        projects.value[index] = project;
      }

      return project;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to fetch project";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Create new project
   */
  const createProject = async (projectData: CreateProjectRequest) => {
    loading.value = true;
    error.value = null;

    try {
      const newProject = await projectService.createProject(projectData);
      projects.value.unshift(newProject);
      totalProjects.value++;
      return newProject;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to create project";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Update existing project
   */
  const updateProject = async (
    id: string,
    projectData: UpdateProjectRequest
  ) => {
    loading.value = true;
    error.value = null;

    try {
      const updatedProject = await projectService.updateProject(
        id,
        projectData
      );

      // Update in projects list
      const index = projects.value.findIndex((p) => p.id === id);
      if (index !== -1) {
        projects.value[index] = updatedProject;
      }

      // Update current project if it's the one being edited
      if (currentProject.value?.id === id) {
        currentProject.value = updatedProject;
      }

      return updatedProject;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to update project";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Delete project
   */
  const deleteProject = async (id: string) => {
    loading.value = true;
    error.value = null;

    try {
      await projectService.deleteProject(id);
      projects.value = projects.value.filter((p) => p.id !== id);
      totalProjects.value--;

      if (currentProject.value?.id === id) {
        currentProject.value = null;
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to delete project";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Get project by ID from local state (no API call)
   */
  const getProject = (id: string): Project | undefined => {
    return projects.value.find((p) => p.id === id);
  };

  /**
   * Trigger AI test generation for project
   */
  const generateTests = async (projectId: string) => {
    loading.value = true;
    error.value = null;

    try {
      const result = await projectService.generateTests(projectId);

      // Poll for generation status
      let attempts = 0;
      const maxAttempts = 60; // 5 minutes max (5s interval)

      const pollStatus = async (): Promise<void> => {
        if (attempts >= maxAttempts) {
          throw new Error("Test generation timed out");
        }

        const status = await projectService.getGenerationStatus(
          projectId,
          result.jobId
        );

        if (status.status === "completed") {
          // Refresh project to get updated questions
          await fetchProject(projectId);
          return;
        } else if (status.status === "failed") {
          throw new Error(status.message || "Test generation failed");
        }

        // Wait and poll again
        attempts++;
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return pollStatus();
      };

      await pollStatus();
    } catch (err: any) {
      error.value =
        err.response?.data?.detail || err.message || "Failed to generate tests";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Activate project (make it available for students)
   */
  const activateProject = async (id: string) => {
    loading.value = true;
    error.value = null;

    try {
      const updatedProject = await projectService.activateProject(id);

      const index = projects.value.findIndex((p) => p.id === id);
      if (index !== -1) {
        projects.value[index] = updatedProject;
      }

      if (currentProject.value?.id === id) {
        currentProject.value = updatedProject;
      }

      return updatedProject;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to activate project";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Complete project
   */
  const completeProject = async (id: string) => {
    loading.value = true;
    error.value = null;

    try {
      const updatedProject = await projectService.completeProject(id);

      const index = projects.value.findIndex((p) => p.id === id);
      if (index !== -1) {
        projects.value[index] = updatedProject;
      }

      if (currentProject.value?.id === id) {
        currentProject.value = updatedProject;
      }

      return updatedProject;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to complete project";
      throw err;
    } finally {
      loading.value = false;
    }
  };

  /**
   * Get project statistics
   */
  const getProjectStatistics = async (id: string) => {
    try {
      return await projectService.getProjectStatistics(id);
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to get statistics";
      throw err;
    }
  };

  /**
   * Clear error state
   */
  const clearError = () => {
    error.value = null;
  };

  /**
   * Set current project
   */
  const setCurrentProject = (project: Project | null) => {
    currentProject.value = project;
  };

  return {
    // State
    projects,
    currentProject,
    loading,
    error,
    totalProjects,
    currentPage,
    pageSize,
    // Getters
    hasProjects,
    totalPages,
    // Actions
    fetchProjects,
    fetchProject,
    createProject,
    updateProject,
    deleteProject,
    getProject,
    generateTests,
    activateProject,
    completeProject,
    getProjectStatistics,
    clearError,
    setCurrentProject,
  };
});
