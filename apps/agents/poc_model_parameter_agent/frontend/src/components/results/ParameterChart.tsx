import ReactECharts from "echarts-for-react";
import type { ParameterProposal } from "../../api/types";

export function ParameterChart({ proposal }: { proposal: ParameterProposal }) {
  const series = proposal.series;
  const eventStart = series.findIndex((point) => point.phase === "event");
  const eventEnd = series.findLastIndex((point) => point.phase === "event");
  const recoveryStart = series.findIndex((point) => point.phase === "recovery");
  const recoveryEnd = series.findLastIndex((point) => point.phase === "recovery");
  const markAreas: Array<Array<{ name?: string; xAxis: string; itemStyle?: { color: string } }>> = [];
  if (eventStart >= 0 && eventEnd >= 0) markAreas.push([{ name: "Event Window", xAxis: series[eventStart].month, itemStyle: { color: "rgba(177, 72, 70, .08)" } }, { xAxis: series[eventEnd].month }]);
  if (recoveryStart >= 0 && recoveryEnd >= 0) markAreas.push([{ name: "Recovery", xAxis: series[recoveryStart].month, itemStyle: { color: "rgba(222, 157, 45, .08)" } }, { xAxis: series[recoveryEnd].month }]);

  const option = {
    animation: !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    grid: { left: 48, right: 22, top: 42, bottom: 48 },
    tooltip: { trigger: "axis", valueFormatter: (value: number) => Number(value).toFixed(2) },
    legend: { top: 4, right: 8, data: ["Baseline", "Proposed", "Δ"] },
    xAxis: { type: "category", data: series.map((point) => point.month), axisLabel: { fontFamily: "var(--font-mono)", fontSize: 10 } },
    yAxis: [
      { type: "value", name: proposal.unit ?? "index", nameTextStyle: { fontSize: 10 }, axisLabel: { fontFamily: "var(--font-mono)", fontSize: 10 } },
      { type: "value", name: "Δ", splitLine: { show: false }, axisLabel: { fontFamily: "var(--font-mono)", fontSize: 10 } },
    ],
    series: [
      { name: "Baseline", type: "line", data: series.map((point) => point.baseline), symbol: "none", lineStyle: { color: "#708292", width: 1.5, type: "dashed" } },
      { type: "line", stack: "difference-fill", data: series.map((point) => point.baseline), symbol: "none", silent: true, lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, tooltip: { show: false } },
      { type: "line", stack: "difference-fill", data: series.map((point) => (point.delta ?? point.proposed - point.baseline)), symbol: "none", silent: true, lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(63, 127, 122, .16)" }, tooltip: { show: false } },
      { name: "Proposed", type: "line", data: series.map((point) => point.proposed), symbol: "circle", symbolSize: 4, lineStyle: { color: "#3f7f7a", width: 2 }, markArea: { silent: true, data: markAreas } },
      { name: "Δ", type: "bar", yAxisIndex: 1, data: series.map((point) => point.delta ?? point.proposed - point.baseline), barMaxWidth: 12, itemStyle: { color: "rgba(63, 127, 122, .28)" } },
    ],
  };

  return (
    <section className="card chart-card" aria-labelledby="chart-title">
      <div className="section-heading section-heading--inline"><div><span className="eyebrow">MONTHLY SERIES</span><h3 id="chart-title">Baseline vs Proposed</h3></div><span className="synthetic-label">Prototype synthetic baseline</span></div>
      {series.length ? <ReactECharts option={option} style={{ height: 340 }} opts={{ renderer: "svg" }} /> : <div className="empty-inline">표시할 월별 Series가 없습니다.</div>}
    </section>
  );
}
