<script setup lang="ts">
/**
 * TeacherMaterialsView
 *
 * Manages educational materials for AI test generation:
 * - File upload with drag & drop
 * - Folder management (create, edit, delete folders)
 * - Materials list with preview, download, delete
 * - Move files to folders
 * - File type validation
 * - Upload progress tracking
 *
 * Materials are used by GPT to generate personalized tests
 */
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import ThemeToggle from "@/components/ThemeToggle.vue";
import {
  Upload,
  Document,
  Picture,
  Delete,
  Download,
  View,
  FolderOpened,
  Folder,
  FolderAdd,
  Edit,
  Back,
  Plus,
} from "@element-plus/icons-vue";
import type { UploadFile, UploadProps } from "element-plus";
import { materialService } from "@/services/material.service";
import type { Material, MaterialFolder } from "@/types";

// Router and stores
const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

// State
const loading = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);

// Folder state
const currentFolderId = ref<string | null>(null);
const showFolderDialog = ref(false);
const folderDialogMode = ref<"create" | "edit">("create");
const editingFolder = ref<MaterialFolder | null>(null);
const folderForm = ref({
  name: "",
  description: "",
});

// Move to folder dialog
const showMoveDialog = ref(false);
const movingMaterial = ref<Material | null>(null);

// Data from API
const folders = ref<MaterialFolder[]>([]);
const materials = ref<Material[]>([]);

// Load data from API
const loadFolders = async () => {
  try {
    const data = await materialService.getFolders();
    folders.value = data || [];
  } catch (error) {
    console.error("Failed to load folders:", error);
    ElMessage.error(
      t("materialsPage.loadFoldersError") || "Failed to load folders"
    );
  }
};

const loadMaterials = async () => {
  loading.value = true;
  try {
    const response = await materialService.getMaterials({
      page: 1,
      size: 100,
      folderId: currentFolderId.value || undefined,
    });
    materials.value = response.items || [];
  } catch (error) {
    console.error("Failed to load materials:", error);
    ElMessage.error(t("materialsPage.loadError") || "Failed to load materials");
  } finally {
    loading.value = false;
  }
};

// Initialize on mount
onMounted(async () => {
  await Promise.all([loadFolders(), loadMaterials()]);
});

// Computed
const hasMaterials = computed(() => filteredMaterials.value.length > 0);
const hasFolders = computed(() => folders.value.length > 0);

// Get current folder object
const currentFolder = computed(() => {
  if (!currentFolderId.value) return null;
  return folders.value.find((f) => f.id === currentFolderId.value) || null;
});

// Filter materials by current folder
const filteredMaterials = computed(() => {
  if (currentFolderId.value) {
    return materials.value.filter((m) => m.folderId === currentFolderId.value);
  }
  // Root level: show files without folder
  return materials.value.filter((m) => !m.folderId);
});

// Get available folders for move dialog (excluding current folder)
const availableFolders = computed(() => {
  return [
    { id: null, name: t("materialsPage.rootFolder") || "Root (No Folder)" },
    ...folders.value.filter((f) => f.id !== movingMaterial.value?.folderId),
  ];
});

/**
 * Get file icon based on file type
 */
const getFileIcon = (fileType: string) => {
  if (fileType.includes("image")) return Picture;
  return Document;
};

/**
 * Get file type display name
 */
const getFileTypeLabel = (fileType: string): string => {
  const types: Record<string, string> = {
    "application/pdf": "PDF",
    "application/msword": "DOC",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
      "DOCX",
    "text/plain": "TXT",
    "image/png": "PNG",
    "image/jpeg": "JPG",
    "image/jpg": "JPG",
  };
  return types[fileType] || fileType.split("/")[1]?.toUpperCase() || "FILE";
};

/**
 * Format date for display
 */
