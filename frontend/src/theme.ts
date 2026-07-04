/**
 * theme.ts — Paleta, registro do ECharts (tree-shaken) e tema global.
 * As cores semânticas de TB vêm do dashboard original (src/constantes.py).
 */
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, MapChart, PieChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
  VisualMapComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart, LineChart, PieChart, MapChart, HeatmapChart,
  GridComponent, TooltipComponent, LegendComponent, VisualMapComponent,
  MarkLineComponent, DataZoomComponent, CanvasRenderer,
]);

export { echarts };

// ── Paletas (claro = padrão, escuro = alternativo) ────────────────────────────
export const DARK = {
  bg: "#0a0e14",
  surface: "#10151d",
  card: "#121923",
  border: "#1e2836",
  borderlight: "#2a3646",
  text: "#e6edf3",
  muted: "#8b98a8",
  faint: "#5c6a7a",
  accent: "#58a6ff",
  green: "#3fb950",
  red: "#f85149",
  orange: "#ffa657",
  yellow: "#d29922",
  purple: "#a371f7",
  pink: "#f778ba",
};

export const LIGHT: typeof DARK = {
  bg: "#f4f6f9",
  surface: "#ffffff",
  card: "#ffffff",
  border: "#dde3ea",
  borderlight: "#c8d0da",
  text: "#1a2332",
  muted: "#5a6a7e",
  faint: "#8fa0b2",
  accent: "#2b7bb9",
  green: "#1a7a4c",
  red: "#c9302c",
  orange: "#c1631a",
  yellow: "#a86f0a",
  purple: "#7c4fd1",
  pink: "#c23b7a",
};

// Paleta ativa — mutada em memória por applyChartTheme(), não reatribuída
// (importações de `C` guardam a referência ao objeto, não um snapshot).
export const C = { ...LIGHT };

export type ThemeName = "light" | "dark";

// Cores semânticas por rótulo epidemiológico
export const TB_COLORS: Record<string, string> = {
  "Cura": "#2ea043",
  "Óbito por TB": "#da3633",
  "Óbito por outras causas": "#8957e5",
  "Abandono": "#d29922",
  "Abandono Primário": "#bb8009",
  "Falência": "#f85149",
  "TB-DR": "#cf222e",
  "Transferência": "#1f6feb",
  "Mudança de Esquema": "#ffa657",
  "Em acompanhamento": "#388bfd",
  // Grupos de desfecho
  "Interrupção": "#d29922",
  "Óbito": "#da3633",
  "Não avaliado": "#484f58",
  // Testes / status
  "Positivo": "#da3633",
  "Negativo": "#3fb950",
  "Em andamento": "#d29922",
  "Não realizado": "#a371f7",
  "Positiva": "#da3633",
  "Negativa": "#3fb950",
  "Não realizada": "#a371f7",
  "Não se aplica": "#79c0ff",
  "Detectável sensível à Rifampicina": "#d29922",
  "Detectável resistente à Rifampicina": "#da3633",
  "Não detectável": "#3fb950",
  "Inconclusivo": "#d2a8ff",
  // Sexo
  "Masculino": "#58a6ff",
  "Feminino": "#f778ba",
  // Sim / não
  "Sim": "#da3633",
  "Não": "#3fb950",
  "Ignorado": "#6e7681",
  "Não informado": "#484f58",
  // Raça/cor
  "Branca": "#79c0ff",
  "Preta": "#a371f7",
  "Parda": "#d2a8ff",
  "Amarela": "#f0b342",
  "Indígena": "#3fb950",
  "Indigena": "#3fb950",
  // Forma clínica
  "Pulmonar": "#58a6ff",
  "Extrapulmonar": "#a371f7",
  "Pulmonar + Extrapulmonar": "#d2a8ff",
  // Tipo de entrada
  "Caso Novo": "#3fb950",
  "Recidiva": "#d29922",
  "Reingresso após Abandono": "#f0883e",
  "Reingresso Após Abandono": "#f0883e",
  "Não Sabe": "#6e7681",
  "Pós-óbito": "#a40e26",
};

const FALLBACK = ["#58a6ff", "#a371f7", "#3fb950", "#d29922", "#f778ba", "#79c0ff", "#d2a8ff", "#ffa657"];

/** Mapeia rótulos → cores TB, com fallback determinístico. */
export function tbColors(labels: string[]): string[] {
  let i = 0;
  return labels.map((l) => TB_COLORS[l] ?? FALLBACK[i++ % FALLBACK.length]);
}

// Escalas sequenciais dos mapas (claro: pálido→saturado; escuro: o inverso,
// pra combinar com o fundo do card em cada tema). Mutáveis — ver applyChartTheme.
const SEQ_CASOS_DARK = ["#0d1b2e", "#123a5c", "#1a5c8a", "#2b7bb9", "#58a6ff", "#a5d6ff"];
const SEQ_CASOS_LIGHT = ["#eaf3fb", "#c7e2f9", "#8cc7f0", "#4f9fdb", "#2b7bb9", "#123a5c"];
const SEQ_MORTALIDADE_DARK = ["#2b0f12", "#5c1a1e", "#8a2226", "#c93026", "#f85149", "#ffa198"];
const SEQ_MORTALIDADE_LIGHT = ["#fdecea", "#f8c9c2", "#f0968a", "#e2594a", "#c9302c", "#7a1410"];

export let SEQ_CASOS: string[] = SEQ_CASOS_LIGHT;
export let SEQ_MORTALIDADE: string[] = SEQ_MORTALIDADE_LIGHT;

// Escala universal para heatmaps/rankings de intensidade (pálido→vermelho),
// pensada pra funcionar em ambos os temas sem precisar trocar.
export const SEQ_INTENSIDADE = ["#fff3d6", "#ffd166", "#f4a261", "#e76f51", "#d62828"];

export const fmt = new Intl.NumberFormat("pt-BR");
export const fmt1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const FONT = "'Inter Variable', Inter, system-ui, sans-serif";

/** Base compartilhada de todos os gráficos — mutada por applyChartTheme(). */
export const baseOption = {
  textStyle: { fontFamily: FONT, color: C.muted },
  tooltip: {
    backgroundColor: "rgba(255, 255, 255, .97)",
    borderColor: C.border,
    textStyle: { color: C.text, fontSize: 12.5, fontFamily: FONT },
    padding: [8, 12],
    extraCssText: "box-shadow: 0 8px 24px rgba(20,30,50,.12); border-radius: 10px;",
  },
};

/** Aplica a paleta do tema em C/baseOption (mesma referência, mutada in-place). */
export function applyChartTheme(theme: ThemeName) {
  Object.assign(C, theme === "dark" ? DARK : LIGHT);
  baseOption.textStyle.color = C.muted;
  baseOption.tooltip.borderColor = C.border;
  baseOption.tooltip.textStyle.color = C.text;
  baseOption.tooltip.backgroundColor =
    theme === "dark" ? "rgba(16, 21, 29, .96)" : "rgba(255, 255, 255, .97)";
  baseOption.tooltip.extraCssText =
    theme === "dark"
      ? "box-shadow: 0 8px 24px rgba(0,0,0,.5); border-radius: 10px;"
      : "box-shadow: 0 8px 24px rgba(20,30,50,.12); border-radius: 10px;";
  SEQ_CASOS = theme === "dark" ? SEQ_CASOS_DARK : SEQ_CASOS_LIGHT;
  SEQ_MORTALIDADE = theme === "dark" ? SEQ_MORTALIDADE_DARK : SEQ_MORTALIDADE_LIGHT;
}
