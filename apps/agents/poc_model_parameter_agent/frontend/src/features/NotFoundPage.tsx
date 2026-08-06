import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return <section className="page-center"><span className="eyebrow">404</span><h1>화면을 찾을 수 없습니다.</h1><p>요청한 경로가 존재하지 않습니다.</p><Link className="button button--primary" to="/generate"><ArrowLeft size={15} />Parameter 생성으로 이동</Link></section>;
}
