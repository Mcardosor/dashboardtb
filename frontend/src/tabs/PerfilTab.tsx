/**
 * PerfilTab.tsx — Perfil dos pacientes: sexo, forma clínica, entrada,
 * raça/cor, desfechos e pirâmides etárias.
 */
import { usePerfil } from "../api";
import { barH, barV, donut, piramide, stacked100 } from "../charts";
import { Chart } from "../components/Chart";
import { ChartCard, SkelCard } from "../components/ui";
import type { Filtros } from "../state";

export function PerfilTab({ filtros }: { filtros: Filtros }) {
  const { data, isLoading } = usePerfil(filtros);

  if (isLoading || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[380, 380, 380, 380].map((h, i) => <SkelCard key={i} h={h} />)}
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <ChartCard
        titulo="Por sexo"
        caption="Distribuição dos casos entre homens e mulheres. Historicamente, a TB afeta mais homens no Brasil."
      >
        <Chart option={donut(data.sexo)} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Forma clínica"
        caption="Pulmonar: TB nos pulmões — transmissível pelo ar. Extrapulmonar: TB em outros órgãos. A forma pulmonar representa maior risco de contágio."
      >
        <Chart option={donut(data.forma)} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Tipo de entrada"
        caption="Caso novo: primeiro diagnóstico. Recidiva: voltou a adoecer após cura. Reingresso: retomou após abandonar o tratamento."
      >
        <Chart option={barH(data.tipo_entrada)} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Por raça/cor"
        caption="A TB afeta desproporcionalmente populações negras e indígenas, refletindo desigualdades socioeconômicas no acesso à saúde."
      >
        <Chart option={barV(data.raca_cor)} height={300} />
      </ChartCard>

      <ChartCard
        titulo="Situação de encerramento"
        caption="Como o caso foi concluído: cura (tratamento completo), abandono (interrompeu) ou óbito. Alta taxa de cura indica programa de controle eficaz."
      >
        <Chart option={barH(data.desfecho, { gradiente: ["#2B7BB9", "#58a6ff"] })} height={340} />
      </ChartCard>

      <ChartCard
        titulo="Desfecho de tratamento — agrupado"
        caption="Quatro categorias: Cura, Interrupção (abandonos), Óbito (por TB ou outras causas) e Não avaliados (transferências, TB-DR, em acompanhamento)."
      >
        <Chart option={donut(data.desfecho_grupo)} height={340} />
      </ChartCard>

      <ChartCard
        titulo="Desfecho × raça/cor"
        caption="Composição dos desfechos dentro de cada grupo racial (cada coluna soma 100%). Diferenças refletem desigualdades no acesso e na qualidade do cuidado."
        className="md:col-span-2"
      >
        <Chart option={stacked100(data.desfecho_por_raca)} height={380} />
      </ChartCard>

      <ChartCard
        titulo="Pirâmide etária — casos de TB"
        caption="Distribuição dos casos notificados por faixa etária e sexo. 🟠 Barras em laranja = menores de 15 anos (público prioritário)."
      >
        <Chart option={piramide(data.piramide_casos)} height={400} />
      </ChartCard>

      <ChartCard
        titulo="Pirâmide etária — óbitos por TB"
        caption="Distribuição dos óbitos por TB (desfecho SINAN) por faixa etária e sexo."
      >
        <Chart option={piramide(data.piramide_obitos)} height={400} />
      </ChartCard>
    </div>
  );
}
