/**
 * charts.ts — Construtores de opções ECharts compartilhados entre as abas.
 * Todos herdam o tema dark de theme.ts e formatação pt-BR.
 */
import type { Contagem, DesfechoPor, Piramide } from "./api";
import { baseOption, C, FONT, fmt, fmt1, tbColors } from "./theme";

const eixoX = {
  axisLine: { lineStyle: { color: C.border } },
  axisTick: { show: false },
  axisLabel: { color: C.muted, fontSize: 11.5 },
  splitLine: { lineStyle: { color: "#141c28" } },
};
const eixoY = { ...eixoX, splitLine: { lineStyle: { color: "#141c28" } } };

/** Donut com rótulos externos e total no centro. */
export function donut(dados: Contagem[], opts: { max?: number } = {}) {
  const top = opts.max ? dados.slice(0, opts.max) : dados;
  const total = dados.reduce((s, d) => s + d.valor, 0);
  const labels = top.map((d) => d.label);
  return {
    ...baseOption,
    color: tbColors(labels),
    tooltip: {
      ...baseOption.tooltip,
      trigger: "item",
      formatter: (p: any) =>
        `<b>${p.name}</b><br/>${fmt.format(p.value)} casos · ${p.percent?.toFixed(1)}%`,
    },
    legend: {
      bottom: 0,
      icon: "circle",
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
    },
    graphic: {
      type: "text",
      left: "center",
      top: "42%",
      style: {
        text: `${fmt.format(total)}\n{sub|casos}`,
        textAlign: "center",
        fill: C.text,
        fontSize: 21,
        fontWeight: 700,
        fontFamily: FONT,
        rich: { sub: { fontSize: 11, fontWeight: 400, fill: C.muted } },
      } as any,
    },
    series: [{
      type: "pie",
      radius: ["58%", "82%"],
      center: ["50%", "46%"],
      itemStyle: { borderColor: C.bg, borderWidth: 2, borderRadius: 6 },
      label: { show: false },
      emphasis: {
        scaleSize: 6,
        itemStyle: { shadowBlur: 18, shadowColor: "rgba(0,0,0,.45)" },
      },
      data: top.map((d) => ({ name: d.label, value: d.valor })),
    }],
  };
}

/** Barras horizontais (ranking). */
export function barH(
  dados: Contagem[],
  opts: { cor?: string; gradiente?: [string, string]; unidade?: string; max?: number } = {},
) {
  const top = (opts.max ? dados.slice(0, opts.max) : dados).slice().reverse();
  const unidade = opts.unidade ?? "casos";
  return {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      trigger: "item",
      formatter: (p: any) => `<b>${p.name}</b><br/>${fmt.format(p.value)} ${unidade}`,
    },
    grid: { left: 8, right: 52, top: 6, bottom: 6, containLabel: true },
    xAxis: { type: "value", ...eixoX },
    yAxis: {
      type: "category",
      data: top.map((d) => d.label),
      ...eixoY,
      axisLabel: { ...eixoY.axisLabel, fontSize: 12 },
    },
    series: [{
      type: "bar",
      barMaxWidth: 22,
      data: top.map((d) => d.valor),
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: opts.gradiente
          ? {
              type: "linear", x: 0, y: 0, x2: 1, y2: 0,
              colorStops: [
                { offset: 0, color: opts.gradiente[0] },
                { offset: 1, color: opts.gradiente[1] },
              ],
            }
          : (opts.cor ?? C.accent),
      },
      label: {
        show: true,
        position: "right",
        color: C.muted,
        fontSize: 11,
        fontFamily: FONT,
        formatter: (p: any) => fmt.format(p.value),
      },
    }],
  };
}

/** Barras verticais coloridas por rótulo semântico. */
export function barV(dados: Contagem[], opts: { unidade?: string } = {}) {
  const labels = dados.map((d) => d.label);
  const cores = tbColors(labels);
  const unidade = opts.unidade ?? "casos";
  return {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      trigger: "item",
      formatter: (p: any) => `<b>${p.name}</b><br/>${fmt.format(p.value)} ${unidade}`,
    },
    grid: { left: 8, right: 16, top: 24, bottom: 4, containLabel: true },
    xAxis: { type: "category", data: labels, ...eixoX, axisLabel: { ...eixoX.axisLabel, interval: 0, rotate: labels.length > 6 ? 24 : 0 } },
    yAxis: { type: "value", ...eixoY },
    series: [{
      type: "bar",
      barMaxWidth: 44,
      data: dados.map((d, i) => ({ value: d.valor, itemStyle: { color: cores[i], borderRadius: [6, 6, 0, 0] } })),
      label: {
        show: true, position: "top", color: C.muted, fontSize: 11, fontFamily: FONT,
        formatter: (p: any) => fmt.format(p.value),
      },
    }],
  };
}

