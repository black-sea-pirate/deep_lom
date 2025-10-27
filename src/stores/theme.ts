import { defineStore } from "pinia";
import { ref, watch } from "vue";

export const useThemeStore = defineStore("theme", () => {
  const isDark = ref(localStorage.getItem("theme") === "dark");

  const toggleTheme = () => {
    isDark.value = !isDark.value;
  };

  const setTheme = (dark: boolean) => {
    isDark.value = dark;
  };

  // Watch for changes and apply to DOM
  watch(
    isDark,
    (dark) => {
      if (dark) {
        document.documentElement.classList.add("dark");
        localStorage.setItem("theme", "dark");
      } else {
        document.documentElement.classList.remove("dark");
        localStorage.setItem("theme", "light");
      }
    },
    { immediate: true }
  );

  return {
    isDark,
    toggleTheme,
    setTheme,
  };
});
