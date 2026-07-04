/**
 * ClinicoTab.tsx — Clínico & diagnóstico: HIV, baciloscopia, TMR-TB,
 * desfecho × HIV, coinfecção por UF e oportunidade do tratamento.
 */
import { useClinico } from "../api";
import { donut, stacked100 } from "../charts";
import { Chart } from "../components/Chart";
import { ChartCard, Metrica, SkelCard } from "../components/ui";
import type { Filtros } from "../state";
import { baseOption, C, fmt, fmt1, FONT } from "../theme";

export function ClinicoTab({ filtros }: { filtros: Filtros }) {
  const { data, isLoading } = useClinico(filtros);

  if (isLoading || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[340, 340, 380, 380].map((h, i) => <SkelCard key={i} h={h} />)}
      </div>
    );
  }

  const tt = data.tempo_tratamento;
  const dias = (n: number) => `${fmt.format(n)} ${n === 1 ? "dia" : "dias"}`;

  const opcaoCoinfeccao = {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      formatter: (p: any) => {
        const e = data.coinfeccao_uf[p.dataIndex];
        return `<b>${e.nome}</b><br/>HIV+: <b>${fmt1.format(e.pct)}%</b><br/>${fmt.format(e.n_testado)} testados`;
      },
    },
    grid: { left: 8, right: 12, top: 26, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: data.coinfeccao_uf.map((e) => e.uf),
      axisLabel: { color: C.muted, fontSize: 10.5, interval: 0, fontFamily: FONT },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: C.border } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: C.faint, fontSize: 10.5, formatter: "{value}%" },
      splitLine: { lineStyle: { color: C.border } },
    },
    visualMap: {
      show: false,
      type: "continuous",
      min: 0,
      max: Math.max(...data.coinfeccao_uf.map((e) => e.pct), 1),
      inRange: { color: ["#2B7BB9", "#a371f7", "#da3633"] },
      dimension: 1,
    },
    series: [{
      type: "bar",
      barMaxWidth: 26,
      data: data.coinfeccao_uf.map((e) => e.pct),
      itemStyle: { borderRadius: [5, 5, 0, 0] },
      label: {
        show: true, position: "top", color: C.faint, fontSize: 9.5, fontFamily: FONT,
        formatter: (p: any) => fmt1.format(p.value),
      },
    }],
  };

  const opcaoHistograma = tt && {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      formatter: (p: any) => `<b>${p.name}</b><br/>${fmt.format(p.value)} casos`,
    },
    grid: { left: 8, right: 12, top: 26, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: tt.histograma.map((h) => h.faixa),
      axisLabel: { color: C.muted, fontSize: 11, interval: 0, fontFamily: FONT },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: C.border } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: C.faint, fontSize: 10.5 },
      splitLine: { lineStyle: { color: C.border } },
    },
    series: [{
      type: "bar",
      barMaxWidth: 52,
      data: tt.histograma.map((h, i) => ({
        value: h.casos,
        itemStyle: {
          color: i <= 2 ? "#3fb950" : i <= 4 ? "#d29922" : "#f85149",
          borderRadius: [6, 6, 0, 0],
        },
      })),
      label: {
        show: true, position: "top", color: C.muted, fontSize: 10.5, fontFamily: FONT,
        formatter: (p: any) => fmt.format(p.value),
      },
    }],
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <ChartCard
        titulo="Status HIV"
        caption="Pacientes com HIV têm imunidade reduzida, tornando a TB mais grave e difícil de tratar."
      >
        <Chart option={donut(data.status_hiv)} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Baciloscopia — 1ª amostra"
        caption="Exame de escarro que detecta a bactéria. Positivo = caso confirmado e transmissível."
      >
        <Chart option={donut(data.baciloscopia)} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Teste Molecular Rápido (TMR-TB)"
        caption="Detecta a TB e a resistência à rifampicina em poucas horas — mais preciso que a baciloscopia."
      >
        <Chart option={donut(data.teste_molecular, { max: 6 })} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Desfecho do tratamento por status HIV"
        caption="Cada coluna soma 100%. Pacientes HIV+ tendem a ter menor taxa de cura e maior risco de óbito."
        className="md:col-span-2 xl:col-span-1"
      >
        <Chart option={stacked100(data.desfecho_por_hiv)} height={360} />
      </ChartCard>

      <ChartCard
        titulo="Coinfecção TB-HIV por estado"
        caption="De cada 100 pacientes testados para HIV no estado, quantos têm resultado positivo (proporção, não quantidade)."
        className="md:col-span-2"
      >
        <Chart option={opcaoCoinfeccao} height={360} />
      </ChartCard>

      <ChartCard
        titulo="⏱️ Oportunidade do tratamento"
        caption="Tempo entre o diagnóstico e o início do tratamento. Início precoce (≤7 dias) interrompe a cadeia de transmissão."
        className="md:col-span-2 xl:col-span-3"
      >
        {tt ? (
          <>
            <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Metrica
                rotulo="Início do tratamento (mediana)"
                valor={dias(Math.round(tt.mediana_inicio))}
                detalhe={`${fmt.format(tt.n)} casos com datas válidas`}
              />
              <Metrica
                rotulo="Início em ≤7 dias"
                valor={`${fmt1.format(tt.pct_ate_7d)}%`}
                detalhe="início oportuno"
                cor="#3fb950"
              />
              <Metrica
                rotulo="Início tardio (>30 dias)"
                valor={`${fmt1.format(tt.pct_acima_30d)}%`}
                detalhe="atraso preocupante"
                cor="#f85149"
              />
              <Metrica
                rotulo="Duração do tratamento (mediana)"
                valor={tt.duracao_mediana !== null ? dias(Math.round(tt.duracao_mediana)) : "—"}
                detalhe="esquema básico ≈180 dias"
              />
            </div>
            {opcaoHistograma && <Chart option={opcaoHistograma} height={300} />}
          </>
        ) : (
          <p className="py-10 text-center text-sm text-muted">
            Dados de datas insuficientes para calcular o tempo de tratamento.
          </p>
        )}
      </ChartCard>

    </div>
  );
}
