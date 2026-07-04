/**
 * Chart.tsx — Wrapper fino do ECharts: init único, resize automático,
 * setOption com notMerge e eventos de clique opcionais.
 */
import { memo, useEffect, useRef } from "react";
import type { ECharts } from "echarts/core";
import { echarts } from "../theme";

interface Props {
  option: object;
  height?: number | string;
  onClick?: (params: any) => void;
  className?: string;
}

function ChartInner({ option, height = 320, onClick, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
  const clickRef = useRef(onClick);
  clickRef.current = onClick;

  useEffect(() => {
    const el = ref.current!;
    const chart = echarts.init(el, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.on("click", (p: any) => clickRef.current?.(p));
    const ro = new ResizeObserver(() => chart.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option as never, { notMerge: true });
  }, [option]);

  return <div ref={ref} className={className} style={{ height, width: "100%" }} />;
}

export const Chart = memo(ChartInner);
