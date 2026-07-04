/**
 * ComorbidadesTab.tsx — Comorbidades, populações vulneráveis, desfecho por
 * grupo vulnerável e heatmap de comorbidades × UF.
 */
import { useComorbidades } from "../api";
import { Chart } from "../components/Chart";
import { ChartCard, Metrica, SkelCard } from "../components/ui";
import type { Filtros } from "../state";
import { baseOption, C, fmt, fmt1, FONT, SEQ_INTENSIDADE, tbColors } from "../theme";

export function ComorbidadesTab({ filtros }: { filtros: Filtros }) {
  const { data, isLoading } = useComorbidades(filtros);

  if (isLoading || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[380, 380, 420, 420].map((h, i) => <SkelCard key={i} h={h} />)}
      </div>
    );
  }

  // Barras horizontais com % sobre o total
  const opcaoAgravos = {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      formatter: (p: any) => {
        const a = data.agravos[data.agravos.length - 1 - p.dataIndex];
        return `<b>${a.label}</b><br/>${fmt.format(a.valor)} casos · ${fmt1.format(a.pct ?? 0)}% do total`;
      },
    },
    grid: { left: 8, right: 84, top: 6, bottom: 6, containLabel: true },
    xAxis: { type: "value", axisLabel: { color: C.faint, fontSize: 10.5 }, splitLine: { lineStyle: { color: C.border } } },
    yAxis: {
      type: "category",
      data: data.agravos.slice().reverse().map((a) => a.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: C.muted, fontSize: 12, fontFamily: FONT },
    },
    series: [{
      type: "bar",
      barMaxWidth: 24,
      data: data.agravos.slice().reverse().map((a) => a.valor),
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: {
          type: "linear", x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [{ offset: 0, color: "#7b3aed" }, { offset: 1, color: "#a371f7" }],
        },
      },
      label: {
        show: true, position: "right", color: C.muted, fontSize: 11, fontFamily: FONT,
        formatter: (p: any) => {
          const a = data.agravos[data.agravos.length - 1 - p.dataIndex];
          return `${fmt.format(p.value)}  (${fmt1.format(a.pct ?? 0)}%)`;
        },
      },
    }],
  };

  // Desfecho × vulnerável (stacked 100%)
  const dv = data.desfecho_por_vulneravel;
  const cores = tbColors(dv.grupos);
  const opcaoDesfVuln = {
    ...baseOption,
    color: cores,
    tooltip: {
      ...baseOption.tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (ps: any[]) => {
        const linha = dv.linhas.find((l) => l.categoria === ps[0]?.name);
        const corpo = ps.map((p) => `${p.marker} ${p.seriesName}: <b>${fmt1.format(p.value)}%</b>`).join("<br/>");
        return `<b>${ps[0]?.name}</b> · ${fmt.format(linha?.n ?? 0)} casos<br/>${corpo}`;
      },
    },
    legend: {
      top: 0, icon: "circle", itemWidth: 9, itemHeight: 9,
      textStyle: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
    },
    grid: { left: 8, right: 16, top: 34, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: dv.linhas.map((l) => l.categoria),
      axisLabel: { color: C.muted, fontSize: 11, interval: 0, fontFamily: FONT },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: C.border } },
    },
    yAxis: {
      type: "value", max: 100,
      axisLabel: { color: C.faint, fontSize: 10.5, formatter: "{value}%" },
      splitLine: { lineStyle: { color: C.border } },
    },
    series: dv.grupos.map((g) => ({
      name: g,
      type: "bar",
      stack: "total",
      barMaxWidth: 46,
      itemStyle: { borderColor: C.bg, borderWidth: 1 },
      data: dv.linhas.map((l) => l.pct[g] ?? 0),
    })),
  };

  // Heatmap comorbidade × UF
  const hm = data.heatmap_uf;
  const maxHeat = Math.max(...hm.valores.map((v) => v[2]), 1);
  const opcaoHeatmap = {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      position: "top",
      formatter: (p: any) =>
        `<b>${hm.ufs[p.value[0]]}</b> · ${hm.agravos[p.value[1]]}<br/><b>${fmt1.format(p.value[2])}%</b> dos casos do estado`,
    },
    grid: { left: 8, right: 16, top: 8, bottom: 40, containLabel: true },
    xAxis: {
      type: "category",
      data: hm.ufs,
      axisLabel: { color: C.muted, fontSize: 10.5, interval: 0, fontFamily: FONT },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: C.border } },
      splitArea: { show: false },
    },
    yAxis: {
      type: "category",
      data: hm.agravos,
      axisLabel: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
      axisTick: { show: false },
      axisLine: { show: false },
    },
    visualMap: {
      type: "continuous",
      min: 0,
      max: maxHeat,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      itemWidth: 12,
      itemHeight: 130,
      inRange: { color: SEQ_INTENSIDADE },
      textStyle: { color: C.faint, fontSize: 10, fontFamily: FONT },
      formatter: (v: number) => `${fmt1.format(v)}%`,
    },
    series: [{
      type: "heatmap",
      data: hm.valores,
      itemStyle: { borderColor: C.bg, borderWidth: 2, borderRadius: 4 },
      emphasis: { itemStyle: { shadowBlur: 12, shadowColor: "rgba(0,0,0,.5)" } },
    }],
  };

  return (
    <div className="grid gap-4 md:grid-cols-5">
      <ChartCard
        titulo="Comorbidades associadas"
        caption="Condições presentes junto com a TB. Diabéticos têm risco 3× maior de desenvolver a doença; o percentual é sobre o total filtrado."
        className="md:col-span-3"
      >
        <Chart option={opcaoAgravos} height={340} />
      </ChartCard>

      <ChartCard
        titulo="Populações vulneráveis"
        caption="Pessoas em situação de rua têm risco até 56× maior; privados de liberdade, até 28× maior que a população geral."
        className="md:col-span-2"
      >
        <div className="grid gap-2.5">
          {data.populacoes.map((p) => (
            <Metrica
              key={p.coluna}
              rotulo={p.label}
              valor={fmt.format(p.valor)}
              detalhe={`${fmt1.format(p.pct ?? 0)}% do total`}
            />
          ))}
        </div>
      </ChartCard>

      <ChartCard
        titulo="Desfecho de tratamento × populações vulneráveis"
        caption="Como o tratamento termina em cada grupo (cada coluna soma 100%). Situação de rua e privação de liberdade tendem a ter mais interrupção."
        className="md:col-span-5"
      >
        <Chart option={opcaoDesfVuln} height={380} />
      </ChartCard>

      <ChartCard
        titulo="Comorbidades por estado"
        caption="Proporção de casos com cada comorbidade em cada estado (% sobre o total do estado). Células mais quentes = maior concentração."
        className="md:col-span-5"
      >
        <Chart option={opcaoHeatmap} height={330} />
      </ChartCard>
    </div>
  );
}
