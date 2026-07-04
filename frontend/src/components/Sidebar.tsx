/**
 * Sidebar.tsx — Filtros globais do painel.
 *
 * Semântica: lista vazia = "todos" (nenhum WHERE aplicado no backend).
 * Visualmente, com a lista vazia todos os chips aparecem ativos; clicar num
 * chip ativo com a lista vazia seleciona "todos menos ele" (uncheck natural).
 */
import { useState, type ReactNode } from "react";
import type { Meta, Resumo } from "../api";
import { useFiltros, type Filtros } from "../state";
import { fmt } from "../theme";

// ── Peças ─────────────────────────────────────────────────────────────────────

function Secao({
  titulo,
  icone,
  aberta = false,
  badge,
  children,
}: {
  titulo: string;
  icone: string;
  aberta?: boolean;
  badge?: number;
  children: ReactNode;
}) {
  const [aberto, setAberto] = useState(aberta);
  return (
    <div className="border-b border-border/70 last:border-0">
      <button
        type="button"
        onClick={() => setAberto((a) => !a)}
        className="flex w-full items-center gap-2.5 px-4 py-3 text-left text-[13px] font-semibold text-ink transition hover:bg-white/[.02]"
      >
        <span className="text-[15px]">{icone}</span>
        <span className="flex-1">{titulo}</span>
        {badge !== undefined && badge > 0 && (
          <span className="grid h-[18px] min-w-[18px] place-items-center rounded-full bg-accent/20 px-1 text-[10.5px] font-bold text-accent">
            {badge}
          </span>
        )}
        <span className={`text-faint transition-transform duration-200 ${aberto ? "rotate-90" : ""}`}>›</span>
      </button>
      {aberto && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

/** Grupo de chips com semântica "vazio = todos". */
function Chips({
  opcoes,
  selecionadas,
  aoMudar,
}: {
  opcoes: string[];
  selecionadas: string[];
  aoMudar: (novas: string[]) => void;
}) {
  const vazio = selecionadas.length === 0;
  const ativa = (o: string) => vazio || selecionadas.includes(o);
  const clicar = (o: string) => {
    let novas: string[];
    if (vazio) novas = opcoes.filter((x) => x !== o);
    else if (selecionadas.includes(o)) novas = selecionadas.filter((x) => x !== o);
    else novas = [...selecionadas, o];
    if (novas.length === opcoes.length || novas.length === 0) novas = [];
    aoMudar(novas);
  };
  return (
    <div className="flex flex-wrap gap-1.5">
      {opcoes.map((o) => (
        <button key={o} type="button" className={`chip ${ativa(o) ? "on" : ""}`} onClick={() => clicar(o)}>
          {o}
        </button>
      ))}
    </div>
  );
}

/** Chips booleanos "incluir apenas quem é X" (vuln/agravos). */
function ChipsFlags({
  opcoes,
  selecionadas,
  aoAlternar,
}: {
  opcoes: Record<string, string>;
  selecionadas: string[];
  aoAlternar: (col: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(opcoes).map(([col, rotulo]) => (
        <button
          key={col}
          type="button"
          className={`chip ${selecionadas.includes(col) ? "on-warn" : ""}`}
          onClick={() => aoAlternar(col)}
        >
          {rotulo}
        </button>
      ))}
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

export function Sidebar({
  meta,
  resumo,
  anosDefault,
}: {
  meta: Meta;
  resumo: Resumo | undefined;
  anosDefault: number[];
}) {
  const { filtros, patch, toggle, limpar, temFiltrosAtivos } = useFiltros();
  const anosSel = filtros.anos.length ? filtros.anos : anosDefault;

  const setAnos = (anos: number[]) => patch({ anos: anos.sort((a, b) => a - b) });
  const toggleAno = (a: number) => {
    const nova = anosSel.includes(a) ? anosSel.filter((x) => x !== a) : [...anosSel, a];
    if (nova.length) setAnos(nova);
  };

  const ufsPorRegiao = (regiao: string) => meta.regioes[regiao] ?? [];
  const setUfs = (ufs: string[]) => patch({ ufs });

  const nFiltros = (f: Filtros) =>
    f.sexo.length + f.formas.length + f.racas.length + f.entradas.length + f.hiv.length;

  return (
    <aside className="card sticky top-4 max-h-[calc(100vh-2rem)] overflow-y-auto">
      <div className="flex items-center justify-between border-b border-border/70 px-4 py-3.5">
        <div className="flex items-center gap-2 text-[13.5px] font-bold tracking-tight">
          <span>🎛️</span> Filtros
        </div>
        {temFiltrosAtivos && (
          <button
            type="button"
            onClick={() => limpar(anosDefault)}
            className="rounded-lg border border-border px-2.5 py-1 text-[11.5px] font-semibold text-muted transition hover:border-red/50 hover:text-red"
          >
            ✕ Limpar
          </button>
        )}
      </div>

      <Secao titulo="Ano de notificação" icone="📅" aberta badge={anosSel.length > 1 ? anosSel.length : 0}>
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          <button type="button" className="chip" onClick={() => setAnos([Math.max(...meta.anos.filter((a) => a !== meta.ano_parcial))])}>
            Último ano
          </button>
          <button
            type="button" className="chip"
            onClick={() => setAnos(meta.anos.filter((a) => a !== meta.ano_parcial).slice(-3))}
          >
            Últimos 3
          </button>
          <button
            type="button" className="chip"
            onClick={() => setAnos(meta.anos.filter((a) => a !== meta.ano_parcial).slice(-10))}
          >
            Últimos 10
          </button>
          <button type="button" className="chip" onClick={() => setAnos([...meta.anos])}>
            Série completa
          </button>
        </div>
        <div className="grid grid-cols-5 gap-1">
          {meta.anos.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => toggleAno(a)}
              className={`chip !px-0 text-center tabular-nums ${anosSel.includes(a) ? "on" : ""}`}
              title={a === meta.ano_parcial ? "Dados parciais" : undefined}
            >
              {String(a).slice(2)}{a === meta.ano_parcial ? "*" : ""}
            </button>
          ))}
        </div>
        {meta.ano_parcial !== null && anosSel.includes(meta.ano_parcial) && (
          <p className="mt-2 text-[11px] leading-snug text-yellow">
            * {meta.ano_parcial}: dados parciais — o SINAN tem atraso de notificação.
          </p>
        )}
      </Secao>

      <Secao titulo="Localização" icone="📍" aberta badge={filtros.ufs.length}>
        <div className="mb-2.5 flex flex-wrap gap-1.5">
          <button type="button" className={`chip ${filtros.ufs.length === 0 ? "on" : ""}`} onClick={() => setUfs([])}>
            Brasil
          </button>
          {Object.keys(meta.regioes).map((r) => {
            const siglas = ufsPorRegiao(r);
            const ativa = siglas.length > 0 && siglas.every((s) => filtros.ufs.includes(s)) && filtros.ufs.length === siglas.length;
            return (
              <button key={r} type="button" className={`chip ${ativa ? "on" : ""}`} onClick={() => setUfs(siglas)}>
                {r}
              </button>
            );
          })}
        </div>
        <div className="grid grid-cols-6 gap-1">
          {meta.ufs
            .slice()
            .sort((a, b) => a.sigla.localeCompare(b.sigla))
            .map((u) => (
              <button
                key={u.sigla}
                type="button"
                title={u.nome}
                onClick={() => toggle("ufs", u.sigla)}
                className={`chip !px-0 text-center ${filtros.ufs.includes(u.sigla) ? "on" : ""}`}
              >
                {u.sigla}
              </button>
            ))}
        </div>
      </Secao>

      <Secao titulo="Perfil do paciente" icone="👤" badge={filtros.sexo.length + filtros.racas.length + filtros.formas.length}>
        <div className="space-y-3">
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">Sexo</div>
            <Chips opcoes={meta.opcoes.sexo} selecionadas={filtros.sexo} aoMudar={(v) => patch({ sexo: v })} />
          </div>
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">Forma clínica</div>
            <Chips opcoes={meta.opcoes.formas} selecionadas={filtros.formas} aoMudar={(v) => patch({ formas: v })} />
          </div>
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">Raça/cor</div>
            <Chips opcoes={meta.opcoes.racas} selecionadas={filtros.racas} aoMudar={(v) => patch({ racas: v })} />
          </div>
        </div>
      </Secao>

      <Secao titulo="Perfil clínico" icone="🏥" badge={filtros.entradas.length + filtros.hiv.length}>
        <div className="space-y-3">
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">Tipo de entrada</div>
            <Chips opcoes={meta.opcoes.entradas} selecionadas={filtros.entradas} aoMudar={(v) => patch({ entradas: v })} />
          </div>
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-faint">Status HIV</div>
            <Chips opcoes={meta.opcoes.hiv} selecionadas={filtros.hiv} aoMudar={(v) => patch({ hiv: v })} />
          </div>
        </div>
      </Secao>

      <Secao titulo="Populações vulneráveis" icone="⚠️" badge={filtros.vuln.length}>
        <p className="mb-2 text-[11.5px] text-faint">Incluir apenas pacientes que sejam:</p>
        <ChipsFlags opcoes={meta.vulneraveis} selecionadas={filtros.vuln} aoAlternar={(c) => toggle("vuln", c)} />
      </Secao>

      <Secao titulo="Comorbidades" icone="💊" badge={filtros.agravos.length}>
        <p className="mb-2 text-[11.5px] text-faint">Incluir apenas pacientes com:</p>
        <ChipsFlags opcoes={meta.agravos} selecionadas={filtros.agravos} aoAlternar={(c) => toggle("agravos", c)} />
      </Secao>

      <div className="px-4 py-4">
        <div className="card2 rounded-xl border border-border bg-surface px-4 py-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-faint">Registros filtrados</div>
          {resumo ? (
            <>
              <div className="mt-0.5 text-lg font-bold tabular-nums text-ink">{fmt.format(resumo.total)}</div>
              <div className="text-[11.5px] text-muted">
                de {fmt.format(resumo.total_base)} ({resumo.pct_filtrado}%)
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent to-purple transition-all duration-500"
                  style={{ width: `${Math.max(resumo.pct_filtrado, 2)}%` }}
                />
              </div>
            </>
          ) : (
            <div className="skeleton mt-1 h-6 w-24" />
          )}
        </div>
        <p className="mt-3 text-center text-[10.5px] text-faint">Fonte: SINAN NET · Ministério da Saúde</p>
        <p className="sr-only">{nFiltros(filtros)}</p>
      </div>
    </aside>
  );
}
