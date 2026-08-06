import { BookOpenText, ExternalLink, Filter, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useFeedback } from "../../api/queries";
import { EmptyState, ErrorState, LoadingState } from "../../components/common/AsyncState";
import { JsonBlock } from "../../components/common/JsonBlock";
import { StatusBadge } from "../../components/common/StatusBadge";

const formatDate = (value: string) => value ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";
const compactJson = (value: unknown) => {
  const text = JSON.stringify(value ?? {});
  return text.length > 100 ? `${text.slice(0, 97)}…` : text;
};

export function FeedbackLedgerPage() {
  const [tag, setTag] = useState("");
  const [source, setSource] = useState("");
  const [status, setStatus] = useState("");
  const feedback = useFeedback({ page: 1, pageSize: 100, tag, source, status });
  return (
    <div className="page-stack feedback-page">
      <header className="page-header"><div><span className="eyebrow">03 · UNIFIED FEEDBACK</span><h1>피드백 원장</h1><p>Interim과 Final Feedback의 원문, Context, Adjustment와 Learning 연결을 하나의 원장에서 조회합니다.</p></div><button className="button button--secondary" onClick={() => feedback.refetch()} disabled={feedback.isFetching}><RefreshCw size={14} />새로고침</button></header>
      <section className="card filter-bar" aria-label="피드백 필터"><Filter size={15} /><label><span>Tag</span><select value={tag} onChange={(event) => setTag(event.target.value)}><option value="">전체</option><option value="interim">interim</option><option value="final">final</option></select></label><label><span>Source</span><select value={source} onChange={(event) => setSource(event.target.value)}><option value="">전체</option><option value="clarification">clarification</option><option value="result_review">result_review</option></select></label><label><span>Processing</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">전체</option><option value="pending">pending</option><option value="processed">processed</option><option value="failed">failed</option></select></label></section>
      {feedback.isLoading && <LoadingState label="통합 Feedback 원장을 불러오는 중입니다." />}
      {feedback.isError && <ErrorState error={feedback.error} />}
      {feedback.data && !feedback.data.items.length && <EmptyState title="조건에 맞는 Feedback이 없습니다." description="Clarification 응답 또는 Final Feedback 제출 시 원문이 이 원장에 저장됩니다." />}
      {Boolean(feedback.data?.items.length) && <section className="card table-card"><div className="table-card__header"><div><span className="eyebrow">IMMUTABLE RECORDS</span><h2>{feedback.data?.total} feedback records</h2></div><StatusBadge tone="info">interim + final</StatusBadge></div><div className="table-scroll"><table className="data-table feedback-table"><thead><tr><th>feedback id</th><th>tag / source</th><th>run / revision</th><th>scope</th><th>원문</th><th>context mapping</th><th>adjustment</th><th>processing</th><th>result run</th><th>learning batch</th><th>created at</th></tr></thead><tbody>{feedback.data?.items.map((item) => <tr key={item.feedbackId}><td className="mono">{item.feedbackId}</td><td><div className="badge-stack"><StatusBadge tone={item.tag === "final" ? "info" : "neutral"}>{item.tag}</StatusBadge><StatusBadge tone="neutral">{item.source}</StatusBadge></div></td><td><Link className="table-link mono" to={`/runs/${item.runId}`}>{item.runId}</Link><small>r{item.revision ?? "—"}</small></td><td><StatusBadge>{item.scope}</StatusBadge></td><td className="feedback-text">{item.rawText}</td><td><code className="json-preview">{compactJson(item.context)}</code></td><td><code className="json-preview">{item.adjustment ? compactJson(item.adjustment) : "—"}</code></td><td><StatusBadge>{item.processingStatus}</StatusBadge></td><td>{item.resultRunId ? <Link className="table-link mono" to={`/runs/${item.resultRunId}`}>{item.resultRunId}<ExternalLink size={11} /></Link> : "—"}</td><td className="mono">{item.learningBatchId ?? "—"}</td><td className="mono">{formatDate(item.createdAt)}</td></tr>)}</tbody></table></div><div className="feedback-records"><div className="section-heading"><BookOpenText size={16} /><div><span className="eyebrow">RAW RECORDS</span><h3>실제 저장 Record JSON</h3></div></div>{feedback.data?.items.map((item) => <details className="accordion" key={`raw-${item.feedbackId}`}><summary><span>{item.feedbackId} · {item.tag}/{item.source}</span><StatusBadge>{item.processingStatus}</StatusBadge></summary><JsonBlock value={item} label="Stored Feedback Record" /></details>)}</div></section>}
    </div>
  );
}
