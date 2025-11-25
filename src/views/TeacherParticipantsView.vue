<script setup lang="ts">
/**
 * TeacherParticipantsView
 *
 * Manages students and groups for tests:
 * - Add individual students (email, name)
 * - Create and manage groups
 * - Assign students to groups
 * - View all participants
 */
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import ThemeToggle from "@/components/ThemeToggle.vue";
import {
  Plus,
  Delete,
  Edit,
  User,
  UserFilled,
  Search,
  FolderOpened,
} from "@element-plus/icons-vue";
import type { Participant, ParticipantGroup } from "@/types";

const router = useRouter();
const authStore = useAuthStore();
const { t } = useI18n();

// State
const loading = ref(false);
const searchQuery = ref("");
const activeTab = ref("students");

// Dialog states
const showStudentDialog = ref(false);
const studentDialogMode = ref<"create" | "edit">("create");
const editingStudent = ref<Participant | null>(null);

const showGroupDialog = ref(false);
const groupDialogMode = ref<"create" | "edit">("create");
const editingGroup = ref<ParticipantGroup | null>(null);

// Forms
const studentForm = ref({
  email: "",
  firstName: "",
  lastName: "",
  type: "individual" as "individual" | "group-member",
  groupId: undefined as string | undefined,
});

const groupForm = ref({
  name: "",
  description: "",
});

// Mock data
const students = ref<Participant[]>([
  {
    id: "student-1",
    email: "john.doe@university.edu",
    firstName: "John",
    lastName: "Doe",
    type: "group-member",
    groupId: "group-1",
    createdAt: new Date("2024-11-10"),
  },
  {
    id: "student-2",
    email: "jane.smith@university.edu",
    firstName: "Jane",
    lastName: "Smith",
    type: "group-member",
    groupId: "group-1",
    createdAt: new Date("2024-11-10"),
  },
  {
    id: "student-3",
    email: "bob.johnson@university.edu",
    firstName: "Bob",
    lastName: "Johnson",
    type: "individual",
    createdAt: new Date("2024-11-12"),
  },
  {
    id: "student-4",
    email: "alice.williams@university.edu",
    firstName: "Alice",
    lastName: "Williams",
    type: "group-member",
    groupId: "group-2",
    createdAt: new Date("2024-11-15"),
  },
  {
    id: "student-5",
    email: "charlie.brown@university.edu",
    firstName: "Charlie",
    lastName: "Brown",
    type: "individual",
    createdAt: new Date("2024-11-18"),
  },
]);

const groups = ref<ParticipantGroup[]>([
  {
    id: "group-1",
    name: "CS-101 Section A",
    description: "Computer Science Introduction - Morning Section",
    teacherId: "teacher-1",
    membersCount: 2,
    createdAt: new Date("2024-11-01"),
  },
  {
    id: "group-2",
    name: "CS-101 Section B",
    description: "Computer Science Introduction - Afternoon Section",
    teacherId: "teacher-1",
    membersCount: 1,
    createdAt: new Date("2024-11-05"),
  },
  {
    id: "group-3",
    name: "Advanced Math",
    description: "Graduate level mathematics course",
    teacherId: "teacher-1",
    membersCount: 0,
    createdAt: new Date("2024-11-10"),
  },
]);

// Computed
const filteredStudents = computed(() => {
  if (!searchQuery.value) return students.value;
  const query = searchQuery.value.toLowerCase();
  return students.value.filter(
    (s) =>
      s.email.toLowerCase().includes(query) ||
      s.firstName.toLowerCase().includes(query) ||
      s.lastName.toLowerCase().includes(query)
  );
});

const individualStudents = computed(() =>
  filteredStudents.value.filter((s) => s.type === "individual")
);

const groupMembers = computed(() =>
  filteredStudents.value.filter((s) => s.type === "group-member")
);

// Helpers
const getGroupName = (groupId?: string) => {
  if (!groupId) return "-";
  const group = groups.value.find((g) => g.id === groupId);
  return group?.name || "-";
};

