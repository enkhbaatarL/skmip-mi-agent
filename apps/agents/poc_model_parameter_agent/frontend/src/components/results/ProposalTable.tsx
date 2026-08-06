import type { ParameterProposal } from "../../api/types";
import { StatusBadge } from "../common/StatusBadge";

const format = (value: number, digits = 2) => Number.isFinite(value) ? value.toFixed(digits) : "—";

export function ProposalTable({ proposals, selectedCode, onSelect }: { proposals: ParameterProposal[]; selectedCode?: string; onSelect: (proposal: ParameterProposal) => void }) {
  return (
    <section className="card result-section" aria-labelledby="proposal-title">
      <div className="section-heading"><span className="eyebrow">PARAMETER OUTPUT</span><h3 id="proposal-title">Parameter Proposal</h3><p>행을 선택하면 Plot과 Rationale이 전환됩니다.</p></div>
      <div className="table-scroll">
        <table className="data-table proposal-table">
          <thead><tr><th>parameter</th><th>parameter name</th><th>domain</th><th>적용 기간</th><th className="numeric">baseline peak</th><th className="numeric">proposed peak</th><th className="numeric">Δ</th><th className="numeric">Δ%</th><th className="numeric">confidence</th><th className="numeric">warning</th></tr></thead>
          <tbody>
            {proposals.map((proposal) => {
              const selected = proposal.parameterCode === selectedCode;
              return (
                <tr key={`${proposal.scenarioKey}-${proposal.parameterCode}`} className={selected ? "is-selected" : ""} aria-selected={selected} data-testid={`proposal-row-${proposal.parameterCode}`} onClick={() => onSelect(proposal)}>
                  <td><button type="button" className="table-row-action" aria-label={`${proposal.parameterName} Parameter 선택`} onClick={() => onSelect(proposal)}>{proposal.parameterCode}</button>{proposal.feedbackAdjusted && <StatusBadge tone="warning">Feedback Adjustment</StatusBadge>}</td>
                  <td>{proposal.parameterName}</td><td><StatusBadge>{proposal.domain}</StatusBadge></td><td className="mono">{proposal.periodStart ?? "—"} → {proposal.periodEnd ?? "—"}</td>
                  <td className="numeric mono">{format(proposal.baselinePeak)}</td><td className="numeric mono">{format(proposal.proposedPeak)}</td>
                  <td className={`numeric mono ${proposal.delta >= 0 ? "value-up" : "value-down"}`}>{proposal.delta >= 0 ? "+" : ""}{format(proposal.delta)}</td>
                  <td className={`numeric mono ${proposal.deltaPct >= 0 ? "value-up" : "value-down"}`}>{proposal.deltaPct >= 0 ? "+" : ""}{format(proposal.deltaPct)}%</td>
                  <td className="numeric mono">{format(proposal.confidence * (proposal.confidence <= 1 ? 100 : 1), 0)}%</td><td className="numeric mono">{proposal.warningCount}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
