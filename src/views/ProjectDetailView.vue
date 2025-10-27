<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();
</script>

<template>
  <div class="placeholder-view">
    <el-card>
      <h2>Project Details</h2>
      <p>
        This view will show detailed information about the project, including
        materials, settings, and generated tests.
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
