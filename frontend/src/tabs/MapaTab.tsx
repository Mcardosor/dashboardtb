/**
 * MapaTab.tsx — Choropleth do Brasil (ECharts + GeoJSON local) com
 * drill-down por estado e ranking lateral.
 */
import { useEffect, useMemo, useState } from "react";
import { useGeoJson, useMapa, type EstadoMapa } from "../api";
import { Chart } from "../components/Chart";
import { ChartCard, Skel, SkelCard } from "../components/ui";
import { UfModal } from "../components/UfModal";
import { baseOption, C, echarts, fmt, fmt1, FONT, SEQ_CASOS, SEQ_MORTALIDADE } from "../theme";
import type { Filtros } from "../state";

export type MetricaMapa = "casos" | "incidencia" | "mortalidade";

// Função (não objeto de módulo) porque SEQ_CASOS/SEQ_MORTALIDADE mudam com o
// tema — um objeto de módulo congelaria a paleta na primeira importação.
function metricas(): Record<MetricaMapa, { rotulo: string; escala: string[]; formatar: (v: number) => string }> {
  return {
    casos: { rotulo: "Total de casos", escala: SEQ_CASOS, formatar: (v) => fmt.format(v) },
    incidencia: { rotulo: "Incidência por 100 mil hab.", escala: SEQ_CASOS, formatar: (v) => fmt1.format(v) },
    mortalidade: { rotulo: "Mortalidade por 100 mil hab.", escala: SEQ_MORTALIDADE, formatar: (v) => fmt1.format(v) },
  };
}

