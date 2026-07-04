/**
 * ui.tsx — Peças pequenas compartilhadas: cartão de gráfico, skeleton,
 * contador animado e métrica compacta.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

/** Cartão padrão de gráfico com título e legenda explicativa. */
export function ChartCard({
  titulo,
  caption,
  children,
  className = "",
  acoes,
}: {
  titulo: string;
  caption?: string;
  children: ReactNode;
  className?: string;
  acoes?: ReactNode;
}) {
  return (
    <section className={`card card-hover p-5 rise ${className}`}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight text-ink">{titulo}</h3>
          {caption && <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{caption}</p>}
        </div>
        {acoes}
      </header>
      {children}
    </section>
  );
}

export function Skel({ h = 320 }: { h?: number }) {
  return <div className="skeleton w-full" style={{ height: h }} />;
}

export function SkelCard({ h = 380 }: { h?: number }) {
  return (
    <div className="card p-5">
      <div className="skeleton mb-3 h-5 w-48" />
      <div className="skeleton w-full" style={{ height: h - 60 }} />
    </div>
  );
}

/** Número que anima do valor anterior para o novo. */
export function CountUp({
  valor,
  formatar,
  duracao = 650,
}: {
  valor: number;
  formatar: (v: number) => string;
  duracao?: number;
}) {
  const [exibido, setExibido] = useState(valor);
  const anterior = useRef(valor);

  useEffect(() => {
    const de = anterior.current;
    const para = valor;
    anterior.current = valor;
    if (de === para) return;
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min((t - t0) / duracao, 1);
      const e = 1 - Math.pow(1 - k, 3); // ease-out cubic
      setExibido(de + (para - de) * e);
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [valor, duracao]);

  return <>{formatar(exibido)}</>;
}

/** Métrica compacta (rótulo + valor + detalhe). */
export function Metrica({
  rotulo,
  valor,
  detalhe,
  cor,
}: {
  rotulo: string;
  valor: string;
  detalhe?: string;
  cor?: string;
}) {
  return (
    <div className="card px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-faint">{rotulo}</div>
      <div className="mt-0.5 text-xl font-bold tracking-tight" style={cor ? { color: cor } : undefined}>
        {valor}
      </div>
      {detalhe && <div className="mt-0.5 text-[11.5px] text-muted">{detalhe}</div>}
    </div>
  );
}

/** Aviso suave (dados ausentes etc.). */
export function Aviso({ children }: { children: ReactNode }) {
  return (
    <div className="card border-yellow/30 bg-yellow/5 px-4 py-3 text-[13px] text-muted">
      {children}
    </div>
  );
}
