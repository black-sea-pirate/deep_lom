import { createI18n } from "vue-i18n";
import en from "./locales/en";
import pl from "./locales/pl";
import ua from "./locales/ua";
import ru from "./locales/ru";

const messages = {
  en,
  pl,
  ua,
  ru,
};

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem("locale") || "en",
  fallbackLocale: "en",
  messages,
  globalInjection: true,
});

export default i18n;