const getGroupMembers = (groupId: string) => {
  return students.value.filter((s) => s.groupId === groupId);
};

const formatDate = (date: Date): string => {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

// Student CRUD
const openAddStudentDialog = () => {
  studentDialogMode.value = "create";
  studentForm.value = {
    email: "",
    firstName: "",
    lastName: "",
    type: "individual",
    groupId: undefined,
  };
  editingStudent.value = null;
  showStudentDialog.value = true;
};

const openEditStudentDialog = (student: Participant) => {
  studentDialogMode.value = "edit";
  studentForm.value = {
    email: student.email,
    firstName: student.firstName,
    lastName: student.lastName,
    type: student.type,
    groupId: student.groupId,
  };
  editingStudent.value = student;
  showStudentDialog.value = true;
};

const saveStudent = () => {
  if (
    !studentForm.value.email ||
    !studentForm.value.firstName ||
    !studentForm.value.lastName
  ) {
    ElMessage.warning(
      t("participantsPage.fillRequired") || "Please fill all required fields"
    );
    return;
  }

  // Email validation
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(studentForm.value.email)) {
    ElMessage.warning(
      t("participantsPage.invalidEmail") || "Please enter a valid email"
    );
    return;
  }

  if (studentDialogMode.value === "create") {
    // Check for duplicate email
    if (students.value.some((s) => s.email === studentForm.value.email)) {
      ElMessage.warning(
        t("participantsPage.duplicateEmail") ||
          "This email is already registered"
      );
      return;
    }

    const newStudent: Participant = {
      id: `student-${Date.now()}`,
      email: studentForm.value.email,
      firstName: studentForm.value.firstName,
      lastName: studentForm.value.lastName,
      type: studentForm.value.type,
      groupId:
        studentForm.value.type === "group-member"
          ? studentForm.value.groupId
          : undefined,
      createdAt: new Date(),
    };

    students.value.push(newStudent);

    // Update group member count
    if (newStudent.groupId) {
      const group = groups.value.find((g) => g.id === newStudent.groupId);
      if (group) group.membersCount++;
    }

    ElMessage.success(t("participantsPage.studentAdded") || "Student added");
  } else if (editingStudent.value) {
    // Check for duplicate email (excluding current student)
    if (
      students.value.some(
        (s) =>
          s.email === studentForm.value.email &&
          s.id !== editingStudent.value!.id
      )
    ) {
      ElMessage.warning(
        t("participantsPage.duplicateEmail") ||
          "This email is already registered"
      );
      return;
    }

    // Update group counts
    const oldGroupId = editingStudent.value.groupId;
    const newGroupId =
      studentForm.value.type === "group-member"
        ? studentForm.value.groupId
        : undefined;

    if (oldGroupId !== newGroupId) {
      if (oldGroupId) {
        const oldGroup = groups.value.find((g) => g.id === oldGroupId);
        if (oldGroup) oldGroup.membersCount--;
      }
      if (newGroupId) {
        const newGroup = groups.value.find((g) => g.id === newGroupId);
        if (newGroup) newGroup.membersCount++;
      }
    }

    // Update student
    const index = students.value.findIndex(
      (s) => s.id === editingStudent.value!.id
    );
    if (index > -1) {
      students.value[index] = {
        ...editingStudent.value,
        email: studentForm.value.email,
        firstName: studentForm.value.firstName,
        lastName: studentForm.value.lastName,
        type: studentForm.value.type,
        groupId: newGroupId,
      };
    }

    ElMessage.success(
      t("participantsPage.studentUpdated") || "Student updated"
    );
  }

  showStudentDialog.value = false;
};

