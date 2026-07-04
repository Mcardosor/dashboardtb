/**
 * theme-context.tsx — Estado do tema claro/escuro (padrão: claro).
 * Persiste em localStorage e aplica tanto no CSS (data-theme no <html>)
 * quanto na paleta dos gráficos ECharts (applyChartTheme em theme.ts).
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { applyChartTheme, type ThemeName } from "./theme";

const CHAVE = "tb-theme";

function temaSalvo(): ThemeName {
  return localStorage.getItem(CHAVE) === "dark" ? "dark" : "light";
}

const ThemeContext = createContext<{ theme: ThemeName; alternar: () => void }>({
  theme: "light",
  alternar: () => {},
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeName>(temaSalvo);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    applyChartTheme(theme);
    localStorage.setItem(CHAVE, theme);
  }, [theme]);

  return (
    <ThemeContext.Provider
      value={{ theme, alternar: () => setTheme((t) => (t === "light" ? "dark" : "light")) }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
