import { Activity, BookOpenCheck, BrainCircuit, Database, History, Menu, PanelLeftClose, SlidersHorizontal, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useFeedback, useHealth, useRuns } from "../api/queries";
import { StatusBadge } from "../components/common/StatusBadge";
import { useTargetMarket } from "./TargetMarketContext";

const navigation = [
  { to: "/generate", number: "01", label: "Parameter 생성", shortLabel: "생성", icon: SlidersHorizontal },
  { to: "/runs", number: "02", label: "Run History", shortLabel: "Runs", icon: History },
  { to: "/feedback", number: "03", label: "피드백 원장", shortLabel: "Feedback", icon: BookOpenCheck },
  { to: "/learning", number: "04", label: "Learning Pipeline", shortLabel: "Learning", icon: BrainCircuit },
];

const breadcrumbFor = (pathname: string) => {
  if (pathname.startsWith("/runs/")) return ["Run History", "Run Detail"];
  if (pathname.startsWith("/runs")) return ["Run History"];
  if (pathname.startsWith("/feedback")) return ["피드백 원장"];
  if (pathname.startsWith("/learning/candidates/")) return ["Learning Pipeline", "Candidate Detail"];
  if (pathname.startsWith("/assets")) return ["Learning Pipeline", "Asset Versions"];
  if (pathname.startsWith("/learning")) return ["Learning Pipeline"];
  return ["Parameter 생성"];
};

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const health = useHealth();
  const runs = useRuns({ page: 1, pageSize: 1 });
  const feedback = useFeedback({ page: 1, pageSize: 1 });
  const { targetMarket } = useTargetMarket();
  const breadcrumbs = breadcrumbFor(location.pathname);
  const databaseStatus = health.isError ? "unavailable" : health.data?.databaseStatus ?? "확인 중";
  const databaseTone = health.isError
    ? "error"
    : databaseStatus === "connected" || databaseStatus === "healthy"
      ? "success"
      : "warning";

  return (
    <div className="app-shell">
      <aside id="primary-navigation" className={`rail${mobileOpen ? " rail--open" : ""}`} aria-label="주요 메뉴">
        <div className="rail__brand">
          <div className="rail__mark"><Activity size={18} /></div>
          <div><strong>LNG PARAM</strong><span>Learning Agent</span></div>
          <button className="rail__mobile-close icon-button" aria-label="메뉴 닫기" onClick={() => setMobileOpen(false)}><X size={18} /></button>
        </div>
        <nav className="rail__nav">
          {navigation.map((item) => {
            const Icon = item.icon;
            const count = item.to === "/runs" ? runs.data?.total : item.to === "/feedback" ? feedback.data?.total : undefined;
            return (
              <NavLink key={item.to} to={item.to} onClick={() => setMobileOpen(false)} className={({ isActive }) => `rail__link${isActive ? " rail__link--active" : ""}`}>
                <span className="rail__number">{item.number}</span><Icon size={16} aria-hidden="true" /><span className="rail__label">{item.label}</span>
                {count !== undefined && <span className="rail__count" aria-label={`${count}개`}>{count}</span>}
              </NavLink>
            );
          })}
        </nav>
        <div className="rail__footer"><PanelLeftClose size={15} /><span>Prototype Control Plane</span></div>
      </aside>
      {mobileOpen && <button className="rail-backdrop" aria-label="메뉴 닫기" onClick={() => setMobileOpen(false)} />}
      <div className="app-main">
        <header className="topbar">
          <div className="topbar__left">
            <button className="topbar__menu icon-button" aria-label="메뉴 열기" aria-controls="primary-navigation" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={18} /></button>
            <nav className="breadcrumb" aria-label="현재 위치">
              <span>MI Agent</span>{breadcrumbs.map((crumb) => <span key={crumb}>{crumb}</span>)}
            </nav>
          </div>
          <div className="topbar__status">
            <StatusBadge tone="info">AGENT_MODE · {health.data?.agentMode?.toUpperCase() ?? "확인 중"}</StatusBadge>
            <StatusBadge tone={databaseTone}>
              <Database size={12} /> MySQL · {databaseStatus}
            </StatusBadge>
            <StatusBadge tone="neutral">TARGET · {targetMarket}</StatusBadge>
          </div>
        </header>
        <main className="content" id="main-content"><Outlet /></main>
      </div>
      <nav className="mobile-nav" aria-label="모바일 주요 메뉴">
        {navigation.map((item) => <NavLink key={item.to} to={item.to} onClick={() => setMobileOpen(false)} className={({ isActive }) => isActive ? "active" : ""}>{item.number}<span>{item.shortLabel}</span></NavLink>)}
      </nav>
    </div>
  );
}
