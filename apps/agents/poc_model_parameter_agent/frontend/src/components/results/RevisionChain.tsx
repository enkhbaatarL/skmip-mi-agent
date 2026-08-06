import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { RevisionLink } from "../../api/types";

export function RevisionChain({ chain, currentRunId }: { chain: RevisionLink[]; currentRunId?: string }) {
  return <section className="card summary-card" aria-labelledby="revision-chain-title" data-testid="revision-chain"><div className="section-heading"><span className="eyebrow">RUN LINEAGE</span><h3 id="revision-chain-title">Revision Chain</h3></div><div className="revision-chain">{chain.length ? chain.map((link, index) => <span key={link.runId}><Link className={link.runId === currentRunId ? "current" : ""} to={`/runs/${link.runId}`}>r{link.revision} <small>{link.runId}</small></Link>{index < chain.length - 1 && <ArrowRight size={14} />}</span>) : <span className="muted">현재 Revision만 존재합니다.</span>}</div></section>;
}
