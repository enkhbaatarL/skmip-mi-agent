import { ArrowRight, BrainCircuit, CheckCircle2, Clock3, Play, RefreshCw, Shield, XCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../api/client";
import { useAssets, useBatches, useCandidates, useFeedback, useProcessPending } from "../../api/queries";
import type { AssetSummary } from "../../api/types";
import { useToast } from "../../app/Toast";
import { EmptyState, ErrorState, LoadingState } from "../../components/common/AsyncState";
import { JsonBlock } from "../../components/common/JsonBlock";
import { StatusBadge } from "../../components/common/StatusBadge";

type Tab = "batches" | "candidates" | "assets";
const formatDate = (value?: string) => value ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";

function LearningBatchesTab() {
  const batches = useBatches({ page: 1, pageSize: 100 });
  if (batches.isLoading) return <LoadingState label="Learning Batch를 불러오는 중입니다." />;
  if (batches.isError) return <ErrorState error={batches.error} />;
  if (!batches.data?.items.length) return <EmptyState title="Learning Batch가 없습니다." description="미처리 Feedback을 Worker가 검토하면 Batch가 생성됩니다." />;
  return <section className="card table-card" aria-label="Learning Batches"><div className="table-scroll"><table className="data-table"><thead><tr><th>batch id</th><th>created at</th><th>feedback ids</th><th>interim / final</th><th>status</th><th>reviewer mode</th><th className="numeric">candidates</th><th>classification summary</th><th>review summary</th></tr></thead><tbody>{batches.data.items.map((batch) => <tr key={batch.batchId}><td className="mono">{batch.batchId}</td><td className="mono">{formatDate(batch.createdAt)}</td><td className="mono">{batch.feedbackIds.join(", ") || "—"}</td><td><StatusBadge tone="neutral">{batch.interimCount} / {batch.finalCount}</StatusBadge></td><td><StatusBadge>{batch.status}</StatusBadge></td><td>{batch.reviewerMode}</td><td className="numeric mono">{batch.candidateCount}</td><td><code className="json-preview">{JSON.stringify(batch.classificationSummary ?? {})}</code></td><td><code className="json-preview">{JSON.stringify(batch.reviewSummary ?? {})}</code></td></tr>)}</tbody></table></div></section>;
}

function CandidatesTab() {
  const candidates = useCandidates({ page: 1, pageSize: 100 });
  if (candidates.isLoading) return <LoadingState label="Learning Candidate를 불러오는 중입니다." />;
  if (candidates.isError) return <ErrorState error={candidates.error} />;
  if (!candidates.data?.items.length) return <EmptyState title="Learning Candidate가 없습니다." description="Worker 검토 결과 Memory 또는 Skill 변경 근거가 충분하면 Candidate가 생성됩니다." />;
  const sorted = [...candidates.data.items].sort((a, b) => Number(b.status === "pending") - Number(a.status === "pending"));
  return <section className="card table-card" aria-label="Learning Candidates"><div className="table-scroll"><table className="data-table candidate-table"><thead><tr><th>candidate id</th><th>source feedback / tag</th><th>source run context</th><th>target</th><th>base → proposed</th><th>change line</th><th className="numeric">confidence</th><th>evaluation</th><th>status</th><th>action</th></tr></thead><tbody>{sorted.map((candidate) => { const passed = candidate.evaluations.filter((check) => check.passed).length; return <tr key={candidate.candidateId}><td className="mono">{candidate.candidateId}</td><td><span className="mono">{candidate.sourceFeedbackId}</span><StatusBadge tone={candidate.sourceTag === "final" ? "info" : "neutral"}>{candidate.sourceTag ?? "—"}</StatusBadge></td><td className="mono">{candidate.sourceRunId ?? "—"}</td><td><StatusBadge tone={candidate.targetType === "memory" ? "info" : "warning"}>{candidate.targetType}</StatusBadge><code>{candidate.targetAssetKey}</code></td><td className="mono">v{candidate.baseVersion} → v{candidate.proposedVersion}</td><td>{candidate.changeLine}</td><td className="numeric mono">{(candidate.confidence * (candidate.confidence <= 1 ? 100 : 1)).toFixed(0)}%</td><td><StatusBadge tone={passed === candidate.evaluations.length ? "success" : "warning"}>{passed}/{candidate.evaluations.length}</StatusBadge></td><td><StatusBadge>{candidate.status}</StatusBadge></td><td><Link className="button button--compact" to={`/learning/candidates/${candidate.candidateId}`}>Detail<ArrowRight size={13} /></Link></td></tr>; })}</tbody></table></div></section>;
}

function AssetRow({ asset }: { asset: AssetSummary }) {
  const versions = useQuery({ queryKey: ["asset-versions", asset.assetType, asset.assetKey], queryFn: () => api.assetVersions(asset.assetType, asset.assetKey) });
  const history = versions.data?.items.length ? versions.data.items : asset.versions;
  return <article className="card asset-card"><div className="asset-card__header"><div><span className="eyebrow">{asset.assetType}</span><h3>{asset.assetKey}</h3></div><div className="badge-group"><StatusBadge tone={asset.learnable ? "info" : "neutral"}>{asset.learnable ? "Learnable" : "Locked"}</StatusBadge><StatusBadge tone="success">Active v{asset.activeVersion}</StatusBadge></div></div>{versions.isError && <div className="message message--warning">Version History를 추가로 불러오지 못해 목록 응답만 표시합니다.</div>}<div className="asset-history">{history.map((version) => <details className="accordion" key={`${version.assetKey}-${version.version}`} open={version.active}><summary><span>Version {version.version}</span><span>{version.active && <StatusBadge tone="success">Active</StatusBadge>}<code>{formatDate(version.createdAt)}</code></span></summary><dl className="compact-dl"><div><dt>Source Candidate</dt><dd className="mono">{version.sourceCandidateId ?? "Seed"}</dd></div><div><dt>State</dt><dd>{version.active ? "Active" : "Inactive"}</dd></div></dl><JsonBlock value={version.content} label={`Version ${version.version} Content`} /></details>)}</div></article>;
}

function AssetVersionsTab() {
  const assets = useAssets();
  if (assets.isLoading) return <LoadingState label="Asset Version을 불러오는 중입니다." />;
  if (assets.isError) return <ErrorState error={assets.error} />;
  if (!assets.data?.items.length) return <EmptyState title="Asset Version이 없습니다." description="Migration과 Seed가 완료되었는지 확인하세요." />;
  return <div className="asset-grid" aria-label="Asset Versions">{assets.data.items.map((asset) => <AssetRow key={`${asset.assetType}-${asset.assetKey}`} asset={asset} />)}</div>;
}

export function LearningPage() {
  const [params, setParams] = useSearchParams();
  const value = params.get("tab");
  const tab: Tab = value === "candidates" || value === "assets" ? value : "batches";
  const pending = useFeedback({ page: 1, pageSize: 1 });
  const process = useProcessPending();
  const { notify } = useToast();
  const counts = pending.data?.pendingCounts ?? { interim: 0, final: 0, total: 0 };
  const runWorker = async () => {
    try { await process.mutateAsync(); notify("Learning Worker의 한 Cycle을 완료했습니다.", "success"); }
    catch (error) { notify(error instanceof Error ? error.message : "Learning Cycle에 실패했습니다.", "error"); }
  };
  const changeTab = (next: Tab) => setParams({ tab: next });

  return <div className="page-stack learning-page"><header className="page-header"><div><span className="eyebrow">04 · BACKGROUND REVIEW</span><h1>Learning Pipeline</h1><p>Main Pipeline과 분리된 Worker가 미처리 Interim/Final Feedback을 검토합니다. Candidate는 수동 승인 전 Asset을 변경하지 않습니다.</p></div><button className="button button--primary" onClick={runWorker} disabled={process.isPending}><Play size={14} />{process.isPending ? "Worker 실행 중…" : "Learning Worker 실행"}</button></header><section className="learning-overview"><div className="stat-card"><Clock3 size={17} /><span>미처리 Interim</span><strong>{counts.interim}</strong></div><div className="stat-card"><Clock3 size={17} /><span>미처리 Final</span><strong>{counts.final}</strong></div><div className="stat-card"><BrainCircuit size={17} /><span>Reviewer Mode</span><strong>Deterministic</strong></div><div className="stat-card"><Shield size={17} /><span>Approval</span><strong>Manual HITL</strong></div></section><div className="tab-bar" role="tablist" aria-label="Learning Pipeline 화면"><button role="tab" aria-selected={tab === "batches"} onClick={() => changeTab("batches")}>A · Learning Batches</button><button role="tab" aria-selected={tab === "candidates"} onClick={() => changeTab("candidates")}>B · Candidates</button><button role="tab" aria-selected={tab === "assets"} onClick={() => changeTab("assets")}>C · Asset Versions</button><button className="tab-refresh" type="button" aria-label="Learning 데이터 새로고침" onClick={() => window.location.reload()}><RefreshCw size={13} /></button></div><div role="tabpanel" data-testid={`learning-${tab}`}>{tab === "batches" ? <LearningBatchesTab /> : tab === "candidates" ? <CandidatesTab /> : <AssetVersionsTab />}</div><aside className="policy-note"><CheckCircle2 size={16} /><span>Memory와 Skill만 Learnable입니다.</span><XCircle size={16} /><span>Flow Profile, Catalog, Domain Rule, Evaluation Case는 Locked입니다.</span></aside></div>;
}
