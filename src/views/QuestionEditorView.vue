<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
  <div class="placeholder-view">
    <el-card>
      <h2>Question Editor</h2>
      <p>
        This view will allow teachers to review and edit AI-generated questions,
        provide feedback for adjustments, and customize test content.
      </p>
      <el-button type="primary" @click="router.push('/teacher')"
        >Back to Dashboard</el-button
      >
    </el-card>
  </div>
</template>

<style scoped>
.placeholder-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background-color: var(--color-surface);
}
</style>
