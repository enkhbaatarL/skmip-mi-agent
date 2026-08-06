import { ArrowLeft, ArrowUpRight, GitBranch, PlayCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { ParameterProposal, RunDetail } from "../../api/types";
import { useRun } from "../../api/queries";
import { EmptyState, ErrorState, LoadingState } from "../../components/common/AsyncState";
import { JsonBlock } from "../../components/common/JsonBlock";
import { StatusBadge } from "../../components/common/StatusBadge";
import { FinalFeedbackCard } from "../../components/feedback/FinalFeedbackCard";
import { EvaluationInvariants } from "../../components/results/EvaluationInvariants";
import { RevisionChain } from "../../components/results/RevisionChain";
import { ScenarioResults } from "../../components/results/ScenarioResults";

const formatDate = (value: string) => value ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "long", timeStyle: "medium" }).format(new Date(value)) : "—";

export function RunDetailPage() {
  const { runId } = useParams();
  const query = useRun(runId);
  const navigate = useNavigate();
  const [displayRun, setDisplayRun] = useState<RunDetail | null>(null);
  const [selection, setSelection] = useState<{ scenarioKey?: string; proposal?: ParameterProposal }>({});
  const run = displayRun ?? query.data;
  const onSelection = useCallback((scenarioKey: string, proposal?: ParameterProposal) => setSelection({ scenarioKey, proposal }), []);

  useEffect(() => {
    if (displayRun && displayRun.runId !== runId) {
      setDisplayRun(null);
      setSelection({});
    }
  }, [displayRun, runId]);

  if (query.isLoading) return <LoadingState label="Run Detail을 불러오는 중입니다." />;
  if (query.isError) return <ErrorState error={query.error} action={<Link className="button button--secondary" to="/runs">목록으로</Link>} />;
  if (!run) return <EmptyState title="Run을 찾을 수 없습니다." description="삭제되었거나 잘못된 Run ID입니다." />;

  return (
    <div className="page-stack run-detail-page">
      <header className="page-header"><div><Link className="back-link" to="/runs"><ArrowLeft size={14} />Run History</Link><span className="eyebrow">RUN DETAIL · REVISION {run.revision}</span><h1>{run.runId}</h1><p>{formatDate(run.createdAt)} · <StatusBadge>{run.status}</StatusBadge></p></div><button className="button button--primary" onClick={() => navigate("/generate", { state: { continueRun: run } })}><PlayCircle size={15} />이 리비전에서 이어서 작업</button></header>
      <section className="detail-metadata-grid">
        <div className="card metadata-list"><div className="section-heading"><span className="eyebrow">IDENTITY</span><h2>Run Metadata</h2></div><dl><div><dt>Run ID</dt><dd className="mono">{run.runId}</dd></div><div><dt>Revision</dt><dd>r{run.revision}</dd></div><div><dt>Target Market</dt><dd>{run.targetMarket}</dd></div><div><dt>Event IDs</dt><dd className="mono">{run.eventIds.join(", ")}</dd></div><div><dt>Comparison Run</dt><dd className="mono">{run.comparisonRunId ?? "—"}</dd></div><div><dt>Horizon</dt><dd className="mono">{run.horizon?.start ?? "—"} → {run.horizon?.end ?? "—"}{run.horizon?.includesRecovery ? " + Recovery" : ""}</dd></div></dl></div>
        <div className="card metadata-list"><div className="section-heading"><span className="eyebrow">LINEAGE &amp; ASSETS</span><h2>Snapshot</h2></div><dl><div><dt>Parent Run</dt><dd>{run.parentRunId ? <Link to={`/runs/${run.parentRunId}`}>{run.parentRunId}<ArrowUpRight size={12} /></Link> : "Root Revision"}</dd></div><div><dt>Child Run</dt><dd>{run.childRunId ? <Link to={`/runs/${run.childRunId}`}>{run.childRunId}<ArrowUpRight size={12} /></Link> : "—"}</dd></div></dl><div className="context-chips">{run.assetSnapshot.map((asset) => <code key={`${asset.assetType}-${asset.assetKey}`}>{asset.assetKey}@{asset.version}</code>)}</div></div>
      </section>
      <RevisionChain chain={run.revisionChain} currentRunId={run.runId} />
      <section className="card detail-section"><div className="section-heading"><span className="eyebrow">PIPELINE EVIDENCE</span><h2>입력과 단계별 Artifact</h2></div><details className="accordion"><summary>원본 Scenario JSON</summary><JsonBlock value={run.sourceScenarioJson} label="Immutable source" /></details><details className="accordion"><summary>Normalized Input</summary><JsonBlock value={run.normalizedInput ?? {}} label="Normalized input" /></details><details className="accordion"><summary>Clarification Answers</summary><JsonBlock value={run.clarificationAnswers ?? {}} label="Interim Feedback answers" /></details><details className="accordion"><summary>Validation Report</summary><JsonBlock value={run.validationReport ?? {}} label="Validation report" /></details>{run.artifacts?.map((artifact, index) => <details className="accordion" key={`${artifact.stepId}-${index}`}><summary><span>{String(index + 1).padStart(2, "0")} · {artifact.stepId}</span><StatusBadge>{artifact.status}</StatusBadge></summary><JsonBlock value={{ output: artifact.output, validationMessages: artifact.validationMessages, exclusions: artifact.exclusions }} label="Artifact JSON" /></details>)}</section>
      <EvaluationInvariants messages={run.evaluationInvariants ?? []} />
      {run.proposals.length || run.scenarios.length ? <ScenarioResults run={run} onSelectionChange={onSelection} /> : <EmptyState title="결과가 없습니다." description="이 Run에는 저장된 Proposal이 없습니다." />}
      <section className="card detail-section"><div className="section-heading section-heading--inline"><div><span className="eyebrow">UNIFIED LEDGER</span><h2>Feedback History</h2></div><GitBranch size={17} /></div>{run.feedback?.length ? run.feedback.map((feedback) => <details className="accordion" key={feedback.feedbackId}><summary><span><StatusBadge tone={feedback.tag === "final" ? "info" : "neutral"}>{feedback.tag}</StatusBadge> {feedback.rawText}</span><code>{feedback.feedbackId}</code></summary><JsonBlock value={feedback} label="Feedback Record JSON" /></details>) : <p className="muted">이 Run에 연결된 Feedback이 없습니다.</p>}</section>
      <FinalFeedbackCard key={run.runId} run={run} scenarioKey={selection.scenarioKey} proposal={selection.proposal} onCreated={(child) => { setDisplayRun(child); setSelection({}); navigate(`/runs/${child.runId}`, { replace: true }); }} />
    </div>
  );
}
