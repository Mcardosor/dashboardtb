/**
 * api.ts — Tipos da API e hooks de dados (TanStack Query).
 * Todos os endpoints compartilham os mesmos filtros (ver state.tsx).
 */
import { useQuery } from "@tanstack/react-query";
import type { Filtros } from "./state";

// ── Tipos ─────────────────────────────────────────────────────────────────────
export interface Meta {
  anos: number[];
  ano_parcial: number | null;
  ufs: { sigla: string; nome: string; regiao: string }[];
  regioes: Record<string, string[]>;
  opcoes: {
    sexo: string[];
    formas: string[];
    racas: string[];
    entradas: string[];
    hiv: string[];
  };
  vulneraveis: Record<string, string>;
  agravos: Record<string, string>;
}

export interface Resumo {
  total: number;
  total_base: number;
  pct_filtrado: number;
  cura: number;
  abandono: number;
  obitos: number;
  fonte_obitos: "SIM" | "SINAN";
  hiv_pos: number;
  municipios: number;
  incidencia: number;
  mortalidade: number;
  anos: number[];
}

export interface EstadoMapa {
  uf: string;
  nome: string;
  casos: number;
  casos_novos: number;
  obitos: number;
  incidencia: number;
  mortalidade: number;
  cura_pct: number;
  abandono_pct: number;
}

export interface Mapa {
  estados: EstadoMapa[];
  fonte_obitos: "SIM" | "SINAN";
}

export interface MunicipioDetalhe {
  municipio: string;
  nm_norm: string;
  casos: number;
  cura_pct: number;
  abandono_pct: number;
  obito_pct: number;
  hiv_pct: number;
}

export interface DetalheUf {
  uf: string;
  nome: string;
  kpis: {
    total: number;
    total_municipios: number;
    encerrados: number;
    cura_pct: number;
    abandono_pct: number;
    obito_pct: number;
    cura_novo_pct: number;
    n_enc_novo: number;
    cura_retrat_pct: number;
    n_enc_retrat: number;
    hiv_pct: number;
    n_hiv_conhecido: number;
  };
  municipios: MunicipioDetalhe[];
}

export interface Contagem {
  label: string;
  valor: number;
  pct?: number;
}

export interface Piramide {
  faixas: string[];
  masculino: number[];
  feminino: number[];
}

export interface DesfechoPor {
  categorias: string[];
  grupos: string[];
  n: Record<string, number>;
  pct: Record<string, Record<string, number>>;
}

export interface Perfil {
  sexo: Contagem[];
  forma: Contagem[];
  tipo_entrada: Contagem[];
  raca_cor: Contagem[];
  escolaridade: Contagem[];
  desfecho: Contagem[];
  desfecho_grupo: Contagem[];
  desfecho_por_raca: DesfechoPor;
  piramide_casos: Piramide;
  piramide_obitos: Piramide;
}

export interface TempoTratamento {
  n: number;
  mediana_inicio: number;
  pct_ate_7d: number;
  pct_acima_30d: number;
  duracao_mediana: number | null;
  histograma: { faixa: string; casos: number }[];
}

export interface Clinico {
  status_hiv: Contagem[];
  baciloscopia: Contagem[];
  teste_molecular: Contagem[];
  desfecho_por_hiv: DesfechoPor;
  coinfeccao_uf: { uf: string; nome: string; pct: number; n_testado: number }[];
  tempo_tratamento: TempoTratamento | null;
}

export interface Comorbidades {
  agravos: Contagem[];
  populacoes: (Contagem & { coluna: string })[];
  total: number;
  desfecho_por_vulneravel: {
    grupos: string[];
    linhas: { categoria: string; n: number; pct: Record<string, number> }[];
  };
  heatmap_uf: { ufs: string[]; agravos: string[]; valores: [number, number, number][] };
}

export interface Tendencia {
  ano: number;
  mensal: { meses: string[]; casos: number[]; media_hist: (number | null)[] };
  kpis: { total_ano: number; media_anual_hist: number; variacao_pct: number | null };
  anual: { ano: number; casos: number }[];
  obitos_anual: { ano: number; obitos: number }[] | null;
  estadual: { uf: string; nome: string; casos: number; media_hist: number; variacao_pct: number }[];
  indicadores: { anos: number[]; series: Record<string, (number | null)[]> } | null;
}

// ── Fetch ─────────────────────────────────────────────────────────────────────
export function filtrosQuery(f: Filtros): string {
  const p = new URLSearchParams();
  if (f.anos.length) p.set("anos", f.anos.join(","));
  if (f.ufs.length) p.set("ufs", f.ufs.join(","));
  if (f.sexo.length) p.set("sexo", f.sexo.join(","));
  if (f.formas.length) p.set("formas", f.formas.join(","));
  if (f.racas.length) p.set("racas", f.racas.join(","));
  if (f.entradas.length) p.set("entradas", f.entradas.join(","));
  if (f.hiv.length) p.set("hiv", f.hiv.join(","));
  if (f.vuln.length) p.set("vuln", f.vuln.join(","));
  if (f.agravos.length) p.set("agravos", f.agravos.join(","));
  return p.toString();
}

// Prefixa com o base path do build (ex: "/cenarios/tb-v2/") — necessário
// porque o app fica atrás de um proxy nginx sob um subcaminho.
export function withBase(url: string): string {
  return import.meta.env.BASE_URL.replace(/\/$/, "") + url;
}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(withBase(url));
  if (!r.ok) throw new Error(`${r.status} ${r.statusText} em ${url}`);
  return r.json();
}

const OPTS = { staleTime: 5 * 60_000, gcTime: 30 * 60_000, retry: 1 } as const;

export const useMeta = () =>
  useQuery<Meta>({ queryKey: ["meta"], queryFn: () => getJson("/api/meta"), staleTime: Infinity });

function useEndpoint<T>(nome: string, f: Filtros, habilitado = true) {
  const qs = filtrosQuery(f);
  return useQuery<T>({
    queryKey: [nome, qs],
    queryFn: () => getJson<T>(`/api/${nome}?${qs}`),
    enabled: habilitado,
    ...OPTS,
  });
}

export const useResumo = (f: Filtros) => useEndpoint<Resumo>("resumo", f);
export const useMapa = (f: Filtros) => useEndpoint<Mapa>("mapa", f);
export const usePerfil = (f: Filtros, on = true) => useEndpoint<Perfil>("perfil", f, on);
export const useClinico = (f: Filtros, on = true) => useEndpoint<Clinico>("clinico", f, on);
export const useComorbidades = (f: Filtros, on = true) => useEndpoint<Comorbidades>("comorbidades", f, on);
export const useTendencia = (f: Filtros, on = true) => useEndpoint<Tendencia>("tendencia", f, on);

export function useDetalheUf(f: Filtros, sigla: string | null) {
  const qs = filtrosQuery(f);
  return useQuery<DetalheUf>({
    queryKey: ["uf", sigla, qs],
    queryFn: () => getJson<DetalheUf>(`/api/uf/${sigla}?${qs}`),
    enabled: !!sigla,
    ...OPTS,
  });
}

export interface GeoFeature {
  type: string;
  properties: Record<string, unknown>;
  geometry: unknown;
}
export interface GeoJson {
  type: string;
  features: GeoFeature[];
}

export function useGeoJson(url: string, habilitado = true) {
  return useQuery<GeoJson>({
    queryKey: ["geo", url],
    queryFn: () => getJson(url),
    enabled: habilitado,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}
