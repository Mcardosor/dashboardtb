/**
 * TendenciaTab.tsx — Série histórica 2001–2026: mensal vs média histórica,
 * evolução anual, óbitos SIM, variação por estado e indicadores clínicos.
 */
import { useMemo, useState } from "react";
import { useTendencia } from "../api";
import { Chart } from "../components/Chart";
import { ChartCard, Metrica, SkelCard } from "../components/ui";
import type { Filtros } from "../state";
import { baseOption, C, fmt, fmt1, FONT } from "../theme";

const CORES_IND = ["#3fb950", "#d29922", "#a371f7", "#58a6ff", "#f778ba", "#ffa657", "#f85149", "#79c0ff", "#d2a8ff"];

export function TendenciaTab({ filtros }: { filtros: Filtros }) {
  const { data, isLoading } = useTendencia(filtros);
  const [indicadoresSel, setIndicadoresSel] = useState<string[]>([
    "Coinfecção HIV (%)", "Taxa de cura (%)", "Taxa de abandono (%)",
  ]);

  const opcaoMensal = useMemo(() => {
    if (!data) return null;
    return {
      ...baseOption,
      tooltip: { ...baseOption.tooltip, trigger: "axis", axisPointer: { type: "shadow" } },
      legend: {
        top: 0, icon: "circle", itemWidth: 9, itemHeight: 9,
        textStyle: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
      },
      grid: { left: 8, right: 16, top: 34, bottom: 4, containLabel: true },
      xAxis: {
        type: "category",
        data: data.mensal.meses,
        axisLabel: { color: C.muted, fontSize: 11, fontFamily: FONT },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: C.border } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: C.faint, fontSize: 10.5 },
        splitLine: { lineStyle: { color: "#141c28" } },
      },
      series: [
        {
          name: `Casos ${data.ano}`,
          type: "bar",
          barMaxWidth: 34,
          data: data.mensal.casos,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: {
              type: "linear", x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: "#ffa657" }, { offset: 1, color: "#d29922" }],
            },
          },
        },
        {
          name: "Média histórica mensal",
          type: "line",
          data: data.mensal.media_hist,
          symbol: "circle",
          symbolSize: 6,
          lineStyle: { type: "dashed", color: "#58a6ff", width: 2 },
          itemStyle: { color: "#58a6ff" },
        },
      ],
    };
  }, [data]);

  const opcaoAnual = useMemo(() => {
    if (!data || !data.anual.length) return null;
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => `<b>${p.name}</b><br/>${fmt.format(p.value)} casos`,
      },
      grid: { left: 8, right: 16, top: 12, bottom: 4, containLabel: true },
      xAxis: {
        type: "category",
        data: data.anual.map((a) => a.ano),
        axisLabel: { color: C.muted, fontSize: 10.5, fontFamily: FONT },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: C.border } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: C.faint, fontSize: 10.5, formatter: (v: number) => `${Math.round(v / 1000)}k` },
        splitLine: { lineStyle: { color: "#141c28" } },
      },
      series: [{
        type: "bar",
        barMaxWidth: 26,
        data: data.anual.map((a) => ({
          value: a.casos,
          itemStyle: {
            color: a.ano === data.ano ? "#f85149" : "#2B7BB9",
            borderRadius: [5, 5, 0, 0],
          },
        })),
      }],
    };
  }, [data]);

  const opcaoObitos = useMemo(() => {
    if (!data?.obitos_anual?.length) return null;
    const anoDestaque = data.obitos_anual.some((o) => o.ano === data.ano)
      ? data.ano
      : Math.max(...data.obitos_anual.map((o) => o.ano));
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => `<b>${p.name}</b><br/>${fmt.format(p.value)} óbitos`,
      },
      grid: { left: 8, right: 16, top: 12, bottom: 4, containLabel: true },
      xAxis: {
        type: "category",
        data: data.obitos_anual.map((o) => o.ano),
        axisLabel: { color: C.muted, fontSize: 10.5, fontFamily: FONT },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: C.border } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: C.faint, fontSize: 10.5 },
        splitLine: { lineStyle: { color: "#141c28" } },
      },
      series: [{
        type: "bar",
        barMaxWidth: 26,
        data: data.obitos_anual.map((o) => ({
          value: o.obitos,
          itemStyle: {
            color: o.ano === anoDestaque ? "#f85149" : "#8957e5",
            borderRadius: [5, 5, 0, 0],
          },
        })),
      }],
    };
  }, [data]);

  const opcaoEstadual = useMemo(() => {
    if (!data?.estadual.length) return null;
    const ordenado = data.estadual.slice().sort((a, b) => a.variacao_pct - b.variacao_pct);
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => {
          const e = ordenado[p.dataIndex];
          return (
            `<b>${e.nome}</b><br/>` +
            `Variação: <b>${e.variacao_pct > 0 ? "+" : ""}${fmt1.format(e.variacao_pct)}%</b><br/>` +
            `${data.ano}: ${fmt.format(e.casos)} casos · média hist.: ${fmt.format(e.media_hist)}`
          );
        },
      },
      grid: { left: 8, right: 56, top: 4, bottom: 4, containLabel: true },
      xAxis: {
        type: "value",
        axisLabel: { color: C.faint, fontSize: 10.5, formatter: "{value}%" },
        splitLine: { lineStyle: { color: "#141c28" } },
      },
      yAxis: {
        type: "category",
        data: ordenado.map((e) => e.uf),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: C.muted, fontSize: 10.5, fontFamily: FONT },
      },
      series: [{
        type: "bar",
        barWidth: "60%",
        data: ordenado.map((e) => ({
          value: e.variacao_pct,
          itemStyle: {
            color: e.variacao_pct > 5 ? "#f85149" : e.variacao_pct < -5 ? "#3fb950" : "#d29922",
            borderRadius: e.variacao_pct >= 0 ? [0, 5, 5, 0] : [5, 0, 0, 5],
          },
        })),
        label: {
          show: true, position: "right", color: C.faint, fontSize: 10, fontFamily: FONT,
          formatter: (p: any) => `${p.value > 0 ? "+" : ""}${fmt1.format(p.value)}%`,
        },
      }],
    };
  }, [data]);

  const opcaoIndicadores = useMemo(() => {
    if (!data?.indicadores) return null;
    const { anos, series } = data.indicadores;
    const visiveis = indicadoresSel.filter((s) => series[s]);
    return {
      ...baseOption,
      tooltip: { ...baseOption.tooltip, trigger: "axis" },
      legend: {
        top: 0, icon: "circle", itemWidth: 9, itemHeight: 9,
        textStyle: { color: C.muted, fontSize: 11.5, fontFamily: FONT },
      },
      grid: { left: 8, right: 16, top: 36, bottom: 4, containLabel: true },
      xAxis: {
        type: "category",
        data: anos,
        axisLabel: { color: C.muted, fontSize: 10.5, fontFamily: FONT },
        axisTick: { show: false },
        axisLine: { lineStyle: { color: C.border } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: C.faint, fontSize: 10.5, formatter: "{value}%" },
        splitLine: { lineStyle: { color: "#141c28" } },
      },
      series: visiveis.map((nome, i) => ({
        name: nome,
        type: "line",
        data: series[nome],
        smooth: true,
        symbol: "circle",
        symbolSize: 5,
        lineStyle: { width: 2.4, color: CORES_IND[i % CORES_IND.length] },
        itemStyle: { color: CORES_IND[i % CORES_IND.length] },
        markLine: nome === visiveis[0] && anos.includes(data.ano)
          ? {
              silent: true,
              symbol: "none",
              lineStyle: { color: "#f85149", type: "dashed", opacity: 0.6 },
              label: { color: "#f85149", fontSize: 10, formatter: `${data.ano}` },
              data: [{ xAxis: String(data.ano) }],
            }
          : undefined,
      })),
    };
  }, [data, indicadoresSel]);

  if (isLoading || !data) {
    return (
      <div className="grid gap-4">
        {[380, 380, 420].map((h, i) => <SkelCard key={i} h={h} />)}
      </div>
    );
  }

  const kv = data.kpis;
  const tendIcone = kv.variacao_pct === null ? "➡️" : kv.variacao_pct > 5 ? "⬆️" : kv.variacao_pct < -5 ? "⬇️" : "➡️";
  const tendLabel = kv.variacao_pct === null ? "Sem histórico" : kv.variacao_pct > 5 ? "Para mais" : kv.variacao_pct < -5 ? "Para menos" : "Estável";

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Metrica
          rotulo="Tendência vs histórico"
          valor={`${tendIcone} ${tendLabel}`}
          detalhe={kv.variacao_pct !== null ? `${kv.variacao_pct > 0 ? "+" : ""}${fmt1.format(kv.variacao_pct)}% vs 2001–${data.ano - 1}` : undefined}
          cor={kv.variacao_pct !== null && kv.variacao_pct > 5 ? "#f85149" : kv.variacao_pct !== null && kv.variacao_pct < -5 ? "#3fb950" : undefined}
        />
        <Metrica rotulo={`Total ${data.ano}`} valor={fmt.format(kv.total_ano)} detalhe="casos notificados (filtros aplicados)" />
        <Metrica rotulo="Média anual histórica" valor={fmt.format(kv.media_anual_hist)} detalhe={`casos/ano · 2001–${data.ano - 1}`} />
      </div>

      <ChartCard
        titulo={`Casos por mês — ${data.ano} vs média histórica`}
        caption={`Barras = casos mês a mês em ${data.ano} (com filtros). Linha pontilhada = média mensal esperada (2001–${data.ano - 1}, nacional). Barras acima da linha indicam meses atípicos.`}
      >
        {opcaoMensal && <Chart option={opcaoMensal} height={360} />}
      </ChartCard>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard
          titulo="Evolução anual do total de casos — 2001–2026"
          caption={`Total nacional de casos notificados por ano. A barra vermelha destaca ${data.ano}.`}
        >
          {opcaoAnual && <Chart option={opcaoAnual} height={330} />}
        </ChartCard>

        {opcaoObitos ? (
          <ChartCard
            titulo="Evolução anual de óbitos por TB (SIM)"
            caption="Óbitos por tuberculose por ano no Brasil — fonte oficial SIM (CID A15–A19)."
          >
            <Chart option={opcaoObitos} height={330} />
          </ChartCard>
        ) : (
          <ChartCard
            titulo="Evolução anual de óbitos por TB (SIM)"
            caption="Fonte oficial SIM indisponível no momento (requer acesso ao banco central)."
          >
            <p className="grid h-[330px] place-items-center text-sm text-muted">🔌 Sem conexão com o SIM</p>
          </ChartCard>
        )}
      </div>

      <ChartCard
        titulo={`Variação por estado — ${data.ano} vs média histórica`}
        caption="Quanto cada estado variou em relação à própria média histórica. 🔴 Mais casos que o habitual · 🟢 menos casos · 🟡 estável (±5%)."
      >
        {opcaoEstadual && <Chart option={opcaoEstadual} height={620} />}
      </ChartCard>

      {data.indicadores && (
        <ChartCard
          titulo="Evolução histórica de indicadores clínicos — 2001–2026"
          caption="Selecione os indicadores de interesse. A linha vertical marca o ano de referência."
        >
          <div className="mb-3 flex flex-wrap gap-1.5">
            {Object.keys(data.indicadores.series).map((nome) => (
              <button
                key={nome}
                type="button"
                className={`chip ${indicadoresSel.includes(nome) ? "on" : ""}`}
                onClick={() =>
                  setIndicadoresSel((sel) =>
                    sel.includes(nome) ? sel.filter((s) => s !== nome) : [...sel, nome],
                  )
                }
              >
                {nome}
              </button>
            ))}
          </div>
          {opcaoIndicadores && indicadoresSel.length > 0 ? (
            <Chart option={opcaoIndicadores} height={400} />
          ) : (
            <p className="grid h-[200px] place-items-center text-sm text-muted">
              Selecione ao menos um indicador acima.
            </p>
          )}
        </ChartCard>
      )}
    </div>
  );
}
