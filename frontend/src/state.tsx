/**
 * state.tsx — Estado global dos filtros (Context + reducer simples).
 * Filtro vazio = "todos" (o backend só aplica WHERE quando o param chega).
 */
import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export interface Filtros {
  anos: number[];
  ufs: string[];
  sexo: string[];
  formas: string[];
  racas: string[];
  entradas: string[];
  hiv: string[];
  vuln: string[];
  agravos: string[];
}

export const FILTROS_INICIAIS: Filtros = {
  anos: [],
  ufs: [],
  sexo: [],
  formas: [],
  racas: [],
  entradas: [],
  hiv: [],
  vuln: [],
  agravos: [],
};

interface Ctx {
  filtros: Filtros;
  setFiltros: (f: Filtros) => void;
  patch: (parcial: Partial<Filtros>) => void;
  limpar: (anosDefault: number[]) => void;
  /** alterna um valor dentro de uma lista de filtro */
  toggle: (chave: keyof Filtros, valor: string | number) => void;
  temFiltrosAtivos: boolean;
}

const FiltrosContext = createContext<Ctx | null>(null);

export function FiltrosProvider({ children }: { children: ReactNode }) {
  const [filtros, setFiltros] = useState<Filtros>(FILTROS_INICIAIS);

  const valor = useMemo<Ctx>(() => {
    const patch = (parcial: Partial<Filtros>) => setFiltros((f) => ({ ...f, ...parcial }));
    const toggle = (chave: keyof Filtros, v: string | number) =>
      setFiltros((f) => {
        const lista = f[chave] as (string | number)[];
        const nova = lista.includes(v) ? lista.filter((x) => x !== v) : [...lista, v];
        return { ...f, [chave]: nova };
      });
    const limpar = (anosDefault: number[]) =>
      setFiltros({ ...FILTROS_INICIAIS, anos: anosDefault });
    const temFiltrosAtivos =
      filtros.ufs.length > 0 || filtros.sexo.length > 0 || filtros.formas.length > 0 ||
      filtros.racas.length > 0 || filtros.entradas.length > 0 || filtros.hiv.length > 0 ||
      filtros.vuln.length > 0 || filtros.agravos.length > 0;
    return { filtros, setFiltros, patch, toggle, limpar, temFiltrosAtivos };
  }, [filtros]);

  return <FiltrosContext.Provider value={valor}>{children}</FiltrosContext.Provider>;
}

export function useFiltros(): Ctx {
  const ctx = useContext(FiltrosContext);
  if (!ctx) throw new Error("useFiltros fora do FiltrosProvider");
  return ctx;
}