/** Barras 100% empilhadas: composição de desfechos por categoria. */
export function stacked100(d: DesfechoPor, opts: { horizontal?: boolean } = {}) {
  const { categorias, grupos, pct, n } = d;
  const cores = tbColors(grupos);
  const horizontal = opts.horizontal ?? false;
  const catAxis = {
    type: "category" as const,
    data: categorias,
    ...eixoX,
    axisLabel: { ...eixoX.axisLabel, interval: 0, fontSize: 11.5 },
  };
  const valAxis = {
    type: "value" as const,
    max: 100,
    ...eixoY,
    axisLabel: { ...eixoY.axisLabel, formatter: "{value}%" },
  };
  return {
    ...baseOption,
    color: cores,
    tooltip: {
      ...baseOption.tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: "rgba(88,166,255,.06)" } },
      formatter: (ps: any[]) => {
        const cat = ps[0]?.name;
        const linhas = ps
          .map((p) => `${p.marker} ${p.seriesName}: <b>${fmt1.format(p.value)}%</b>`)
          .join("<br/>");
        return `<b>${cat}</b> · ${fmt.format(n[cat] ?? 0)} casos<br/>${linhas}`;
      },
    },
    legend: {
      top: 0, icon: "circle", itemWidth: 9, itemHeight: 9,
      textStyle: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
    },
    grid: { left: 8, right: 16, top: 34, bottom: 4, containLabel: true },
    xAxis: horizontal ? valAxis : catAxis,
    yAxis: horizontal ? { ...catAxis, data: categorias.slice().reverse() } : valAxis,
    series: grupos.map((g) => ({
      name: g,
      type: "bar",
      stack: "total",
      barMaxWidth: 42,
      itemStyle: { borderColor: C.bg, borderWidth: 1 },
      data: (horizontal ? categorias.slice().reverse() : categorias).map((c) => pct[c]?.[g] ?? 0),
    })),
  };
}

/** Pirâmide etária (barras espelhadas M/F). */
export function piramide(p: Piramide, opts: { destaqueMenor15?: boolean } = {}) {
  const destaque = opts.destaqueMenor15 ?? true;
  const jovem = (fx: string) => ["0-4", "5-9", "10-14"].includes(fx);
  const corM = (fx: string) => (destaque && jovem(fx) ? "#ffa657" : "#58a6ff");
  const corF = (fx: string) => (destaque && jovem(fx) ? "#f0883e" : "#f778ba");
  const maxVal = Math.max(...p.masculino, ...p.feminino, 1);
  return {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (ps: any[]) => {
        const fx = ps[0]?.name;
        const linhas = ps
          .map((s) => `${s.marker} ${s.seriesName}: <b>${fmt.format(Math.abs(s.value))}</b>`)
          .join("<br/>");
        return `<b>${fx} anos</b><br/>${linhas}`;
      },
    },
    legend: {
      top: 0,
      icon: "circle", itemWidth: 9, itemHeight: 9,
      textStyle: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
      data: ["Masculino", "Feminino"],
    },
    grid: { left: 8, right: 16, top: 30, bottom: 4, containLabel: true },
    xAxis: {
      type: "value",
      min: -maxVal,
      max: maxVal,
      ...eixoX,
      axisLabel: { ...eixoX.axisLabel, formatter: (v: number) => fmt.format(Math.abs(v)) },
    },
    yAxis: { type: "category", data: p.faixas, ...eixoY },
    series: [
      {
        name: "Masculino",
        type: "bar",
        stack: "p",
        barMaxWidth: 20,
        color: "#58a6ff",
        data: p.faixas.map((fx, i) => ({
          value: -p.masculino[i],
          itemStyle: { color: corM(fx), borderRadius: [6, 0, 0, 6] },
        })),
      },
      {
        name: "Feminino",
        type: "bar",
        stack: "p",
        barMaxWidth: 20,
        color: "#f778ba",
        data: p.faixas.map((fx, i) => ({
          value: p.feminino[i],
          itemStyle: { color: corF(fx), borderRadius: [0, 6, 6, 0] },
        })),
      },
    ],
  };
}
