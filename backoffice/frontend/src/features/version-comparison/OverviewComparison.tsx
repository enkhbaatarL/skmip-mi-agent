import { AlertTriangle } from "lucide-react";
import {
  countScenarioRoles,
  scenarioProbabilitySum,
  summarizeChecks,
  type DeterministicCheckResult
} from "../../domain/deterministicChecks";
import type {
  ApiVersion,
  VersionedCreateScenariosData
} from "../../domain/apiTypes";
import { totalTokens } from "../../domain/tokenUsage";
import {
  VERSION_ORDER,
  type VersionRunState
} from "./types";

interface OverviewComparisonProps {
  versions: Record<ApiVersion, VersionRunState>;
  checks: Record<ApiVersion, DeterministicCheckResult[]>;
  complete?: boolean;
}

export function comparisonSuccessCount(
  versions: Record<ApiVersion, VersionRunState>
): number {
  return VERSION_ORDER.filter(
    (version) => versions[version].status === "success"
  ).length;
}

function comparableData(
  state: VersionRunState
): VersionedCreateScenariosData | undefined {
  return state.status === "success" ? state.response?.data ?? undefined : undefined;
}

function pressureDistribution(
  data: VersionedCreateScenariosData | undefined
): string {
  if (!data) return "—";
  const distribution = new Map<string, number>();
  data.table.rows.forEach((row) => {
    const band = row.globalPressureBand ?? "미지정";
    distribution.set(band, (distribution.get(band) ?? 0) + 1);
  });
  return [...distribution.entries()]
    .map(([band, count]) => `${band} ${count}`)
    .join(", ");
}

function lineageEvidence(
  checks: readonly DeterministicCheckResult[]
): string {
  return (
    checks.find((item) => item.id === "event-lineage-coverage")?.evidence ?? "—"
  );
}

export function OverviewComparison({
  versions,
  checks,
  complete = true
}: OverviewComparisonProps) {
  const successCount = comparisonSuccessCount(versions);
  const cell = (
    version: ApiVersion,
    render: (
      data: VersionedCreateScenariosData,
      state: VersionRunState
    ) => React.ReactNode
  ) => {
    const state = versions[version];
    const data = comparableData(state);
    return data ? render(data, state) : "—";
  };

  const rows: Array<{
    label: string;
    render: (version: ApiVersion) => React.ReactNode;
  }> = [
    {
      label: "API status",
      render: (version) => versions[version].status
    },
    {
      label: "Generation strategy",
      render: (version) =>
        cell(version, (data) => data.generationStrategy)
    },
    {
      label: "Scenario Group",
      render: (version) =>
        cell(
          version,
          (data) =>
            `#${data.scenarioGroup.scenarioGroupId} · ${data.scenarioGroup.title || "이름 없음"}`
        )
    },
    {
      label: "Event 수",
      render: (version) => cell(version, (data) => data.events.length)
    },
    {
      label: "Dimension 수",
      render: (version) =>
        cell(version, (data) => data.dimensionDefinitions.length)
    },
    {
      label: "Scenario 수",
      render: (version) => cell(version, (data) => data.table.rows.length)
    },
    {
      label: "baseline / floor / ceiling / mixed",
      render: (version) =>
        cell(version, (data) => {
          const counts = countScenarioRoles(data);
          return `${counts.baseline} / ${counts.floor} / ${counts.ceiling} / ${counts.mixed}`;
        })
    },
    {
      label: "Pressure band 분포",
      render: (version) =>
        cell(version, (data) => (
          <>
            <strong className="metric-label">Global LNG pressure</strong>
            {pressureDistribution(data)}
          </>
        ))
    },
    {
      label: "Probability 합계",
      render: (version) =>
        cell(version, (data) => scenarioProbabilitySum(data).sum.toFixed(4))
    },
    {
      label: "Event lineage coverage",
      render: (version) =>
        cell(version, () => lineageEvidence(checks[version]))
    },
    {
      label: "Diagnostics coverage",
      render: (version) =>
        cell(version, (data) => data.generationDiagnostics.coverageStatus ?? "—")
    },
    {
      label: "Excluded candidate / dimension",
      render: (version) =>
        cell(
          version,
          (data) =>
            `${data.generationDiagnostics.excludedCandidates.length} / ${data.generationDiagnostics.excludedDimensions.length}`
        )
    },
    {
      label: "Unsupported lever",
      render: (version) =>
        cell(
          version,
          (data) => data.generationDiagnostics.unsupportedLevers.length
        )
    },
    {
      label: "Elapsed",
      render: (version) =>
        versions[version].elapsedMs === undefined
          ? "—"
          : `${versions[version].elapsedMs?.toLocaleString()} ms`
    },
    {
      label: "Token usage",
      render: (version) =>
        cell(version, (data) => totalTokens(data.usage) ?? "—")
    },
    {
      label: "결정적 검사",
      render: (version) =>
        cell(version, () => {
          const summary = summarizeChecks(checks[version]);
          return `PASS ${summary.pass} · WARN ${summary.warn} · FAIL ${summary.fail}`;
        })
    }
  ];

  return (
    <section aria-labelledby="overview-title">
      {complete && successCount < 2 && (
        <div className="callout warning comparison-unavailable" role="alert">
          <AlertTriangle aria-hidden="true" size={19} />
          <div>
            <strong>비교 판정 불가</strong>
            <p>
              비교 성공 version이 {successCount}개입니다. 성공한 version의 개별
              상세와 모든 Raw 응답은 계속 확인할 수 있습니다.
            </p>
          </div>
        </div>
      )}
      <h3 id="overview-title">Overview</h3>
      <div className="table-scroll comparison-table-scroll" tabIndex={0}>
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">항목</th>
              {VERSION_ORDER.map((version) => (
                <th scope="col" key={version}>
                  {version}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                {VERSION_ORDER.map((version) => (
                  <td key={version}>{row.render(version)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="check-detail-grid" aria-label="결정적 검사 근거">
        {VERSION_ORDER.map((version) => (
          <details key={version}>
            <summary>{version} 결정적 검사 근거</summary>
            {checks[version].length === 0 ? (
              <p className="empty-hint">아직 실행 결과가 없습니다.</p>
            ) : (
              <ul className="check-list">
                {checks[version].map((item) => (
                  <li className={`check-${item.status}`} key={item.id}>
                    <strong>
                      {item.status.toUpperCase()} · {item.label}
                    </strong>
                    <span>{item.evidence}</span>
                  </li>
                ))}
              </ul>
            )}
          </details>
        ))}
      </div>
    </section>
  );
}
