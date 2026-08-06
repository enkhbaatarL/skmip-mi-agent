import { ArrowLeft, Check, ExternalLink, ShieldAlert, X } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { useCandidate, useCandidateDecision } from "../../api/queries";
import { useToast } from "../../app/Toast";
import { EmptyState, ErrorState, LoadingState } from "../../components/common/AsyncState";
import { JsonBlock } from "../../components/common/JsonBlock";
import { StatusBadge } from "../../components/common/StatusBadge";

export function CandidateDetailPage() {
  const { candidateId = "" } = useParams();
  const candidate = useCandidate(candidateId);
  const decision = useCandidateDecision(candidateId);
  const [reviewerNote, setReviewerNote] = useState("");
  const [conflict, setConflict] = useState<string | null>(null);
  const { notify } = useToast();
  const navigate = useNavigate();
  if (candidate.isLoading) return <LoadingState label="Candidate Detail을 불러오는 중입니다." />;
  if (candidate.isError) return <ErrorState error={candidate.error} />;
  if (!candidate.data) return <EmptyState title="Candidate를 찾을 수 없습니다." description="잘못된 Candidate ID입니다." />;
  const item = candidate.data;
  const pending = item.status === "pending";
  const approve = async () => {
    setConflict(null);
    try { await decision.approve.mutateAsync(reviewerNote); notify("Candidate를 승인하고 새 Asset Version을 활성화했습니다.", "success"); }
    catch (error) { if (error instanceof ApiError && error.status === 409) setConflict("Base Version이 현재 Active Version과 다릅니다. 어떤 Asset도 변경되지 않았습니다."); else notify(error instanceof Error ? error.message : "승인하지 못했습니다.", "error"); }
  };
  const reject = async () => {
    if (!reviewerNote.trim()) { notify("거절 사유를 입력하세요.", "error"); return; }
    try { await decision.reject.mutateAsync(reviewerNote.trim()); notify("Candidate를 거절했습니다. Asset은 변경되지 않았습니다.", "success"); }
    catch (error) { notify(error instanceof Error ? error.message : "거절하지 못했습니다.", "error"); }
  };
  return <div className="page-stack candidate-detail" data-testid="candidate-detail"><header className="page-header"><div><Link className="back-link" to="/learning?tab=candidates"><ArrowLeft size={14} />Candidates</Link><span className="eyebrow">CANDIDATE DETAIL</span><h1>{item.candidateId}</h1><p><StatusBadge>{item.status}</StatusBadge> · Confidence {(item.confidence * (item.confidence <= 1 ? 100 : 1)).toFixed(0)}%</p></div>{item.sourceRunId && <Link className="button button--secondary" to={`/runs/${item.sourceRunId}`}>원본 Run 이동<ExternalLink size={13} /></Link>}</header>{conflict && <div className="conflict-banner" role="alert"><ShieldAlert size={18} /><div><strong>Version Conflict · HTTP 409</strong><p>{conflict}</p></div></div>}<section className="candidate-grid"><div className="card"><div className="section-heading"><span className="eyebrow">SOURCE EVIDENCE</span><h2>Source Feedback</h2></div><blockquote>{item.sourceFeedbackText ?? "원문을 불러올 수 없습니다."}</blockquote><div className="context-chips"><code>feedback/{item.sourceFeedbackId}</code>{item.sourceTag && <code>tag/{item.sourceTag}</code>}{item.sourceRunId && <code>run/{item.sourceRunId}</code>}</div><JsonBlock value={item.sourceContext ?? {}} label="Feedback Context" /></div><div className="card metadata-list"><div className="section-heading"><span className="eyebrow">CLASSIFICATION</span><h2>분류 근거와 감지 신호</h2></div><dl><div><dt>Target</dt><dd><StatusBadge tone={item.targetType === "memory" ? "info" : "warning"}>{item.targetType}</StatusBadge> <code>{item.targetAssetKey}</code></dd></div><div><dt>Version</dt><dd className="mono">v{item.baseVersion} → v{item.proposedVersion}</dd></div><div><dt>Classification</dt><dd>{item.classification ?? "—"}</dd></div><div><dt>Expected Impact</dt><dd>{item.expectedImpact ?? "—"}</dd></div><div><dt>Rationale</dt><dd>{item.rationale ?? "—"}</dd></div></dl><div className="signal-list">{item.matchedSignals?.map((signal) => <StatusBadge key={signal} tone="neutral">{signal}</StatusBadge>)}</div>{Boolean(item.risks?.length) && <div className="risk-list"><strong>Risks</strong><ul>{item.risks?.map((risk) => <li key={risk}>{risk}</li>)}</ul></div>}</div></section><section className="card diff-card"><div className="section-heading section-heading--inline"><div><span className="eyebrow">PROPOSED CHANGE</span><h2>Line Diff</h2></div><span className="mono">{item.changeLine}</span></div><pre aria-label="Candidate Line Diff">{item.diff || "변경 Diff가 없습니다."}</pre><details className="accordion"><summary>Proposed Content</summary><JsonBlock value={item.proposedContent ?? {}} label="Proposed Asset Content" /></details></section><section className="card evaluation-card"><div className="section-heading"><span className="eyebrow">SAFETY GATE</span><h2>Evaluation</h2></div><ul>{item.evaluations.map((check) => <li key={check.name} className={check.passed ? "passed" : "failed"}>{check.passed ? <Check size={15} /> : <X size={15} />}<div><strong>{check.name}</strong><p>{check.detail ?? (check.passed ? "통과" : "실패")}</p></div></li>)}</ul></section><section className="card candidate-actions"><div><label className="field field--full"><span>Reviewer Note {pending && <em>거절 시 required</em>}</span><textarea rows={3} value={reviewerNote} onChange={(event) => setReviewerNote(event.target.value)} disabled={!pending} placeholder="승인 메모 또는 거절 사유를 입력하세요." /></label><p>승인은 Base Version을 Transaction에서 재검증합니다. 거절은 Candidate 상태만 변경합니다.</p></div><div><button className="button button--danger" disabled={!pending || decision.reject.isPending} onClick={reject}><X size={14} />Candidate 거절</button><button className="button button--primary" disabled={!pending || decision.approve.isPending || item.evaluations.some((check) => !check.passed)} onClick={approve}><Check size={14} />Candidate 승인</button></div></section></div>;
}
