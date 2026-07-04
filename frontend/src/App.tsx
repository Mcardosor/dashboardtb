/**
 * App.tsx — Casca do painel: topbar, sidebar, hero, KPIs e abas.
 * Cada aba busca seus próprios dados (cacheados pelo TanStack Query),
 * então trocar de aba é instantâneo depois da primeira visita.
 */
import { useMemo, useState } from "react";
import { useMeta, useResumo } from "./api";
import { Hero } from "./components/Hero";
import { KpiCards } from "./components/KpiCards";
import { Sidebar } from "./components/Sidebar";
import { useFiltros, type Filtros } from "./state";
import { MapaTab, type MetricaMapa } from "./tabs/MapaTab";
import { PerfilTab } from "./tabs/PerfilTab";
import { ClinicoTab } from "./tabs/ClinicoTab";
import { ComorbidadesTab } from "./tabs/ComorbidadesTab";
import { TendenciaTab } from "./tabs/TendenciaTab";
import { DadosTab } from "./tabs/DadosTab";

const ABAS = [
  { id: "mapa", rotulo: "🗺️ Distribuição Geográfica" },
  { id: "perfil", rotulo: "👥 Perfil dos Pacientes" },
  { id: "clinico", rotulo: "🏥 Clínico & Diagnóstico" },
  { id: "comorbidades", rotulo: "⚠️ Comorbidades & Vulnerabilidades" },
  { id: "tendencia", rotulo: "📈 Tendência Histórica" },
  { id: "dados", rotulo: "📄 Dados" },
] as const;

type AbaId = (typeof ABAS)[number]["id"];

export default function App() {
  const { data: meta, isError: metaErro } = useMeta();
  const { filtros } = useFiltros();
  const [aba, setAba] = useState<AbaId>("mapa");
  const [metricaMapa, setMetricaMapa] = useState<MetricaMapa>("incidencia");
  const [sidebarAberta, setSidebarAberta] = useState(false);

  // Ano default: o mais recente com dados completos (ignora o ano parcial)
  const anosDefault = useMemo(() => {
    if (!meta) return [];
    const completos = meta.anos.filter((a) => a !== meta.ano_parcial);
    return [completos.length ? Math.max(...completos) : Math.max(...meta.anos)];
  }, [meta]);

  const filtrosEfetivos: Filtros = useMemo(
    () => ({ ...filtros, anos: filtros.anos.length ? filtros.anos : anosDefault }),
    [filtros, anosDefault],
  );

  const { data: resumo } = useResumo(filtrosEfetivos);

  if (metaErro) {
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <div className="card max-w-md p-8 text-center">
          <div className="text-4xl">🔌</div>
          <h1 className="mt-3 text-lg font-bold">API indisponível</h1>
          <p className="mt-2 text-sm text-muted">
            Não foi possível falar com o backend. Verifique se ele está rodando:
          </p>
          <code className="mt-3 block rounded-lg bg-surface p-3 text-left text-xs text-accent">
            cd backend && uvicorn main:app --port 8000
          </code>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="aurora" />

      {/* ── Topbar ── */}
      <div className="sticky top-0 z-40 border-b border-border/80 bg-bg/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1560px] items-center gap-3 px-4 py-2.5 lg:px-6">
          <span className="text-[15px] font-extrabold tracking-tight">
            Cenários<span className="text-orange">+</span>
          </span>
          <span className="text-faint">|</span>
          <span className="text-[13px] font-medium text-muted">Dashboard TB · SINAN</span>
          <div className="ml-auto hidden items-center gap-2 md:flex">
            {resumo && (
              <span className="badge">
                <span className="dot" style={{ background: "#3fb950" }} />
                API {resumo.fonte_obitos === "SIM" ? "· SIM conectado" : "· modo local"}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => setSidebarAberta(true)}
            className="chip on lg:hidden"
          >
            🎛️ Filtros
          </button>
        </div>
      </div>

      <div className="mx-auto grid max-w-[1560px] gap-5 px-4 py-5 lg:grid-cols-[300px_minmax(0,1fr)] lg:px-6">
        {/* ── Sidebar (drawer no mobile) ── */}
        <div className="hidden lg:block">
          {meta && <Sidebar meta={meta} resumo={resumo} anosDefault={anosDefault} />}
        </div>
        {sidebarAberta && meta && (
          <div className="modal-backdrop lg:hidden" onClick={() => setSidebarAberta(false)}>
            <div
              className="absolute left-0 top-0 h-full w-[320px] max-w-[85vw] overflow-y-auto bg-bg p-3"
              onClick={(e) => e.stopPropagation()}
            >
              <Sidebar meta={meta} resumo={resumo} anosDefault={anosDefault} />
            </div>
          </div>
        )}

        {/* ── Conteúdo ── */}
        <main className="min-w-0 space-y-5">
          <Hero anos={filtrosEfetivos.anos} anoParcial={meta?.ano_parcial ?? null} resumo={resumo} />

          <KpiCards resumo={resumo} metricaMapa={metricaMapa} aoEscolherMetrica={(m) => { setMetricaMapa(m); setAba("mapa"); }} />

          {/* Abas */}
          <nav className="card sticky top-[52px] z-30 flex gap-1 overflow-x-auto p-1.5">
            {ABAS.map((a) => (
              <button
                key={a.id}
                type="button"
                className={`tab-btn ${aba === a.id ? "active" : ""}`}
                onClick={() => setAba(a.id)}
              >
                {a.rotulo}
              </button>
            ))}
          </nav>

          <div key={aba} className="rise">
            {aba === "mapa" && (
              <MapaTab filtros={filtrosEfetivos} metrica={metricaMapa} setMetrica={setMetricaMapa} />
            )}
            {aba === "perfil" && <PerfilTab filtros={filtrosEfetivos} />}
            {aba === "clinico" && <ClinicoTab filtros={filtrosEfetivos} />}
            {aba === "comorbidades" && <ComorbidadesTab filtros={filtrosEfetivos} />}
            {aba === "tendencia" && <TendenciaTab filtros={filtrosEfetivos} />}
            {aba === "dados" && <DadosTab filtros={filtrosEfetivos} resumo={resumo} />}
          </div>

          {/* ── Footer ── */}
          <footer className="rounded-2xl bg-[#2B7BB9] px-8 py-7">
            <div className="text-lg font-extrabold tracking-tight text-white">
              Cenários<span className="text-[#E07B54]">+</span>
            </div>
            <div className="mt-0.5 text-[12.5px] text-white/75">
              Fonte: SINAN NET · Ministério da Saúde — Todos os direitos reservados.
            </div>
          </footer>
        </main>
      </div>
    </>
  );
}