export function MapaTab({
  filtros,
  metrica,
  setMetrica,
}: {
  filtros: Filtros;
  metrica: MetricaMapa;
  setMetrica: (m: MetricaMapa) => void;
}) {
  const { data: mapa, isLoading } = useMapa(filtros);
  const { data: geo } = useGeoJson("/api/geojson/estados");
  const [mapaPronto, setMapaPronto] = useState(false);
  const [ufAberta, setUfAberta] = useState<string | null>(null);

  useEffect(() => {
    if (geo) {
      echarts.registerMap("BR", geo as never);
      setMapaPronto(true);
    }
  }, [geo]);

  const cfg = metricas()[metrica];
  const porUf = useMemo(() => {
    const d: Record<string, EstadoMapa> = {};
    mapa?.estados.forEach((e) => (d[e.uf] = e));
    return d;
  }, [mapa]);

  const opcaoMapa = useMemo(() => {
    if (!mapa) return null;
    const valores = mapa.estados.map((e) => e[metrica]);
    const maxReal = Math.max(...valores, 1);
    // "Casos" é uma contagem absoluta muito assimétrica (SP concentra boa
    // parte do total) — raiz quadrada espalha a escala de cor melhor do que
    // linear. Taxas (incidência/mortalidade) já são normalizadas, ficam lineares.
    const transformar = metrica === "casos" ? Math.sqrt : (v: number) => v;
    const max = transformar(maxReal);
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => {
          const e = porUf[p.name];
          if (!e) return `<b>${p.name}</b><br/>sem dados`;
          return (
            `<b>${e.nome} (${e.uf})</b><br/>` +
            `Casos: <b>${fmt.format(e.casos)}</b><br/>` +
            `Incidência: <b>${fmt1.format(e.incidencia)}</b> /100 mil<br/>` +
            `Mortalidade: <b>${fmt1.format(e.mortalidade)}</b> /100 mil<br/>` +
            `Cura: <b>${fmt1.format(e.cura_pct)}%</b> · Abandono: <b>${fmt1.format(e.abandono_pct)}%</b><br/>` +
            `<span style="color:${C.muted};font-size:11px">clique para ver municípios</span>`
          );
        },
      },
      visualMap: {
        type: "continuous",
        min: 0,
        max,
        inRange: { color: cfg.escala },
        left: 8,
        bottom: 8,
        calculable: false,
        itemHeight: 110,
        text: [cfg.formatar(maxReal), "0"],
        textStyle: { color: C.muted, fontSize: 10.5, fontFamily: FONT },
      },
      series: [{
        type: "map",
        map: "BR",
        nameProperty: "uf",
        roam: false,
        selectedMode: false,
        aspectScale: 0.95,
        layoutCenter: ["50%", "50%"],
        layoutSize: "108%",
        itemStyle: { areaColor: C.card, borderColor: C.borderlight, borderWidth: 0.7 },
        emphasis: {
          label: {
            show: true, color: C.text, fontWeight: 700, fontFamily: FONT,
            textBorderColor: C.card, textBorderWidth: 3,
          },
          itemStyle: {
            areaColor: null as never,
            borderColor: "#79c0ff",
            borderWidth: 1.6,
            shadowBlur: 16,
            shadowColor: "rgba(88,166,255,.35)",
          },
        },
        label: { show: false },
        data: mapa.estados.map((e) => ({ name: e.uf, value: transformar(e[metrica]) })),
      }],
    };
  }, [mapa, metrica, cfg, porUf]);

  const opcaoRanking = useMemo(() => {
    if (!mapa) return null;
    const ordenado = mapa.estados.slice().sort((a, b) => a[metrica] - b[metrica]);
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => {
          const e = porUf[p.name];
          return e
            ? `<b>${e.nome}</b><br/>${cfg.rotulo}: <b>${cfg.formatar(e[metrica])}</b>`
            : p.name;
        },
      },
      grid: { left: 8, right: 54, top: 4, bottom: 4, containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: C.faint, fontSize: 10.5 },
        splitLine: { lineStyle: { color: C.border } },
      },
      yAxis: {
        type: "category",
        data: ordenado.map((e) => e.uf),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: C.muted, fontSize: 11, fontFamily: FONT },
      },
      visualMap: {
        show: false,
        type: "continuous",
        min: 0,
        max: Math.max(...mapa.estados.map((e) => e[metrica]), 1),
        inRange: { color: cfg.escala },
        dimension: 0,
      },
      series: [{
        type: "bar",
        barWidth: "62%",
        data: ordenado.map((e) => e[metrica]),
        itemStyle: { borderRadius: [0, 5, 5, 0] },
        label: {
          show: true,
          position: "right",
          color: C.muted,
          fontSize: 10.5,
          fontFamily: FONT,
          formatter: (p: any) => cfg.formatar(p.value),
        },
      }],
    };
  }, [mapa, metrica, cfg, porUf]);

  if (isLoading || !mapaPronto || !opcaoMapa) {
    return (
      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <SkelCard h={600} />
        <SkelCard h={600} />
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <ChartCard
          titulo={`${cfg.rotulo} — Brasil`}
          caption="💡 Clique num estado para explorar os municípios."
          acoes={
            <div className="flex gap-1 rounded-xl border border-border bg-surface p-1">
              {(Object.keys(metricas()) as MetricaMapa[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMetrica(m)}
                  className={`rounded-lg px-2.5 py-1 text-[11.5px] font-semibold transition ${
                    metrica === m ? "bg-accent/20 text-accent" : "text-faint hover:text-muted"
                  }`}
                >
                  {m === "casos" ? "Casos" : m === "incidencia" ? "Incidência" : "Mortalidade"}
                </button>
              ))}
            </div>
          }
        >
          <Chart option={opcaoMapa} height={620} onClick={(p) => p?.name && setUfAberta(p.name)} />
          {mapa && (
            <p className="mt-1 text-right text-[10.5px] text-faint">
              Óbitos/mortalidade: fonte {mapa.fonte_obitos === "SIM" ? "SIM (oficial)" : "SINAN (desfecho)"}
            </p>
          )}
        </ChartCard>

        <ChartCard
          titulo={`${cfg.rotulo} por estado`}
          caption={
            metrica === "incidencia"
              ? "📌 Por 100 mil hab. — permite comparar estados de tamanhos diferentes."
              : metrica === "mortalidade"
                ? "📌 Estados com valor mais alto pedem atenção prioritária."
                : "📌 Total absoluto de casos notificados no estado."
          }
        >
          {opcaoRanking ? (
            <Chart option={opcaoRanking} height={620} onClick={(p) => p?.name && setUfAberta(p.name)} />
          ) : (
            <Skel h={620} />
          )}
        </ChartCard>
      </div>

      {ufAberta && <UfModal uf={ufAberta} filtros={filtros} aoFechar={() => setUfAberta(null)} />}
    </>
  );
}
