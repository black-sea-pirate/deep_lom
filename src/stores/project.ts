import { defineStore } from "pinia";
import { ref } from "vue";
import type { Project, QuestionType } from "@/types";

export const useProjectStore = defineStore("project", () => {
  const projects = ref<Project[]>([
    {
      id: "1",
      teacherId: "1",
      title: "Linear Equations",
      description: "Advanced mathematics course for engineering students",
      groupName: "KN420-Б",
      settings: {
        totalTime: 60,
        timePerQuestion: 120,
        questionTypes: [
          { type: "single-choice" as QuestionType, count: 10 },
          { type: "multiple-choice" as QuestionType, count: 5 },
          { type: "short-answer" as QuestionType, count: 3 },
        ],
        maxStudents: 30,
      },
      status: "ready",
      createdAt: new Date("2025-10-20"),
      materials: [
        {
          id: "m1",
          projectId: "1",
          fileName: "linear_equations_theory.pdf",
          fileType: "pdf",
          filePath: "/uploads/linear_equations_theory.pdf",
          uploadedAt: new Date("2025-10-20"),
        },
      ],
      tests: [],
    },
    {
      id: "2",
      teacherId: "1",
      title: "Quantum Physics Introduction",
      description: "Introduction to quantum mechanics",
      groupName: "PH301-A",
      settings: {
        totalTime: 90,
        timePerQuestion: 180,
        questionTypes: [
          { type: "single-choice" as QuestionType, count: 8 },
          { type: "essay" as QuestionType, count: 2 },
        ],
        maxStudents: 25,
      },
      status: "draft",
      createdAt: new Date("2025-10-25"),
      materials: [],
      tests: [],
    },
  ]);

  const currentProject = ref<Project | null>(null);
  const loading = ref(false);

  const createProject = async (projectData: Partial<Project>) => {
    loading.value = true;
    await new Promise((resolve) => setTimeout(resolve, 1000));

    const newProject: Project = {
      id: Date.now().toString(),
      teacherId: "1",
      title: projectData.title || "",
      description: projectData.description || "",
      groupName: projectData.groupName || "",
      settings: projectData.settings || {
        totalTime: 60,
        timePerQuestion: 120,
        questionTypes: [],
        maxStudents: 30,
      },
      status: "draft",
      createdAt: new Date(),
      materials: [],
      tests: [],
    };

    projects.value.push(newProject);
    loading.value = false;
    return newProject;
  };

  const updateProject = async (id: string, projectData: Partial<Project>) => {
    loading.value = true;
    await new Promise((resolve) => setTimeout(resolve, 500));

    const index = projects.value.findIndex((p) => p.id === id);
    if (index !== -1) {
      projects.value[index] = { ...projects.value[index], ...projectData };
    }

    loading.value = false;
  };

  const deleteProject = async (id: string) => {
    loading.value = true;
    await new Promise((resolve) => setTimeout(resolve, 500));

    projects.value = projects.value.filter((p) => p.id !== id);
    loading.value = false;
  };

  const getProject = (id: string) => {
    return projects.value.find((p) => p.id === id);
  };

  const generateTests = async (projectId: string) => {
    loading.value = true;
    // Simulate GPT test generation
    await new Promise((resolve) => setTimeout(resolve, 3000));

    const project = getProject(projectId);
    if (project) {
      project.status = "ready";
    }

    loading.value = false;
  };

  return {
    projects,
    currentProject,
    loading,
    createProject,
    updateProject,
    deleteProject,
    getProject,
    generateTests,
  };
});
