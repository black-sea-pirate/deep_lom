<script setup lang="ts">
import { Moon, Sunny } from "@element-plus/icons-vue";
import { useThemeStore } from "@/stores/theme";

const themeStore = useThemeStore();
</script>

<template>
  <el-switch
    v-model="themeStore.isDark"
    inline-prompt
    :active-icon="Moon"
    :inactive-icon="Sunny"
    size="large"
  />
</template>

<style scoped>
.el-switch {
  --el-switch-on-color: var(--color-primary);
  --el-switch-off-color: var(--color-neutral-darker);
}
</style>
