/**
 * DadosTab.tsx — Download dos dados filtrados em CSV + dicionário resumido.
 * Substitui a "Análise Livre" (PyGWalker) do dashboard Streamlit: o CSV sai
 * pronto para Excel, R, Python ou qualquer ferramenta de análise.
 */
import { filtrosQuery, type Resumo } from "../api";
import { ChartCard } from "../components/ui";
import type { Filtros } from "../state";
import { fmt } from "../theme";

const COLUNAS = [
  ["estado_notificacao / municipio_notificacao", "Local da notificação"],
  ["ano_notificacao / data_notificacao", "Quando o caso foi notificado"],
  ["data_diagnostico / data_inicio_tratamento / data_encerramento", "Linha do tempo clínica"],
  ["idade_anos / sexo / raca_cor / escolaridade", "Perfil demográfico"],
  ["tipo_entrada / forma / situacao_encerramento", "Classificação e desfecho"],
  ["status_hiv / baciloscopia / cultura / teste_molecular", "Exames e diagnóstico"],
  ["agravo_*", "Comorbidades (AIDS, alcoolismo, diabetes...)"],
  ["populacao_* / profissional_saude / beneficiario_governo", "Populações vulneráveis"],
  ["numero_contatos / numero_contatos_examinados", "Vigilância de contatos"],
];

export function DadosTab({ filtros, resumo }: { filtros: Filtros; resumo: Resumo | undefined }) {
  const urlCsv = `/api/export.csv?${filtrosQuery(filtros)}`;
  const bloqueado = filtros.anos.length > 5;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard
        titulo="🔬 Exportar dados filtrados"
        caption="Baixe os microdados exatamente como estão filtrados na sidebar — prontos para Excel, R, Python ou a ferramenta que preferir."
      >
        <div className="grid place-items-center gap-4 py-8 text-center">
          <div className="text-5xl">🧪</div>
          <div>
            <div className="text-lg font-bold">
              {resumo ? `${fmt.format(resumo.total)} registros` : "…"}
            </div>
            <div className="text-[12.5px] text-muted">
              {filtros.anos.length === 1
                ? `ano ${filtros.anos[0]}`
                : `anos ${Math.min(...filtros.anos)}–${Math.max(...filtros.anos)}`}{" "}
              · filtros da sidebar aplicados · 37 variáveis
            </div>
          </div>
          {bloqueado ? (
            <p className="max-w-xs text-[12.5px] text-yellow">
              ⚡ Export limitado a 5 anos por vez — reduza a seleção de anos para baixar.
            </p>
          ) : (
            <a
              href={urlCsv}
              download
              className="rounded-xl bg-gradient-to-r from-[#79c0ff] to-[#58a6ff] px-6 py-3 text-[14px] font-bold text-[#0a0e14] shadow-lg shadow-accent/25 transition hover:brightness-110"
            >
              ⬇️ Baixar CSV
            </a>
          )}
          <p className="text-[11px] text-faint">Streaming direto do DuckDB — sem limite de memória.</p>
        </div>
      </ChartCard>

      <ChartCard
        titulo="📖 O que vem no arquivo"
        caption="Principais grupos de variáveis do SINAN NET (dicionário v5.0) incluídos no export."
      >
        <div className="overflow-hidden rounded-xl border border-border">
          <table className="tbl w-full">
            <thead>
              <tr><th>Colunas</th><th>Conteúdo</th></tr>
            </thead>
            <tbody>
              {COLUNAS.map(([col, desc]) => (
                <tr key={col}>
                  <td className="font-mono text-[11.5px] text-accent">{col}</td>
                  <td className="text-muted">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
  );
}