const deleteStudent = async (student: Participant) => {
  try {
    await ElMessageBox.confirm(
      `${t("participantsPage.confirmDeleteStudent") || "Delete student"} ${
        student.firstName
      } ${student.lastName}?`,
      t("common.delete"),
      {
        confirmButtonText: t("common.delete"),
        cancelButtonText: t("common.cancel"),
        type: "warning",
      }
    );

    // Update group count
    if (student.groupId) {
      const group = groups.value.find((g) => g.id === student.groupId);
      if (group) group.membersCount--;
    }

    const index = students.value.findIndex((s) => s.id === student.id);
    if (index > -1) {
      students.value.splice(index, 1);
    }

    ElMessage.success(
      t("participantsPage.studentDeleted") || "Student deleted"
    );
  } catch {
    // User cancelled
  }
};

// Group CRUD
const openAddGroupDialog = () => {
  groupDialogMode.value = "create";
  groupForm.value = { name: "", description: "" };
  editingGroup.value = null;
  showGroupDialog.value = true;
};

const openEditGroupDialog = (group: ParticipantGroup) => {
  groupDialogMode.value = "edit";
  groupForm.value = { name: group.name, description: group.description || "" };
  editingGroup.value = group;
  showGroupDialog.value = true;
};

const saveGroup = () => {
  if (!groupForm.value.name.trim()) {
    ElMessage.warning(
      t("participantsPage.groupNameRequired") || "Group name is required"
    );
    return;
  }

  if (groupDialogMode.value === "create") {
    const newGroup: ParticipantGroup = {
      id: `group-${Date.now()}`,
      name: groupForm.value.name.trim(),
      description: groupForm.value.description.trim(),
      teacherId: authStore.user?.id || "teacher-1",
      membersCount: 0,
      createdAt: new Date(),
    };
    groups.value.push(newGroup);
    ElMessage.success(t("participantsPage.groupCreated") || "Group created");
  } else if (editingGroup.value) {
    const group = editingGroup.value;
    const index = groups.value.findIndex((g) => g.id === group.id);
    if (index > -1) {
      groups.value[index].name = groupForm.value.name.trim();
      groups.value[index].description = groupForm.value.description.trim();
    }
    ElMessage.success(t("participantsPage.groupUpdated") || "Group updated");
  }

  showGroupDialog.value = false;
};

const deleteGroup = async (group: ParticipantGroup) => {
  const groupMembersList = getGroupMembers(group.id);

  const confirmMessage =
    groupMembersList.length > 0
      ? `${t("participantsPage.confirmDeleteGroup") || "Delete group"} "${
          group.name
        }"? ${groupMembersList.length} members will become individual students.`
      : `${t("participantsPage.confirmDeleteGroup") || "Delete group"} "${
          group.name
        }"?`;

  try {
    await ElMessageBox.confirm(confirmMessage, t("common.delete"), {
      confirmButtonText: t("common.delete"),
      cancelButtonText: t("common.cancel"),
      type: "warning",
    });

    // Move members to individual
    groupMembersList.forEach((member) => {
      member.type = "individual";
      member.groupId = undefined;
    });

    const index = groups.value.findIndex((g) => g.id === group.id);
    if (index > -1) {
      groups.value.splice(index, 1);
    }

    ElMessage.success(t("participantsPage.groupDeleted") || "Group deleted");
  } catch {
    // User cancelled
  }
};

const handleLogout = () => {
  authStore.logout();
  router.push("/login");
};
</script>

