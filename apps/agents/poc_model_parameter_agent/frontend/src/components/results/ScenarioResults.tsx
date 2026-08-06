import { useEffect, useMemo, useState } from "react";
import type { ParameterProposal, RunDetail } from "../../api/types";
import { StatusBadge } from "../common/StatusBadge";
import { PressureGauge } from "./PressureGauge";
import { ProposalTable } from "./ProposalTable";
import { ParameterChart } from "./ParameterChart";
import { RationaleTrace } from "./RationaleTrace";

export function ScenarioResults({ run, onSelectionChange }: { run: RunDetail; onSelectionChange?: (scenarioKey: string, proposal?: ParameterProposal) => void }) {
  const [selectedScenarioKey, setSelectedScenarioKey] = useState(run.scenarios[0]?.scenarioKey ?? run.proposals[0]?.scenarioKey ?? "");
  const scenario = run.scenarios.find((item) => item.scenarioKey === selectedScenarioKey) ?? run.scenarios[0];
  const proposals = useMemo(() => run.proposals.filter((proposal) => proposal.scenarioKey === (scenario?.scenarioKey ?? selectedScenarioKey)), [run.proposals, scenario?.scenarioKey, selectedScenarioKey]);
  const [selectedCode, setSelectedCode] = useState(proposals[0]?.parameterCode ?? "");
  const selectedProposal = proposals.find((proposal) => proposal.parameterCode === selectedCode) ?? proposals[0];

  useEffect(() => {
    const first = run.proposals.find((proposal) => proposal.scenarioKey === (scenario?.scenarioKey ?? selectedScenarioKey));
    setSelectedCode(first?.parameterCode ?? "");
  }, [selectedScenarioKey, scenario?.scenarioKey, run.proposals]);

  useEffect(() => onSelectionChange?.(scenario?.scenarioKey ?? selectedScenarioKey, selectedProposal), [onSelectionChange, scenario?.scenarioKey, selectedScenarioKey, selectedProposal]);

  const selectProposal = (proposal: ParameterProposal) => setSelectedCode(proposal.parameterCode);
  return (
    <section className="scenario-results" aria-labelledby="scenario-result-title" data-testid="scenario-results">
      <div className="section-title-row"><div><span className="eyebrow">CALCULATION RESULT</span><h2 id="scenario-result-title">Scenario Result</h2></div><div className="section-title-row__meta"><StatusBadge>{run.status}</StatusBadge><span className="mono">{run.runId} · r{run.revision}</span></div></div>
      <div className="scenario-tabs" role="tablist" aria-label="Scenario 선택">
        {run.scenarios.map((item) => <button key={item.scenarioKey} role="tab" aria-selected={item.scenarioKey === scenario?.scenarioKey} aria-controls="scenario-panel" onClick={() => setSelectedScenarioKey(item.scenarioKey)}><strong>{item.title}</strong><span>{item.scenarioKey} · {item.declaredPressureBand ?? "band 없음"} · {item.probability ?? 0}%</span></button>)}
      </div>
      {scenario ? <div id="scenario-panel" role="tabpanel" className="scenario-panel">
        <section className="card narrative-card"><div><span className="eyebrow">NARRATIVE</span><h3>{scenario.title}</h3><p>{scenario.narrative}</p></div>{Boolean(scenario.mixedFactors?.length) && <div className="chip-list"><span className="chip-label">Mixed Factor</span>{scenario.mixedFactors?.map((factor) => <StatusBadge key={factor} tone="warning">{factor}</StatusBadge>)}</div>}</section>
        <div className="result-grid result-grid--summary">
          <PressureGauge declared={scenario.declaredPressureBand} computed={scenario.computedPressureBand} score={scenario.pressureScore} consistency={scenario.pressureConsistency} />
          <section className="card dimension-card"><div className="section-heading"><span className="eyebrow">RESOLVED INPUT</span><h3>Dimension Values</h3></div><div className="table-scroll"><table className="data-table"><thead><tr><th>dimension ID</th><th>value ID</th><th>의미</th><th>Lever</th><th>Event ID</th></tr></thead><tbody>{scenario.dimensions?.map((row) => <tr key={row.dimensionId}><td className="mono">{row.dimensionId}</td><td className="mono">{row.valueId}</td><td>{row.meaning ?? "—"}</td><td className="mono">{row.leverCodes?.join(", ") || "—"}</td><td className="mono">{row.eventIds?.join(", ") || "—"}</td></tr>)}</tbody></table></div>{Boolean(scenario.validationMessages?.length) && <ul className="compact-messages">{scenario.validationMessages?.map((message, index) => <li className={`message message--${message.level}`} key={index}>{message.message}</li>)}</ul>}</section>
        </div>
        {proposals.length ? <>
          <ProposalTable proposals={proposals} selectedCode={selectedProposal?.parameterCode} onSelect={selectProposal} />
          {selectedProposal && <div className="result-grid"><ParameterChart proposal={selectedProposal} /><RationaleTrace proposal={selectedProposal} /></div>}
        </> : <div className="empty-inline">이 Scenario에 저장된 Parameter Proposal이 없습니다.</div>}
      </div> : <div className="empty-inline">저장된 Scenario 결과가 없습니다.</div>}
    </section>
  );
}
