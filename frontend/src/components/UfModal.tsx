/**
 * UfModal.tsx — Drill-down de um estado: mapa municipal, KPIs de coorte,
 * top municípios e tabela completa.
 */
import { useEffect, useMemo, useState } from "react";
import { useDetalheUf, useGeoJson, type MunicipioDetalhe } from "../api";
import type { Filtros } from "../state";
import { baseOption, C, echarts, fmt, fmt1, FONT, SEQ_CASOS } from "../theme";
import { Chart } from "./Chart";
import { Metrica, Skel } from "./ui";

const norm = (s: string) =>
  s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

export function UfModal({
  uf,
  filtros,
  aoFechar,
}: {
  uf: string;
  filtros: Filtros;
  aoFechar: () => void;
}) {
  const { data: detalhe, isLoading } = useDetalheUf(filtros, uf);
  const { data: geo } = useGeoJson(`/api/geojson/municipios/${uf}`);
  const [mapaPronto, setMapaPronto] = useState(false);
  const [topN, setTopN] = useState(15);

  useEffect(() => {
    const fecharEsc = (e: KeyboardEvent) => e.key === "Escape" && aoFechar();
    window.addEventListener("keydown", fecharEsc);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", fecharEsc);
      document.body.style.overflow = "";
    };
  }, [aoFechar]);

  useEffect(() => {
    if (geo) {
      echarts.registerMap(`mun-${uf}`, geo as never);
      setMapaPronto(true);
    }
  }, [geo, uf]);

  const porNorm = useMemo(() => {
    const d: Record<string, MunicipioDetalhe> = {};
    detalhe?.municipios.forEach((m) => (d[m.nm_norm] = m));
    return d;
  }, [detalhe]);

  const opcaoMapa = useMemo(() => {
    if (!detalhe || !geo) return null;
    const dados = geo.features.map((f) => {
      const nome = String(f.properties["NM_MUN"] ?? "");
      const m = porNorm[norm(nome)];
      return { name: nome, value: m?.casos ?? 0 };
    });
    const max = Math.max(...dados.map((d) => d.value), 1);
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => {
          const m = porNorm[norm(p.name ?? "")];
          if (!m) return `<b>${p.name}</b><br/>0 casos`;
          return (
            `<b>${m.municipio}</b><br/>` +
            `Casos: <b>${fmt.format(m.casos)}</b><br/>` +
            `Cura: <b>${fmt1.format(m.cura_pct)}%</b> · Abandono: <b>${fmt1.format(m.abandono_pct)}%</b><br/>` +
            `Óbitos: <b>${fmt1.format(m.obito_pct)}%</b> · HIV+: <b>${fmt1.format(m.hiv_pct)}%</b>`
          );
        },
      },
      visualMap: {
        type: "continuous",
        min: 0,
        max,
        inRange: { color: SEQ_CASOS },
        left: 8,
        bottom: 8,
        itemHeight: 90,
        text: [fmt.format(max), "0"],
        textStyle: { color: C.muted, fontSize: 10, fontFamily: FONT },
      },
      series: [{
        type: "map",
        map: `mun-${uf}`,
        nameProperty: "NM_MUN",
        roam: true,
        scaleLimit: { min: 0.8, max: 8 },
        itemStyle: { areaColor: "#141c28", borderColor: "#2a3646", borderWidth: 0.5 },
        emphasis: {
          label: { show: true, color: "#fff", fontSize: 10.5, fontFamily: FONT },
          itemStyle: { borderColor: "#79c0ff", borderWidth: 1.4 },
        },
        label: { show: false },
        data: dados,
      }],
    };
  }, [detalhe, geo, porNorm, uf]);

  const opcaoTop = useMemo(() => {
    if (!detalhe) return null;
    const top = detalhe.municipios.slice(0, topN).slice().reverse();
    return {
      ...baseOption,
      tooltip: {
        ...baseOption.tooltip,
        formatter: (p: any) => `<b>${p.name}</b><br/>${fmt.format(p.value)} casos`,
      },
      grid: { left: 8, right: 56, top: 4, bottom: 4, containLabel: true },
      xAxis: { type: "value", axisLabel: { color: C.faint, fontSize: 10.5 }, splitLine: { lineStyle: { color: "#141c28" } } },
      yAxis: {
        type: "category",
        data: top.map((m) => m.municipio),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: C.muted, fontSize: 11, fontFamily: FONT },
      },
      visualMap: {
        show: false,
        type: "continuous",
        min: 0,
        max: Math.max(...detalhe.municipios.map((m) => m.casos), 1),
        inRange: { color: ["#f4a261", "#e76f51", "#c0392b", "#7b0c0c"].reverse() },
        dimension: 0,
      },
      series: [{
        type: "bar",
        barWidth: "64%",
        data: top.map((m) => m.casos),
        itemStyle: { borderRadius: [0, 5, 5, 0] },
        label: {
          show: true, position: "right", color: C.muted, fontSize: 10.5, fontFamily: FONT,
          formatter: (p: any) => fmt.format(p.value),
        },
      }],
    };
  }, [detalhe, topN]);

  const k = detalhe?.kpis;

  return (
    <div className="modal-backdrop grid place-items-center overflow-y-auto p-4" onClick={aoFechar}>
      <div
        className="card max-h-[92vh] w-full max-w-5xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-card/95 px-6 py-4 backdrop-blur">
          <div>
            <h2 className="text-lg font-bold tracking-tight">
              📍 {detalhe?.nome ?? uf} <span className="text-muted">({uf})</span>
            </h2>
            {detalhe && (
              <p className="text-[12px] text-muted">
                {fmt.format(k!.total)} notificações · {fmt.format(k!.total_municipios)} municípios
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={aoFechar}
            className="grid h-9 w-9 place-items-center rounded-xl border border-border text-muted transition hover:border-red/50 hover:text-red"
          >
            ✕
          </button>
        </header>

        <div className="space-y-5 p-6">
          {/* Mapa municipal */}
          {mapaPronto && opcaoMapa ? (
            <Chart option={opcaoMapa} height={400} />
          ) : (
            <Skel h={400} />
          )}
          {uf === "DF" && (
            <p className="text-[11.5px] text-faint">
              ℹ️ O SINAN não distingue Regiões Administrativas — dados do DF inteiro.
            </p>
          )}

          {/* KPIs de coorte */}
          {k && (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              <Metrica rotulo="Notificações" valor={fmt.format(k.total)} detalhe="todos os desfechos" />
              <Metrica
                rotulo="Cura · caso novo"
                valor={`${fmt1.format(k.cura_novo_pct)}%`}
                detalhe={`${fmt.format(k.n_enc_novo)} encerrados · meta ≥85%`}
                cor={k.cura_novo_pct >= 85 ? "#3fb950" : "#d29922"}
              />
              <Metrica
                rotulo="Cura · retratamento"
                valor={`${fmt1.format(k.cura_retrat_pct)}%`}
                detalhe={`${fmt.format(k.n_enc_retrat)} encerrados`}
              />
              <Metrica
                rotulo="Abandono"
                valor={`${fmt1.format(k.abandono_pct)}%`}
                detalhe={k.abandono_pct >= 5 ? "🔴 acima da meta OMS (<5%)" : "🟢 dentro da meta OMS"}
                cor={k.abandono_pct >= 5 ? "#f85149" : "#3fb950"}
              />
              <Metrica
                rotulo="Óbitos por TB"
                valor={`${fmt1.format(k.obito_pct)}%`}
                detalhe={`sobre ${fmt.format(k.encerrados)} encerrados`}
              />
              <Metrica
                rotulo="HIV+"
                valor={`${fmt1.format(k.hiv_pct)}%`}
                detalhe={`${fmt.format(k.n_hiv_conhecido)} com testagem`}
                cor="#d2a8ff"
              />
            </div>
          )}

          {/* Top municípios */}
          <section>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-[14.5px] font-semibold">Top municípios por casos</h3>
              <div className="flex gap-1 rounded-xl border border-border bg-surface p-1">
                {[10, 15, 20].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setTopN(n)}
                    className={`rounded-lg px-2.5 py-1 text-[11.5px] font-semibold transition ${
                      topN === n ? "bg-accent/20 text-accent" : "text-faint hover:text-muted"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            {opcaoTop ? <Chart option={opcaoTop} height={Math.max(320, topN * 26)} /> : <Skel h={380} />}
          </section>

          {/* Tabela completa */}
          {detalhe && (
            <details className="card overflow-hidden !bg-surface">
              <summary className="cursor-pointer px-5 py-3 text-[13px] font-semibold text-muted transition hover:text-ink">
                📋 Ver todos os {fmt.format(detalhe.kpis.total_municipios)} municípios
              </summary>
              <div className="max-h-[340px] overflow-y-auto">
                <table className="tbl w-full">
                  <thead>
                    <tr>
                      <th>#</th><th>Município</th><th>Casos</th><th>Cura</th><th>Abandono</th><th>Óbito</th><th>HIV+</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detalhe.municipios.map((m, i) => (
                      <tr key={m.nm_norm}>
                        <td className="text-faint">{i + 1}</td>
                        <td className="font-medium">{m.municipio}</td>
                        <td className="tabular-nums">{fmt.format(m.casos)}</td>
                        <td className="tabular-nums text-green">{fmt1.format(m.cura_pct)}%</td>
                        <td className="tabular-nums text-yellow">{fmt1.format(m.abandono_pct)}%</td>
                        <td className="tabular-nums text-red">{fmt1.format(m.obito_pct)}%</td>
                        <td className="tabular-nums text-purple">{fmt1.format(m.hiv_pct)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}

          {isLoading && <Skel h={200} />}
        </div>
      </div>
    </div>
  );
}
