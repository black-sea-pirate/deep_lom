/**
 * Material Service
 *
 * Handles all educational material operations:
 * - File upload/download
 * - Material management
 * - Project-material associations
 */

import api, { type PaginatedResponse } from "./api";
import type { Material } from "@/types";

/**
 * Material list query parameters
 */
export interface MaterialListParams {
  page?: number;
  size?: number;
  projectId?: string;
  fileType?: string;
  search?: string;
}

/**
 * Upload progress callback type
 */
export type UploadProgressCallback = (progress: number) => void;

/**
 * Material Service
 */
export const materialService = {
  /**
   * Get all materials for current teacher
   * @param params - Query parameters
   * @returns Paginated list of materials
   */
  async getMaterials(
    params?: MaterialListParams
  ): Promise<PaginatedResponse<Material>> {
    const response = await api.get<PaginatedResponse<Material>>("/materials", {
      params,
    });
    return response.data;
  },

  /**
   * Get materials for specific project
   * @param projectId - Project ID
   * @returns List of project materials
   */
  async getProjectMaterials(projectId: string): Promise<Material[]> {
    const response = await api.get<Material[]>(
      `/projects/${projectId}/materials`
    );
    return response.data;
  },

  /**
   * Get single material by ID
   * @param id - Material ID
   * @returns Material details
   */
  async getMaterial(id: string): Promise<Material> {
    const response = await api.get<Material>(`/materials/${id}`);
    return response.data;
  },

  /**
   * Upload new material file
   * @param file - File to upload
   * @param projectId - Optional project ID to associate with
   * @param onProgress - Optional progress callback
   * @returns Uploaded material
   */
  async uploadMaterial(
    file: File,
    projectId?: string,
    onProgress?: UploadProgressCallback
  ): Promise<Material> {
    const formData = new FormData();
    formData.append("file", file);

    if (projectId) {
      formData.append("project_id", projectId);
    }

    const response = await api.post<Material>("/materials/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    });

    return response.data;
  },

  /**
   * Upload multiple materials at once
   * @param files - Array of files to upload
   * @param projectId - Optional project ID to associate with
   * @param onProgress - Optional progress callback (overall progress)
   * @returns Array of uploaded materials
   */
  async uploadMultipleMaterials(
    files: File[],
    projectId?: string,
    onProgress?: UploadProgressCallback
  ): Promise<Material[]> {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append("files", file);
    });

    if (projectId) {
      formData.append("project_id", projectId);
    }

    const response = await api.post<Material[]>(
      "/materials/upload-multiple",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress(progress);
          }
        },
      }
    );

    return response.data;
  },

  /**
   * Delete material
   * @param id - Material ID
   */
  async deleteMaterial(id: string): Promise<void> {
    await api.delete(`/materials/${id}`);
  },

  /**
   * Associate material with project
   * @param materialId - Material ID
   * @param projectId - Project ID
   * @returns Updated material
   */
  async associateWithProject(
    materialId: string,
    projectId: string
  ): Promise<Material> {
    const response = await api.post<Material>(
      `/materials/${materialId}/projects/${projectId}`
    );
    return response.data;
  },

  /**
   * Remove material from project
   * @param materialId - Material ID
   * @param projectId - Project ID
   */
  async removeFromProject(
    materialId: string,
    projectId: string
  ): Promise<void> {
    await api.delete(`/materials/${materialId}/projects/${projectId}`);
  },

  /**
   * Download material file
   * @param id - Material ID
   * @returns Blob for file download
   */
  async downloadMaterial(id: string): Promise<Blob> {
    const response = await api.get(`/materials/${id}/download`, {
      responseType: "blob",
    });
    return response.data;
  },

  /**
   * Get material preview URL
   * @param id - Material ID
   * @returns Preview URL (for PDFs, images)
   */
  getPreviewUrl(id: string): string {
    const baseUrl =
      import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
    const token = localStorage.getItem("token");
    return `${baseUrl}/materials/${id}/preview?token=${token}`;
  },

  /**
   * Extract text content from material (for AI processing)
   * @param id - Material ID
   * @returns Extracted text content
   */
  async extractContent(
    id: string
  ): Promise<{ content: string; pages?: number }> {
    const response = await api.post(`/materials/${id}/extract`);
    return response.data;
  },

  /**
   * Get supported file types
   * @returns List of supported MIME types
   */
  getSupportedTypes(): string[] {
    return [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
      "image/png",
      "image/jpeg",
      "image/jpg",
    ];
  },

  /**
   * Get supported file extensions for upload
   * @returns List of supported extensions
   */
  getSupportedExtensions(): string[] {
    return [".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg"];
  },

  /**
   * Validate file before upload
   * @param file - File to validate
   * @returns Validation result
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 50 * 1024 * 1024; // 50MB
    const supportedTypes = this.getSupportedTypes();

    if (file.size > maxSize) {
      return { valid: false, error: "File size exceeds 50MB limit" };
    }

    if (!supportedTypes.includes(file.type)) {
      return { valid: false, error: "File type not supported" };
    }

    return { valid: true };
  },
};

export default materialService;
