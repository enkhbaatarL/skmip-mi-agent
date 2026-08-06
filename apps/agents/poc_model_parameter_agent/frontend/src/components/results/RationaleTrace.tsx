import type { ParameterProposal } from "../../api/types";
import { JsonBlock } from "../common/JsonBlock";
import { StatusBadge } from "../common/StatusBadge";

export function RationaleTrace({ proposal }: { proposal: ParameterProposal }) {
  return (
    <section className="card trace-card" aria-labelledby="trace-title">
      <div className="section-heading"><span className="eyebrow">EVIDENCE &amp; RATIONALE</span><h3 id="trace-title">Rationale Trace</h3><p>{proposal.parameterCode}의 구조화 계산 경로입니다.</p></div>
      {proposal.trace.length ? <ol className="trace-list">
        {proposal.trace.map((step, index) => <li key={`${step.step}-${index}`}><span className="trace-index">{String(index + 1).padStart(2, "0")}</span><div><div className="trace-label"><strong>{step.label}</strong>{step.status && <StatusBadge>{step.status}</StatusBadge>}</div><p>{step.summary}</p>{step.details !== undefined && <JsonBlock value={step.details} label="단계 상세" />}</div></li>)}
      </ol> : <div className="empty-inline">저장된 Trace가 없습니다.</div>}
      <div className="formula-block"><span>FORMULA</span><code>{proposal.formula ?? "Formula가 저장되지 않았습니다."}</code></div>
      <details className="accordion"><summary>Evidence 원본</summary><JsonBlock value={proposal.evidence ?? proposal.contributions ?? {}} label="Evidence JSON" /></details>
      <details className="accordion"><summary>전체 월별 시계열 Table</summary><div className="table-scroll"><table className="data-table"><thead><tr><th>month</th><th className="numeric">baseline</th><th className="numeric">proposed</th><th className="numeric">Δ</th><th className="numeric">Δ%</th><th>phase</th></tr></thead><tbody>{proposal.series.map((point) => <tr key={point.month}><td className="mono">{point.month}</td><td className="numeric mono">{point.baseline.toFixed(2)}</td><td className="numeric mono">{point.proposed.toFixed(2)}</td><td className="numeric mono">{point.delta?.toFixed(2) ?? "—"}</td><td className="numeric mono">{point.deltaPct?.toFixed(2) ?? "—"}%</td><td>{point.phase}</td></tr>)}</tbody></table></div></details>
    </section>
  );
}
