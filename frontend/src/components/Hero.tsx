/**
 * Hero.tsx — Cabeçalho do painel: título, subtítulo e badges de contexto.
 */
import type { Resumo } from "../api";
import { fmt } from "../theme";

export function Hero({
  anos,
  anoParcial,
  resumo,
}: {
  anos: number[];
  anoParcial: number | null;
  resumo: Resumo | undefined;
}) {
  const labelAnos =
    anos.length === 0
      ? "—"
      : anos.length > 1
        ? `Anos ${Math.min(...anos)}–${Math.max(...anos)}`
        : `Ano ${anos[0]}`;
  const parcial = anoParcial !== null && anos.includes(anoParcial);

  return (
    <header className="rise relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-[#101826] via-[#0e1520] to-[#101423] px-7 py-8 md:px-9">
      <div
        className="pointer-events-none absolute -right-24 -top-32 h-80 w-80 rounded-full opacity-25"
        style={{ background: "radial-gradient(circle, rgba(88,166,255,.5), transparent 65%)" }}
      />
      <div
        className="pointer-events-none absolute -bottom-40 left-1/3 h-72 w-72 rounded-full opacity-15"
        style={{ background: "radial-gradient(circle, rgba(163,113,247,.55), transparent 65%)" }}
      />

      <h1 className="flex items-center gap-3 text-[26px] font-extrabold tracking-tight md:text-[32px]">
        <span className="grid h-12 w-12 place-items-center rounded-2xl border border-accent/25 bg-accent/10 text-[24px]">
          🩺
        </span>
        Tuberculose no Brasil
      </h1>
      <p className="mt-2.5 max-w-3xl text-[13.5px] leading-relaxed text-muted md:text-sm">
        Painel de vigilância epidemiológica baseado em notificações do SINAN — perfil dos casos,
        indicadores clínicos, distribuição geográfica e tendências temporais (2001–2026).
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <span className="badge badge-accent"><span className="dot pulse" />{labelAnos}</span>
        {parcial && (
          <span className="badge badge-red"><span className="dot pulse" />{anoParcial} · dados parciais</span>
        )}
        <span className="badge"><span className="dot" />SINAN NET · Dicionário v5.0</span>
        {resumo && (
          <span className="badge badge-green">
            <span className="dot" />
            {fmt.format(resumo.total)} registros ({resumo.pct_filtrado}% da base)
          </span>
        )}
        <span className="badge"><span className="dot" />Série histórica: 2001–2026</span>
      </div>
    </header>
  );
}
