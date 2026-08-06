import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import type { ValidationMessage } from "../../api/types";

export function EvaluationInvariants({ messages }: { messages: ValidationMessage[] }) {
  const defaultMessages: ValidationMessage[] = messages.length ? messages : [{ level: "pass", message: "저장된 구조화 결과를 사용합니다." }];
  return <section className="card summary-card" aria-labelledby="invariants-title"><div className="section-heading"><span className="eyebrow">OUTPUT CONTRACT</span><h3 id="invariants-title">Evaluation Invariants</h3></div><ul className="invariant-list">{defaultMessages.map((message, index) => <li className={`message message--${message.level}`} key={`${message.code}-${index}`}>{message.level === "error" ? <XCircle size={15} /> : message.level === "warning" ? <AlertTriangle size={15} /> : <CheckCircle2 size={15} />}<span>{message.message}</span>{message.code && <code>{message.code}</code>}</li>)}</ul></section>;
}
