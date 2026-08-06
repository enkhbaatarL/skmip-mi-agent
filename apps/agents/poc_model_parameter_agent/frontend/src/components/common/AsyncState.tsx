import { AlertTriangle, Database, LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";

export function LoadingState({ label = "데이터를 불러오는 중입니다." }: { label?: string }) {
  return <div className="async-state" role="status"><LoaderCircle className="spin" size={20} /><span>{label}</span></div>;
}

export function ErrorState({ error, action }: { error: unknown; action?: ReactNode }) {
  const message = error instanceof Error ? error.message : "요청을 처리하지 못했습니다.";
  return <div className="async-state async-state--error" role="alert"><AlertTriangle size={20} /><div><strong>오류가 발생했습니다.</strong><p>{message}</p>{action}</div></div>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><Database size={22} aria-hidden="true" /><strong>{title}</strong><p>{description}</p></div>;
}
