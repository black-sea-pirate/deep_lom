// Roboto Regular font for jsPDF with Cyrillic support
// This is a minimal subset - for full support, a larger font file would be needed

import { jsPDF } from "jspdf";

// Function to add Roboto font to jsPDF document
// Since embedding full font is large, we'll use a workaround:
// Convert Cyrillic to Latin transliteration for PDF compatibility

const cyrillicToLatin: Record<string, string> = {
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "yo",
  ж: "zh",
  з: "z",
  и: "i",
  й: "y",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "kh",
  ц: "ts",
  ч: "ch",
  ш: "sh",
  щ: "shch",
  ъ: "",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya",
  А: "A",
  Б: "B",
  В: "V",
  Г: "G",
  Д: "D",
  Е: "E",
  Ё: "Yo",
  Ж: "Zh",
  З: "Z",
  И: "I",
  Й: "Y",
  К: "K",
  Л: "L",
  М: "M",
  Н: "N",
  О: "O",
  П: "P",
  Р: "R",
  С: "S",
  Т: "T",
  У: "U",
  Ф: "F",
  Х: "Kh",
  Ц: "Ts",
  Ч: "Ch",
  Ш: "Sh",
  Щ: "Shch",
  Ъ: "",
  Ы: "Y",
  Ь: "",
  Э: "E",
  Ю: "Yu",
  Я: "Ya",
  // Ukrainian specific
  і: "i",
  І: "I",
  ї: "yi",
  Ї: "Yi",
  є: "ye",
  Є: "Ye",
  ґ: "g",
  Ґ: "G",
};

export function transliterate(text: string): string {
  if (!text) return "";
  return text
    .split("")
    .map((char) => cyrillicToLatin[char] ?? char)
    .join("");
}

// For proper Unicode support, we need to use a different approach
// Using standard PDF fonts with character encoding
export function setupPDFFont(doc: jsPDF): void {
  // jsPDF standard fonts don't support Cyrillic
  // We'll use transliteration as fallback
  doc.setFont("helvetica", "normal");
}