const formatDate = (date: Date): string => {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

// ============ FOLDER FUNCTIONS ============

/**
 * Navigate to folder
 */
const openFolder = async (folder: MaterialFolder) => {
  currentFolderId.value = folder.id;
  await loadMaterials();
};

/**
 * Navigate back to root
 */
const goBack = async () => {
  currentFolderId.value = null;
  await loadMaterials();
};

/**
 * Open create folder dialog
 */
const openCreateFolderDialog = () => {
  folderDialogMode.value = "create";
  folderForm.value = { name: "", description: "" };
  editingFolder.value = null;
  showFolderDialog.value = true;
};

/**
 * Open edit folder dialog
 */
const openEditFolderDialog = (folder: MaterialFolder) => {
  folderDialogMode.value = "edit";
  folderForm.value = {
    name: folder.name,
    description: folder.description || "",
  };
  editingFolder.value = folder;
  showFolderDialog.value = true;
};

/**
 * Save folder (create or edit)
 */
const saveFolder = async () => {
  if (!folderForm.value.name.trim()) {
    ElMessage.warning(
      t("materialsPage.folderNameRequired") || "Folder name is required"
    );
    return;
  }

  loading.value = true;
  try {
    if (folderDialogMode.value === "create") {
      await materialService.createFolder({
        name: folderForm.value.name.trim(),
        description: folderForm.value.description.trim() || undefined,
      });
      ElMessage.success(t("materialsPage.folderCreated") || "Folder created");
    } else if (editingFolder.value) {
      await materialService.updateFolder(editingFolder.value.id, {
        name: folderForm.value.name.trim(),
        description: folderForm.value.description.trim() || undefined,
      });
      ElMessage.success(t("materialsPage.folderUpdated") || "Folder updated");
    }

    showFolderDialog.value = false;
    await loadFolders();
  } catch (error: any) {
    const message = error.response?.data?.detail || "Failed to save folder";
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
};

/**
 * Delete folder
 */
const handleDeleteFolder = async (folder: MaterialFolder) => {
  const confirmMessage =
    folder.materialsCount > 0
      ? `${t("materialsPage.confirmDeleteFolder") || "Delete folder"} "${
          folder.name
        }"? ${folder.materialsCount} files will be moved to root.`
      : `${t("materialsPage.confirmDeleteFolder") || "Delete folder"} "${
          folder.name
        }"?`;

  try {
    await ElMessageBox.confirm(confirmMessage, t("common.delete"), {
      confirmButtonText: t("common.delete"),
      cancelButtonText: t("common.cancel"),
      type: "warning",
    });

    loading.value = true;
    await materialService.deleteFolder(folder.id);
    ElMessage.success(t("materialsPage.folderDeleted") || "Folder deleted");
    await Promise.all([loadFolders(), loadMaterials()]);
  } catch (error: any) {
    if (error !== "cancel") {
      const message = error.response?.data?.detail || "Failed to delete folder";
      ElMessage.error(message);
    }
  } finally {
    loading.value = false;
  }
};

/**
 * Open move to folder dialog
 */
const openMoveDialog = (material: Material) => {
  movingMaterial.value = material;
  showMoveDialog.value = true;
};

/**
 * Move material to selected folder
 */
const moveToFolder = async (targetFolderId: string | null) => {
  if (!movingMaterial.value) return;

  loading.value = true;
  try {
    await materialService.moveMaterialToFolder(
      movingMaterial.value.id,
      targetFolderId
    );
    showMoveDialog.value = false;
    movingMaterial.value = null;
    ElMessage.success(t("materialsPage.fileMoved") || "File moved");
    await Promise.all([loadFolders(), loadMaterials()]);
  } catch (error: any) {
    const message = error.response?.data?.detail || "Failed to move file";
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
};

// ============ FILE FUNCTIONS ============

/**
 * Validate file before upload
 */
const beforeUpload: UploadProps["beforeUpload"] = (rawFile) => {
  const maxSize = 50 * 1024 * 1024; // 50MB
  const allowedTypes = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "image/png",
    "image/jpeg",
    "image/jpg",
  ];

  if (!allowedTypes.includes(rawFile.type)) {
    ElMessage.error(t("materialsPage.uploadError") + ": Unsupported file type");
    return false;
  }

  if (rawFile.size > maxSize) {
    ElMessage.error(
      t("materialsPage.uploadError") + ": File size exceeds 50MB"
    );
    return false;
  }

  return true;
};

/**
 * Handle file upload
 * Note: When using http-request, options.file is the raw File object directly
 */
const handleUpload = async (options: any) => {
  uploading.value = true;
  uploadProgress.value = 0;

  try {
    // In http-request mode, file is directly available as options.file (raw File object)
    const file = options.file as File;
    if (!file) {
      throw new Error("No file provided");
    }

    console.log("📤 Uploading file:", file.name, file.type, file.size);

    await materialService.uploadMaterial(
      file,
      currentFolderId.value || undefined,
      (progress) => {
        uploadProgress.value = progress;
      }
    );

    uploadProgress.value = 100;
    ElMessage.success(t("materialsPage.uploadSuccess"));
    await Promise.all([loadFolders(), loadMaterials()]);
  } catch (error: any) {
    // Error is already handled by API interceptor, just log for debugging
    console.error("❌ Upload error:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    });
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
};

/**
 * Handle material deletion
 */
const handleDelete = async (material: Material) => {
  try {
    await ElMessageBox.confirm(
      t("materialsPage.confirmDelete"),
      t("common.delete"),
      {
        confirmButtonText: t("common.delete"),
        cancelButtonText: t("common.cancel"),
        type: "warning",
      }
    );

    loading.value = true;
    await materialService.deleteMaterial(material.id);
    ElMessage.success(t("materialsPage.deleteSuccess"));
    await Promise.all([loadFolders(), loadMaterials()]);
  } catch (error: any) {
    if (error !== "cancel") {
      const message =
        error.response?.data?.detail || "Failed to delete material";
      ElMessage.error(message);
    }
  } finally {
    loading.value = false;
  }
};

/**
 * Handle material preview
 */
const handlePreview = (material: Material) => {
  const previewUrl = materialService.getPreviewUrl(material.id);
  window.open(previewUrl, "_blank");
};

/**
 * Handle material download
 */
const handleDownload = async (material: Material) => {
  try {
    const blob = await materialService.downloadMaterial(material.id);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = material.originalName || material.fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success(
      `Downloading: ${material.originalName || material.fileName}`
    );
  } catch (error) {
    ElMessage.error("Failed to download file");
  }
};

/**
 * Handle logout
 */
const handleLogout = () => {
  authStore.logout();
  router.push("/login");
};
</script>

<template>
  <div class="materials-page">
    <el-container>
      <!-- Header -->
      <el-header class="page-header">
        <div class="header-content">
          <h1>{{ t("materialsPage.title") }}</h1>
          <div class="user-section">
            <ThemeToggle />
            <span
              >{{ authStore.user?.firstName }}
              {{ authStore.user?.lastName }}</span
            >
            <el-button @click="handleLogout" link>{{
              t("common.logout")
            }}</el-button>
          </div>
        </div>
      </el-header>

      <el-main>
        <div class="materials-content">
          <!-- Upload Section -->
          <el-card class="upload-card" shadow="hover">
            <el-upload
              class="upload-area"
              drag
              :auto-upload="true"
              :show-file-list="false"
              :before-upload="beforeUpload"
              :http-request="handleUpload"
              accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
              :disabled="uploading"
            >
              <div class="upload-content" v-if="!uploading">
                <el-icon class="upload-icon"><Upload /></el-icon>
                <div class="upload-text">
                  {{ t("materialsPage.dragDropHint") }}
                </div>
                <div class="upload-hint">
                  {{ t("materialsPage.supportedFormats") }}
                </div>
                <div v-if="currentFolder" class="upload-folder-hint">
                  {{ t("materialsPage.uploadTo") || "Upload to:" }}
                  <strong>{{ currentFolder.name }}</strong>
                </div>
              </div>
              <div class="upload-progress" v-else>
                <el-progress
                  :percentage="uploadProgress"
                  :stroke-width="10"
                  :text-inside="true"
                />
                <div class="upload-status">
                  {{ t("materialsPage.uploading") }}
                </div>
              </div>
            </el-upload>
          </el-card>

          <!-- Folders Section (only show at root level) -->
          <el-card v-if="!currentFolderId" class="folders-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>{{ t("materialsPage.folders") || "Folders" }}</span>
                <el-button
                  type="primary"
                  size="small"
                  :icon="FolderAdd"
                  @click="openCreateFolderDialog"
                >
                  {{ t("materialsPage.createFolder") || "Create Folder" }}
                </el-button>
              </div>
            </template>

            <div v-if="!hasFolders" class="empty-folders">
              <p>
                {{
                  t("materialsPage.noFolders") ||
                  "No folders yet. Create a folder to organize your materials."
                }}
              </p>
            </div>

            <div v-else class="folders-grid">
              <div
                v-for="folder in folders"
                :key="folder.id"
                class="folder-item"
                @click="openFolder(folder)"
              >
                <div class="folder-icon">
                  <el-icon :size="40"><Folder /></el-icon>
                </div>
                <div class="folder-info">
                  <div class="folder-name">{{ folder.name }}</div>
                  <div class="folder-meta">
                    {{ folder.materialsCount }}
                    {{ folder.materialsCount === 1 ? "file" : "files" }}
                  </div>
                </div>
                <div class="folder-actions" @click.stop>
                  <el-button-group size="small">
                    <el-tooltip :content="t('common.edit')" placement="top">
                      <el-button
                        :icon="Edit"
                        @click="openEditFolderDialog(folder)"
                      />
                    </el-tooltip>
                    <el-tooltip :content="t('common.delete')" placement="top">
                      <el-button
                        type="danger"
                        :icon="Delete"
                        @click="handleDeleteFolder(folder)"
                      />
                    </el-tooltip>
                  </el-button-group>
                </div>
              </div>
            </div>
          </el-card>

          <!-- Materials List -->
          <el-card
            class="materials-list-card"
            shadow="hover"
            v-loading="loading"
          >
            <template #header>
              <div class="card-header">
                <div class="card-header-left">
                  <el-button
                    v-if="currentFolderId"
                    :icon="Back"
                    size="small"
                    @click="goBack"
                    class="back-button"
                  >
                    {{ t("common.back") || "Back" }}
                  </el-button>
                  <span v-if="currentFolder">
                    <el-icon><Folder /></el-icon>
                    {{ currentFolder.name }}
                  </span>
                  <span v-else>{{ t("materialsPage.files") || "Files" }}</span>
                </div>
                <el-tag
                  >{{ filteredMaterials.length }}
                  {{
                    filteredMaterials.length === 1 ? "file" : "files"
                  }}</el-tag
                >
              </div>
            </template>

            <!-- Empty State -->
            <div v-if="!hasMaterials && !loading" class="empty-state">
              <el-icon :size="64" class="empty-icon"><FolderOpened /></el-icon>
              <h3>{{ t("materialsPage.noMaterials") }}</h3>
              <p>{{ t("materialsPage.uploadFirst") }}</p>
            </div>

            <!-- Materials Table -->
            <el-table
              v-else
              :data="filteredMaterials"
              style="width: 100%"
              :row-class-name="() => 'material-row'"
            >
              <!-- File Icon & Name -->
              <el-table-column
                :label="t('materialsPage.fileName')"
                min-width="250"
              >
                <template #default="{ row }">
                  <div class="file-info">
                    <el-icon :size="24" class="file-icon">
                      <component :is="getFileIcon(row.fileType)" />
                    </el-icon>
                    <span class="file-name">{{
                      row.originalName || row.fileName
                    }}</span>
                  </div>
                </template>
              </el-table-column>

              <!-- File Type -->
              <el-table-column :label="t('materialsPage.fileType')" width="100">
                <template #default="{ row }">
                  <el-tag size="small" type="info">
                    {{ getFileTypeLabel(row.fileType) }}
                  </el-tag>
                </template>
              </el-table-column>

              <!-- Upload Date -->
              <el-table-column
                :label="t('materialsPage.uploadDate')"
                width="150"
              >
                <template #default="{ row }">
                  {{ formatDate(row.uploadedAt) }}
                </template>
              </el-table-column>

              <!-- Actions -->
              <el-table-column
                :label="t('materialsPage.actions')"
                width="250"
                align="right"
              >
                <template #default="{ row }">
                  <el-button-group>
                    <el-tooltip
                      :content="t('materialsPage.preview')"
                      placement="top"
                    >
                      <el-button
                        size="small"
                        :icon="View"
                        @click="handlePreview(row)"
                      />
                    </el-tooltip>
                    <el-tooltip
                      :content="t('materialsPage.download')"
                      placement="top"
                    >
                      <el-button
                        size="small"
                        :icon="Download"
                        @click="handleDownload(row)"
                      />
                    </el-tooltip>
                    <el-tooltip
                      :content="
                        t('materialsPage.moveToFolder') || 'Move to folder'
                      "
                      placement="top"
                    >
                      <el-button
                        size="small"
                        :icon="Folder"
                        @click="openMoveDialog(row)"
                      />
                    </el-tooltip>
                    <el-tooltip
                      :content="t('materialsPage.delete')"
                      placement="top"
                    >
                      <el-button
                        size="small"
                        type="danger"
                        :icon="Delete"
                        @click="handleDelete(row)"
                      />
                    </el-tooltip>
                  </el-button-group>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-main>
    </el-container>

    <!-- Create/Edit Folder Dialog -->
    <el-dialog
      v-model="showFolderDialog"
      :title="
        folderDialogMode === 'create'
          ? t('materialsPage.createFolder') || 'Create Folder'
          : t('materialsPage.editFolder') || 'Edit Folder'
      "
      width="500px"
    >
      <el-form :model="folderForm" label-position="top">
        <el-form-item
          :label="t('materialsPage.folderName') || 'Folder Name'"
          required
        >
          <el-input
            v-model="folderForm.name"
            :placeholder="
              t('materialsPage.folderNamePlaceholder') || 'Enter folder name'
            "
          />
        </el-form-item>
        <el-form-item
          :label="t('materialsPage.folderDescription') || 'Description'"
        >
          <el-input
            v-model="folderForm.description"
            type="textarea"
            :rows="3"
            :placeholder="
              t('materialsPage.folderDescriptionPlaceholder') ||
              'Optional description'
            "
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFolderDialog = false">{{
          t("common.cancel")
        }}</el-button>
        <el-button type="primary" @click="saveFolder">{{
          t("common.save")
        }}</el-button>
      </template>
    </el-dialog>

    <!-- Move to Folder Dialog -->
    <el-dialog
      v-model="showMoveDialog"
      :title="t('materialsPage.moveToFolder') || 'Move to Folder'"
      width="400px"
    >
      <p class="move-dialog-hint">
        {{
          t("materialsPage.selectDestination") ||
          "Select destination folder for"
        }}:
        <strong>{{
          movingMaterial?.originalName || movingMaterial?.fileName
        }}</strong>
      </p>
      <div class="folder-select-list">
        <div
          v-for="folder in availableFolders"
          :key="folder.id || 'root'"
          class="folder-select-item"
          :class="{ 'current-folder': folder.id === movingMaterial?.folderId }"
          @click="moveToFolder(folder.id)"
        >
          <el-icon><Folder /></el-icon>
          <span>{{ folder.name }}</span>
          <el-tag
            v-if="folder.id === movingMaterial?.folderId"
            size="small"
            type="info"
          >
            {{ t("materialsPage.current") || "Current" }}
          </el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="showMoveDialog = false">{{
          t("common.cancel")
        }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.materials-page {
  min-height: 100%;
  background: var(--color-surface);
}

.page-header {
  background: var(--color-background);
  box-shadow: var(--shadow-sm);

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;

    h1 {
      font-size: 1.5rem;
      color: var(--color-primary);
    }

    .user-section {
      display: flex;
      align-items: center;
      gap: var(--spacing-md);
    }
  }
}

.materials-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

// Upload Card
.upload-card {
  .upload-area {
    width: 100%;

    :deep(.el-upload) {
      width: 100%;
    }

    :deep(.el-upload-dragger) {
      width: 100%;
      padding: var(--spacing-2xl);
      border: 2px dashed var(--color-neutral);
      border-radius: var(--radius-lg);
      transition: all var(--transition-base);

      &:hover {
        border-color: var(--color-primary);
        background: var(--color-primary-light);
      }
    }
  }

  .upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);

    .upload-icon {
      font-size: 48px;
      color: var(--color-primary);
    }

    .upload-text {
      font-size: 1.1rem;
      color: var(--color-text);
    }

    .upload-hint {
      font-size: 0.9rem;
      color: var(--color-text-light);
    }

    .upload-folder-hint {
      margin-top: var(--spacing-sm);
      padding: var(--spacing-xs) var(--spacing-md);
      background: var(--color-primary-light);
      border-radius: var(--radius-sm);
      font-size: 0.85rem;
      color: var(--color-primary);
    }
  }

  .upload-progress {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    width: 60%;
    margin: 0 auto;

    .el-progress {
      width: 100%;
    }

    .upload-status {
      color: var(--color-primary);
      font-weight: 500;
    }
  }
}

