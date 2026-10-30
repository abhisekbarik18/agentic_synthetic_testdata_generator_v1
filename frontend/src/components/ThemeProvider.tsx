"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
const THEME_STORAGE_KEY = "tdm-theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const initialTheme =
      storedTheme === "light" || storedTheme === "dark"
        ? storedTheme
        : mediaQuery.matches
        ? "dark"
        : "light";

    setTheme(initialTheme);

    if (storedTheme !== "light" && storedTheme !== "dark") {
      const handleSystemThemeChange = (event: MediaQueryListEvent) => {
        const preference = window.localStorage.getItem(THEME_STORAGE_KEY);
        if (preference === "light" || preference === "dark") {
          return;
        }
        setTheme(event.matches ? "dark" : "light");
      };

      mediaQuery.addEventListener("change", handleSystemThemeChange);
      return () => mediaQuery.removeEventListener("change", handleSystemThemeChange);
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    setTheme(nextTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
