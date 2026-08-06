import { ArrowRight, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { useRuns } from "../../api/queries";
import { EmptyState, ErrorState, LoadingState } from "../../components/common/AsyncState";
import { StatusBadge } from "../../components/common/StatusBadge";

const formatDate = (value: string) => value ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";

export function RunHistoryPage() {
  const runs = useRuns({ page: 1, pageSize: 100 });
  return (
    <div className="page-stack">
      <header className="page-header"><div><span className="eyebrow">02 · PERSISTED RUNS</span><h1>Run History</h1><p>MySQL에 저장된 Run Revision, Feedback, Adjustment와 Asset Snapshot을 조회합니다.</p></div><button type="button" className="button button--secondary" onClick={() => runs.refetch()} disabled={runs.isFetching}><RefreshCw size={14} />새로고침</button></header>
      {runs.isLoading && <LoadingState label="Run History를 불러오는 중입니다." />}
      {runs.isError && <ErrorState error={runs.error} />}
      {runs.data && !runs.data.items.length && <EmptyState title="저장된 Run이 없습니다." description="Parameter 생성에서 첫 Run을 실행하면 여기에 영구 저장됩니다." />}
      {Boolean(runs.data?.items.length) && <section className="card table-card" aria-label="Run History 목록"><div className="table-card__header"><div><span className="eyebrow">RUN LEDGER</span><h2>{runs.data?.total ?? 0} revisions</h2></div></div><div className="table-scroll"><table className="data-table"><thead><tr><th>run id</th><th>revision</th><th>parent run id</th><th>comparison run id</th><th>market</th><th>event ids</th><th>created at</th><th>status</th><th className="numeric">scenario</th><th className="numeric">proposal</th><th>interim / final</th><th className="numeric">adjustment</th><th>asset versions</th><th>action</th></tr></thead><tbody>{runs.data?.items.map((run) => <tr key={run.runId}><td className="mono"><Link className="table-link" to={`/runs/${run.runId}`}>{run.runId}</Link></td><td className="numeric mono">r{run.revision}</td><td className="mono">{run.parentRunId ?? "—"}</td><td className="mono">{run.comparisonRunId ?? "—"}</td><td><StatusBadge tone="info">{run.targetMarket}</StatusBadge></td><td className="mono">{run.eventIds.join(", ")}</td><td className="mono">{formatDate(run.createdAt)}</td><td><StatusBadge>{run.status}</StatusBadge></td><td className="numeric mono">{run.scenarioCount}</td><td className="numeric mono">{run.proposalCount}</td><td><StatusBadge tone="neutral">{run.interimFeedbackCount} / {run.finalFeedbackCount}</StatusBadge></td><td className="numeric mono">{run.adjustmentCount}</td><td><div className="asset-inline">{run.assetSnapshot.slice(0, 3).map((asset) => <code key={`${asset.assetKey}-${asset.version}`}>{asset.assetKey}@{asset.version}</code>)}{run.assetSnapshot.length > 3 && <small>+{run.assetSnapshot.length - 3}</small>}</div></td><td><Link className="button button--compact" to={`/runs/${run.runId}`}>Detail<ArrowRight size={13} /></Link></td></tr>)}</tbody></table></div></section>}
    </div>
  );
}
