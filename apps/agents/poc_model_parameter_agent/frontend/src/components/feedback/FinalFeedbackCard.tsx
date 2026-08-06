import { RefreshCcw, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../../api/client";
import { useSubmitFinalFeedback } from "../../api/queries";
import type { FeedbackScope, ParameterProposal, RunDetail } from "../../api/types";
import { useToast } from "../../app/Toast";
import { StatusBadge } from "../common/StatusBadge";

export function FinalFeedbackCard({ run, scenarioKey, proposal, onCreated }: { run: RunDetail; scenarioKey?: string; proposal?: ParameterProposal; onCreated: (run: RunDetail) => void }) {
  const [scope, setScope] = useState<FeedbackScope>(proposal ? "parameter" : scenarioKey ? "scenario" : "run");
  const [text, setText] = useState("");
  const [conflicted, setConflicted] = useState(false);
  const mutation = useSubmitFinalFeedback(run.runId);
  const { notify } = useToast();
  const locked = Boolean(run.hasFinalFeedback || run.finalFeedbackCount > 0 || conflicted);
  const selectedScenario = useMemo(
    () => run.scenarios.find((scenario) => scenario.scenarioKey === scenarioKey),
    [run.scenarios, scenarioKey],
  );
  const parameterCodes = useMemo(() => {
    if (scope === "parameter" && proposal) return [proposal.parameterCode];
    const source = scope === "scenario" && scenarioKey
      ? run.proposals.filter((item) => item.scenarioKey === scenarioKey)
      : run.proposals;
    return [...new Set(source.map((item) => item.parameterCode))];
  }, [proposal, run.proposals, scenarioKey, scope]);

  useEffect(() => {
    setScope(proposal ? "parameter" : scenarioKey ? "scenario" : "run");
    setText("");
    setConflicted(false);
  }, [run.runId]);

  useEffect(() => {
    if (scope === "parameter" && !proposal) setScope(scenarioKey ? "scenario" : "run");
    if (scope === "scenario" && !scenarioKey) setScope("run");
  }, [proposal, scenarioKey, scope]);

  const context = useMemo(() => [
    `run/${run.runId} · r${run.revision}`,
    `scope/${scope}`,
    scenarioKey ? `scenario/${scenarioKey}` : undefined,
    `events/${run.eventIds.join(",")}`,
    proposal?.leverCodes?.length ? `levers/${proposal.leverCodes.join(",")}` : undefined,
    selectedScenario?.dimensions?.length ? `dimensions/${selectedScenario.dimensions.map((item) => `${item.dimensionId}=${item.valueId}`).join(",")}` : undefined,
    parameterCodes.length ? `parameters/${parameterCodes.join(",")}` : undefined,
    `assets/${run.assetSnapshot.map((asset) => `${asset.assetKey}@${asset.version}`).join(",")}`,
  ].filter(Boolean) as string[], [parameterCodes, proposal, run, scenarioKey, scope, selectedScenario]);

  const submit = async () => {
    if (!text.trim() || (scope === "parameter" && (!proposal || !scenarioKey)) || (scope === "scenario" && !scenarioKey)) return;
    try {
      const response = await mutation.mutateAsync({ scope, scenarioKey: scope !== "run" ? scenarioKey : undefined, parameterCode: scope === "parameter" ? proposal?.parameterCode : undefined, text: text.trim() });
      notify(`Final Feedback이 저장되어 r${response.resultRun.revision} Child Revision을 생성했습니다.`, "success");
      if ("proposals" in response.resultRun) onCreated(response.resultRun);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setConflicted(true);
        notify("이 Revision에는 이미 Final Feedback이 있습니다. 어떤 값도 변경하지 않았습니다.", "error");
      }
      else notify(error instanceof Error ? error.message : "Final Feedback을 저장하지 못했습니다.", "error");
    }
  };

  return (
    <section className="card final-feedback-card" aria-labelledby="final-feedback-title">
      <div className="section-heading section-heading--inline"><div><span className="eyebrow">HUMAN-IN-THE-LOOP</span><h3 id="final-feedback-title">최종 사용자 피드백 → Parameter 재생성</h3></div><div className="badge-group"><StatusBadge tone="info">tag=final</StatusBadge><StatusBadge tone="neutral">source=result_review</StatusBadge></div></div>
      {locked && <div className="message message--warning" role="status">이 Revision에는 Final Feedback이 이미 저장되었습니다. Child Revision에서 새 피드백을 제출하세요.</div>}
      <fieldset className="segmented-control" disabled={locked}><legend>Feedback Scope</legend>{(["parameter", "scenario", "run"] as FeedbackScope[]).map((value) => <label key={value}><input type="radio" name="feedback-scope" value={value} checked={scope === value} onChange={() => setScope(value)} disabled={value === "parameter" && !proposal || value === "scenario" && !scenarioKey} /><span>{value === "parameter" ? "선택 Parameter" : value === "scenario" ? "선택 Scenario" : "Run 전체"}</span></label>)}</fieldset>
      <div className="context-chips" aria-label="저장되는 Context">{context.map((item) => <code key={item}>{item}</code>)}</div>
      <label className="field field--full"><span>Final Feedback</span><textarea value={text} disabled={locked} onChange={(event) => setText(event.target.value)} rows={5} placeholder="예: 현물 Cargo 가용성 영향이 너무 직접적입니다. 선택 Parameter를 완화해 주세요." /></label>
      <div className="card-actions"><button type="button" className="button button--secondary" disabled={locked} onClick={() => setText("현물 Cargo 가용성 영향이 너무 직접적입니다. 선택 Parameter를 완화해 주세요.")}><RefreshCcw size={14} />예시 피드백 채우기</button><button type="button" className="button button--primary" disabled={locked || !text.trim() || mutation.isPending || scope === "parameter" && (!proposal || !scenarioKey) || scope === "scenario" && !scenarioKey} onClick={submit}><Send size={14} />{mutation.isPending ? "재생성 중…" : "피드백 저장 + Parameter 재생성"}</button></div>
    </section>
  );
}