<template>
  <div class="page-wrap">
    <el-container>
      <el-header class="page-header">
        <div class="header-content">
          <h1>{{ t("teacher.participants") }}</h1>
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
        <div class="participants-content">
          <!-- Actions Bar -->
          <div class="actions-bar">
            <el-input
              v-model="searchQuery"
              :placeholder="
                t('participantsPage.searchStudents') || 'Search students...'
              "
              :prefix-icon="Search"
              clearable
              style="width: 300px"
            />
            <div class="actions-buttons">
              <el-button
                type="primary"
                :icon="Plus"
                @click="openAddStudentDialog"
              >
                {{ t("participantsPage.addStudent") || "Add Student" }}
              </el-button>
              <el-button :icon="Plus" @click="openAddGroupDialog">
                {{ t("participantsPage.createGroup") || "Create Group" }}
              </el-button>
            </div>
          </div>

          <!-- Stats Cards -->
          <div class="stats-row">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon students">
                <el-icon :size="24"><UserFilled /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ students.length }}</div>
                <div class="stat-label">
                  {{ t("participantsPage.totalStudents") || "Total Students" }}
                </div>
              </div>
            </el-card>
            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon groups">
                <el-icon :size="24"><FolderOpened /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ groups.length }}</div>
                <div class="stat-label">
                  {{ t("participantsPage.totalGroups") || "Groups" }}
                </div>
              </div>
            </el-card>
            <el-card class="stat-card" shadow="hover">
              <div class="stat-icon individual">
                <el-icon :size="24"><User /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ individualStudents.length }}</div>
                <div class="stat-label">
                  {{ t("participantsPage.individualStudents") || "Individual" }}
                </div>
              </div>
            </el-card>
          </div>

          <!-- Tabs -->
          <el-tabs v-model="activeTab">
            <!-- Students Tab -->
            <el-tab-pane
              :label="t('participantsPage.allStudents') || 'All Students'"
              name="students"
            >
              <el-table
                :data="filteredStudents"
                style="width: 100%"
                v-loading="loading"
              >
                <el-table-column
                  :label="t('participantsPage.name') || 'Name'"
                  min-width="180"
                >
                  <template #default="{ row }">
                    <div class="student-name">
                      <el-avatar :size="32" :icon="User" />
                      <span>{{ row.firstName }} {{ row.lastName }}</span>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column
                  prop="email"
                  :label="t('participantsPage.email') || 'Email'"
                  min-width="220"
                />

                <el-table-column
                  :label="t('participantsPage.type') || 'Type'"
                  width="150"
                >
                  <template #default="{ row }">
                    <el-tag
                      :type="row.type === 'individual' ? 'info' : 'success'"
                      size="small"
                    >
                      {{
                        row.type === "individual"
                          ? t("participantsPage.individual") || "Individual"
                          : t("participantsPage.groupMember") || "Group Member"
                      }}
                    </el-tag>
                  </template>
                </el-table-column>

                <el-table-column
                  :label="t('participantsPage.group') || 'Group'"
                  width="180"
                >
                  <template #default="{ row }">
                    {{ getGroupName(row.groupId) }}
                  </template>
                </el-table-column>

                <el-table-column
                  :label="t('participantsPage.addedOn') || 'Added On'"
                  width="130"
                >
                  <template #default="{ row }">
                    {{ formatDate(row.createdAt) }}
                  </template>
                </el-table-column>

                <el-table-column
                  :label="t('materialsPage.actions') || 'Actions'"
                  width="120"
                  align="right"
                >
                  <template #default="{ row }">
                    <el-button-group>
                      <el-tooltip :content="t('common.edit')" placement="top">
                        <el-button
                          size="small"
                          :icon="Edit"
                          @click="openEditStudentDialog(row)"
                        />
                      </el-tooltip>
                      <el-tooltip :content="t('common.delete')" placement="top">
                        <el-button
                          size="small"
                          type="danger"
                          :icon="Delete"
                          @click="deleteStudent(row)"
                        />
                      </el-tooltip>
                    </el-button-group>
                  </template>
                </el-table-column>
              </el-table>

              <div v-if="filteredStudents.length === 0" class="empty-state">
                <el-icon :size="64" class="empty-icon"><UserFilled /></el-icon>
                <h3>
                  {{ t("participantsPage.noStudents") || "No students yet" }}
                </h3>
                <p>
                  {{
                    t("participantsPage.addFirstStudent") ||
                    "Add your first student to get started"
                  }}
                </p>
                <el-button
                  type="primary"
                  :icon="Plus"
                  @click="openAddStudentDialog"
                >
                  {{ t("participantsPage.addStudent") || "Add Student" }}
                </el-button>
              </div>
            </el-tab-pane>

            <!-- Groups Tab -->
            <el-tab-pane
              :label="t('participantsPage.groups') || 'Groups'"
              name="groups"
            >
              <div v-if="groups.length === 0" class="empty-state">
                <el-icon :size="64" class="empty-icon"
                  ><FolderOpened
                /></el-icon>
                <h3>{{ t("participantsPage.noGroups") || "No groups yet" }}</h3>
                <p>
                  {{
                    t("participantsPage.createFirstGroup") ||
                    "Create a group to organize your students"
                  }}
                </p>
                <el-button
                  type="primary"
                  :icon="Plus"
                  @click="openAddGroupDialog"
                >
                  {{ t("participantsPage.createGroup") || "Create Group" }}
                </el-button>
              </div>

              <div v-else class="groups-grid">
                <el-card
                  v-for="group in groups"
                  :key="group.id"
                  class="group-card"
                  shadow="hover"
                >
                  <template #header>
                    <div class="group-header">
                      <div class="group-title">
                        <el-icon :size="20" class="group-icon"
                          ><FolderOpened
                        /></el-icon>
                        <span>{{ group.name }}</span>
                      </div>
                      <el-button-group size="small">
                        <el-button
                          :icon="Edit"
                          @click="openEditGroupDialog(group)"
                        />
                        <el-button
                          type="danger"
                          :icon="Delete"
                          @click="deleteGroup(group)"
                        />
                      </el-button-group>
                    </div>
                  </template>

                  <p v-if="group.description" class="group-description">
                    {{ group.description }}
                  </p>

                  <div class="group-stats">
                    <el-tag type="info"
                      >{{ group.membersCount }}
                      {{
                        group.membersCount === 1 ? "member" : "members"
                      }}</el-tag
                    >
                    <span class="group-date"
                      >{{ t("participantsPage.created") || "Created" }}:
                      {{ formatDate(group.createdAt) }}</span
                    >
                  </div>

                  <!-- Group Members Preview -->
                  <div v-if="group.membersCount > 0" class="group-members">
                    <div class="members-label">
                      {{ t("participantsPage.members") || "Members" }}:
                    </div>
                    <div class="members-list">
                      <div
                        v-for="member in getGroupMembers(group.id).slice(0, 3)"
                        :key="member.id"
                        class="member-item"
                      >
                        <el-avatar :size="24" :icon="User" />
                        <span
                          >{{ member.firstName }} {{ member.lastName }}</span
                        >
                      </div>
                      <div
                        v-if="getGroupMembers(group.id).length > 3"
                        class="more-members"
                      >
                        +{{ getGroupMembers(group.id).length - 3 }} more
                      </div>
                    </div>
                  </div>
                </el-card>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-main>
    </el-container>

    <!-- Add/Edit Student Dialog -->
    <el-dialog
      v-model="showStudentDialog"
      :title="
        studentDialogMode === 'create'
          ? t('participantsPage.addStudent') || 'Add Student'
          : t('participantsPage.editStudent') || 'Edit Student'
      "
      width="500px"
    >
      <el-form :model="studentForm" label-position="top">
        <el-form-item :label="t('participantsPage.email') || 'Email'" required>
          <el-input
            v-model="studentForm.email"
            type="email"
            :placeholder="
              t('participantsPage.emailPlaceholder') || 'student@university.edu'
            "
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item
              :label="t('participantsPage.firstName') || 'First Name'"
              required
            >
              <el-input
                v-model="studentForm.firstName"
                :placeholder="
                  t('participantsPage.firstNamePlaceholder') || 'John'
                "
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item
              :label="t('participantsPage.lastName') || 'Last Name'"
              required
            >
              <el-input
                v-model="studentForm.lastName"
                :placeholder="
                  t('participantsPage.lastNamePlaceholder') || 'Doe'
                "
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item
          :label="t('participantsPage.studentType') || 'Student Type'"
        >
          <el-radio-group v-model="studentForm.type">
            <el-radio value="individual">{{
              t("participantsPage.individual") || "Individual"
            }}</el-radio>
            <el-radio value="group-member">{{
              t("participantsPage.groupMember") || "Group Member"
            }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="studentForm.type === 'group-member'"
          :label="t('participantsPage.selectGroup') || 'Select Group'"
        >
          <el-select
            v-model="studentForm.groupId"
            :placeholder="t('participantsPage.chooseGroup') || 'Choose a group'"
            style="width: 100%"
          >
            <el-option
              v-for="group in groups"
              :key="group.id"
              :label="group.name"
              :value="group.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showStudentDialog = false">{{
          t("common.cancel")
        }}</el-button>
        <el-button type="primary" @click="saveStudent">{{
          t("common.save")
        }}</el-button>
      </template>
    </el-dialog>

    <!-- Add/Edit Group Dialog -->
    <el-dialog
      v-model="showGroupDialog"
      :title="
        groupDialogMode === 'create'
          ? t('participantsPage.createGroup') || 'Create Group'
          : t('participantsPage.editGroup') || 'Edit Group'
      "
      width="500px"
    >
      <el-form :model="groupForm" label-position="top">
        <el-form-item
          :label="t('participantsPage.groupName') || 'Group Name'"
          required
        >
          <el-input
            v-model="groupForm.name"
            :placeholder="
              t('participantsPage.groupNamePlaceholder') ||
              'e.g., CS-101 Section A'
            "
          />
        </el-form-item>

        <el-form-item
          :label="t('participantsPage.description') || 'Description'"
        >
          <el-input
            v-model="groupForm.description"
            type="textarea"
            :rows="3"
            :placeholder="
              t('participantsPage.descriptionPlaceholder') ||
              'Optional description for this group'
            "
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showGroupDialog = false">{{
          t("common.cancel")
        }}</el-button>
        <el-button type="primary" @click="saveGroup">{{
          t("common.save")
        }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page-wrap {
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

.participants-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-xl);
}

