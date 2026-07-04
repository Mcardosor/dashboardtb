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

// ── Paleta base ───────────────────────────────────────────────────────────────
export const C = {
  bg: "#0a0e14",
  surface: "#10151d",
  card: "#121923",
  border: "#1e2836",
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

// Escalas sequenciais dos mapas
export const SEQ_CASOS = ["#0d1b2e", "#123a5c", "#1a5c8a", "#2b7bb9", "#58a6ff", "#a5d6ff"];
export const SEQ_MORTALIDADE = ["#2b0f12", "#5c1a1e", "#8a2226", "#c93026", "#f85149", "#ffa198"];

export const fmt = new Intl.NumberFormat("pt-BR");
export const fmt1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export const FONT = "'Inter Variable', Inter, system-ui, sans-serif";

/** Base compartilhada de todos os gráficos. */
export const baseOption = {
  textStyle: { fontFamily: FONT, color: C.muted },
  tooltip: {
    backgroundColor: "rgba(16, 21, 29, .96)",
    borderColor: C.border,
    textStyle: { color: C.text, fontSize: 12.5, fontFamily: FONT },
    padding: [8, 12],
    extraCssText: "box-shadow: 0 8px 24px rgba(0,0,0,.5); border-radius: 10px;",
  },
};
