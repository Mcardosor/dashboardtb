/**
 * KpiCards.tsx — Grade de 8 KPIs. Incidência, mortalidade e total são
 * clicáveis e trocam a métrica exibida no mapa.
 */
import type { Resumo } from "../api";
import type { MetricaMapa } from "../tabs/MapaTab";
import { fmt, fmt1 } from "../theme";
import { CountUp } from "./ui";

interface CardDef {
  chave: string;
  titulo: string;
  valor: (r: Resumo) => number;
  formatar: (v: number) => string;
  icone: string;
  cor: string;
  metrica?: MetricaMapa;
  nota?: (r: Resumo) => string | undefined;
}

const CARDS: CardDef[] = [
  {
    chave: "incidencia", titulo: "Incidência por 100 mil hab.",
    valor: (r) => r.incidencia, formatar: (v) => fmt1.format(v),
    icone: "📈", cor: "#58a6ff", metrica: "incidencia",
    nota: () => "casos novos / população",
  },
  {
    chave: "mortalidade", titulo: "Mortalidade por 100 mil hab.",
    valor: (r) => r.mortalidade, formatar: (v) => fmt1.format(v),
    icone: "💀", cor: "#f85149", metrica: "mortalidade",
    nota: (r) => (r.fonte_obitos === "SIM" ? "fonte oficial: SIM" : "fonte: desfecho SINAN"),
  },
  {
    chave: "obitos", titulo: "Óbitos por TB",
    valor: (r) => r.obitos, formatar: (v) => fmt.format(Math.round(v)),
    icone: "⚠️", cor: "#ffd700",
    nota: (r) => (r.fonte_obitos === "SIM" ? "SIM · CID A15–A19" : "desfecho SINAN"),
  },
  {
    chave: "hiv", titulo: "Coinfecção HIV",
    valor: (r) => r.hiv_pos, formatar: (v) => fmt.format(Math.round(v)),
    icone: "🔬", cor: "#d2a8ff",
    nota: () => "testes positivos",
  },
  {
    chave: "cura", titulo: "Curas registradas",
    valor: (r) => r.cura, formatar: (v) => fmt.format(Math.round(v)),
    icone: "✅", cor: "#7ee787",
    nota: (r) => `${fmt1.format((r.cura / Math.max(r.total, 1)) * 100)}% dos casos`,
  },
  {
    chave: "abandono", titulo: "Abandonos",
    valor: (r) => r.abandono, formatar: (v) => fmt.format(Math.round(v)),
    icone: "🚪", cor: "#d29922",
    nota: (r) => `${fmt1.format((r.abandono / Math.max(r.total, 1)) * 100)}% dos casos`,
  },
  {
    chave: "total", titulo: "Total de casos",
    valor: (r) => r.total, formatar: (v) => fmt.format(Math.round(v)),
    icone: "🦠", cor: "#ffa657", metrica: "casos",
    nota: (r) => `${r.pct_filtrado}% da base`,
  },
  {
    chave: "municipios", titulo: "Municípios com casos",
    valor: (r) => r.municipios, formatar: (v) => fmt.format(Math.round(v)),
    icone: "🏙️", cor: "#79c0ff",
    nota: () => "com ≥1 notificação",
  },
];

export function KpiCards({
  resumo,
  metricaMapa,
  aoEscolherMetrica,
}: {
  resumo: Resumo | undefined;
  metricaMapa: MetricaMapa;
  aoEscolherMetrica: (m: MetricaMapa) => void;
}) {
  if (!resumo) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {CARDS.map((c) => (
          <div key={c.chave} className="skeleton h-[104px]" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {CARDS.map((c, i) => {
        const clicavel = !!c.metrica;
        const selecionado = clicavel && metricaMapa === c.metrica;
        return (
          <button
            key={c.chave}
            type="button"
            disabled={!clicavel}
            onClick={() => c.metrica && aoEscolherMetrica(c.metrica)}
            className={`card card-hover kpi rise text-left ${clicavel ? "kpi-clickable" : ""} ${selecionado ? "kpi-selected" : ""}`}
            style={{ "--kpi-accent": c.cor, animationDelay: `${i * 40}ms` } as React.CSSProperties}
            title={clicavel ? "Clique para ver no mapa" : undefined}
          >
            <div className="kpi-icon">{c.icone}</div>
            <div className="pr-12 text-[11px] font-semibold uppercase tracking-wider text-faint">
              {c.titulo}
            </div>
            <div className="mt-1 text-[26px] font-bold leading-none tracking-tight text-ink">
              <CountUp valor={c.valor(resumo)} formatar={c.formatar} />
            </div>
            <div className="mt-1.5 flex items-center gap-2 text-[11px] text-muted">
              {c.nota?.(resumo)}
              {selecionado && <span className="badge badge-accent !px-2 !py-0.5 !text-[10px]">🗺️ no mapa</span>}
            </div>
          </button>
        );
      })}
    </div>
  );
}