// Actions Bar
.actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
  gap: var(--spacing-md);

  .actions-buttons {
    display: flex;
    gap: var(--spacing-sm);
  }
}

// Stats Row
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.stat-card {
  :deep(.el-card__body) {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;

    &.students {
      background: var(--color-primary);
    }

    &.groups {
      background: var(--color-warning);
    }

    &.individual {
      background: var(--color-info);
    }
  }

  .stat-info {
    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--color-text);
    }

    .stat-label {
      font-size: 0.85rem;
      color: var(--color-text-light);
    }
  }
}

// Students Table
.student-name {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);

  span {
    font-weight: 500;
  }
}

// Empty State
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  text-align: center;

  .empty-icon {
    color: var(--color-neutral);
    margin-bottom: var(--spacing-md);
  }

  h3 {
    margin: 0 0 var(--spacing-sm);
    color: var(--color-text);
  }

  p {
    margin: 0 0 var(--spacing-lg);
    color: var(--color-text-light);
  }
}

// Groups Grid
.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--spacing-lg);
}

.group-card {
  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .group-title {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-weight: 600;

      .group-icon {
        color: var(--color-warning);
      }
    }
  }

  .group-description {
    color: var(--color-text-light);
    font-size: 0.9rem;
    margin: 0 0 var(--spacing-md);
  }

  .group-stats {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);

    .group-date {
      font-size: 0.8rem;
      color: var(--color-text-light);
    }
  }

  .group-members {
    border-top: 1px solid var(--color-border);
    padding-top: var(--spacing-md);

    .members-label {
      font-size: 0.85rem;
      color: var(--color-text-light);
      margin-bottom: var(--spacing-sm);
    }

    .members-list {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .member-item {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      font-size: 0.9rem;
    }

    .more-members {
      font-size: 0.85rem;
      color: var(--color-text-light);
      font-style: italic;
    }
  }
}

// Responsive
@media (max-width: 768px) {
  .participants-content {
    padding: var(--spacing-md);
  }

  .actions-bar {
    flex-direction: column;
    align-items: stretch;

    .actions-buttons {
      justify-content: center;
    }
  }

  .groups-grid {
    grid-template-columns: 1fr;
  }
}
</style>