// Folders Card
.folders-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }

  .empty-folders {
    text-align: center;
    padding: var(--spacing-lg);
    color: var(--color-text-light);
  }

  .folders-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: var(--spacing-md);
  }

  .folder-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-base);

    &:hover {
      background: var(--color-surface);
      border-color: var(--color-primary);
      box-shadow: var(--shadow-sm);
    }

    .folder-icon {
      color: var(--color-warning);
    }

    .folder-info {
      flex: 1;
      min-width: 0;

      .folder-name {
        font-weight: 600;
        color: var(--color-text);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .folder-meta {
        font-size: 0.85rem;
        color: var(--color-text-light);
      }
    }

    .folder-actions {
      opacity: 0;
      transition: opacity var(--transition-base);
    }

    &:hover .folder-actions {
      opacity: 1;
    }
  }
}

// Materials List Card
.materials-list-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;

    .card-header-left {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);

      .back-button {
        margin-right: var(--spacing-sm);
      }

      .el-icon {
        color: var(--color-warning);
      }
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-2xl);
    color: var(--color-text-light);

    .empty-icon {
      color: var(--color-neutral);
      margin-bottom: var(--spacing-md);
    }

    h3 {
      margin: 0 0 var(--spacing-sm);
      color: var(--color-text);
    }

    p {
      margin: 0;
    }
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);

    .file-icon {
      color: var(--color-primary);
    }

    .file-name {
      font-weight: 500;
    }
  }

  :deep(.material-row) {
    transition: background-color var(--transition-base);

    &:hover {
      background-color: var(--color-surface);
    }
  }
}

// Move Dialog
.move-dialog-hint {
  margin-bottom: var(--spacing-lg);
  color: var(--color-text-light);

  strong {
    color: var(--color-text);
  }
}

.folder-select-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  max-height: 300px;
  overflow-y: auto;
}

.folder-select-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    background: var(--color-surface);
    border-color: var(--color-primary);
  }

  &.current-folder {
    background: var(--color-surface);
    border-color: var(--color-neutral);
    cursor: default;
    opacity: 0.7;
  }

  .el-icon {
    color: var(--color-warning);
  }

  span {
    flex: 1;
  }
}

// Responsive
@media (max-width: 768px) {
  .materials-content {
    padding: var(--spacing-md);
  }

  .upload-card {
    .upload-content {
      .upload-icon {
        font-size: 36px;
      }
    }

    .upload-progress {
      width: 90%;
    }
  }

  .folders-card {
    .folders-grid {
      grid-template-columns: 1fr;
    }

    .folder-item .folder-actions {
      opacity: 1;
    }
  }
}
</style>
