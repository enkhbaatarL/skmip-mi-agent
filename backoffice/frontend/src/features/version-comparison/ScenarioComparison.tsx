import { useState } from "react";
import type {
  ApiVersion,
  ScenarioTableRow,
  VersionedCreateScenariosData
} from "../../domain/apiTypes";
import {
  VERSION_ORDER,
  type ComparisonManifest,
  type VersionRunState
} from "./types";

interface ScenarioComparisonProps {
  versions: Record<ApiVersion, VersionRunState>;
  manifest: ComparisonManifest;
}

export function sortScenarioRows(
  rows: readonly ScenarioTableRow[]
): ScenarioTableRow[] {
  const rank = (row: ScenarioTableRow) => {
    if (row.scenarioRole === "floor") return 0;
    if (row.scenarioRole === "ceiling") return 3;
    if (row.baselineYn === "Y") return 2;
    return 1;
  };
  return [...rows].sort(
    (left, right) =>
      rank(left) - rank(right) || left.displayOrder - right.displayOrder
  );
}

const PRESSURE_RANK: Record<string, number> = {
  strong_bearish: 0,
  bearish: 1,
  balanced: 2,
  bullish: 3,
  strong_bullish: 4
};

export function scenarioAlignmentKey(row: ScenarioTableRow): string {
  if (row.globalPressureBand) return `pressure:${row.globalPressureBand}`;
  if (row.scenarioRole) return `role:${row.scenarioRole}`;
  return `order:${row.displayOrder}`;
}

function indexRows(
  rows: readonly ScenarioTableRow[]
): Map<string, ScenarioTableRow> {
  const indexed = new Map<string, ScenarioTableRow>();
  const occurrences = new Map<string, number>();
  for (const row of rows) {
    const baseKey = scenarioAlignmentKey(row);
    const occurrence = (occurrences.get(baseKey) ?? 0) + 1;
    occurrences.set(baseKey, occurrence);
    indexed.set(
      occurrence === 1 ? baseKey : `${baseKey}::${occurrence}`,
      row
    );
  }
  return indexed;
}

function alignmentRank(
  key: string,
  row: ScenarioTableRow | undefined
): readonly [number, number, string] {
  const roleRank =
    row?.scenarioRole === "floor"
      ? 0
      : row?.scenarioRole === "ceiling"
        ? 3
        : row?.baselineYn === "Y"
          ? 2
          : 1;
  const pressureBand = key.startsWith("pressure:")
    ? key.slice("pressure:".length).split("::")[0]
    : row?.globalPressureBand ?? "";
  return [roleRank, PRESSURE_RANK[pressureBand] ?? 99, key];
}

function scenarioEventCoverage(
  row: ScenarioTableRow,
  data: VersionedCreateScenariosData,
  manifest: ComparisonManifest
): string {
  const ids = new Set<number>();
  for (const dimension of data.dimensionDefinitions) {
    if (
      Object.prototype.hasOwnProperty.call(row.cells, dimension.dimensionId) &&
      row.cells[dimension.dimensionId] != null
    ) {
      dimension.sourceEventIds.forEach((eventId) => ids.add(eventId));
    }
  }
  const ordered = manifest.miEventIds.filter((eventId) => ids.has(eventId));
  return ordered.length > 0 ? ordered.map((id) => `#${id}`).join(", ") : "확인 불가";
}

export function ScenarioComparison({
  versions,
  manifest
}: ScenarioComparisonProps) {
  const [mobileVersion, setMobileVersion] = useState<ApiVersion>("v2");
  const successfulData = Object.fromEntries(
    VERSION_ORDER.map((version) => [
      version,
      versions[version].status === "success"
        ? versions[version].response?.data
        : undefined
    ])
  ) as Record<ApiVersion, VersionedCreateScenariosData | undefined>;
  const orderedRows = Object.fromEntries(
    VERSION_ORDER.map((version) => [
      version,
      sortScenarioRows(successfulData[version]?.table.rows ?? [])
    ])
  ) as Record<ApiVersion, ScenarioTableRow[]>;
  const indexedRows = Object.fromEntries(
    VERSION_ORDER.map((version) => [version, indexRows(orderedRows[version])])
  ) as Record<ApiVersion, Map<string, ScenarioTableRow>>;
  const alignmentKeys = [
    ...new Set(
      VERSION_ORDER.flatMap((version) => [...indexedRows[version].keys()])
    )
  ].sort((left, right) => {
    const leftRow = VERSION_ORDER
      .map((version) => indexedRows[version].get(left))
      .find(Boolean);
    const rightRow = VERSION_ORDER
      .map((version) => indexedRows[version].get(right))
      .find(Boolean);
    const leftRank = alignmentRank(left, leftRow);
    const rightRank = alignmentRank(right, rightRow);
    return (
      leftRank[0] - rightRank[0] ||
      leftRank[1] - rightRank[1] ||
      leftRank[2].localeCompare(rightRank[2])
    );
  });

  return (
    <section aria-labelledby="scenarios-title">
      <h3 id="scenarios-title">Scenarios</h3>
      <p className="comparison-help">
        실제 scenarioRole과 baseline marker만 사용해 floor → 내부/mixed →
        baseline → ceiling 순으로 안정 정렬합니다. pressure band의 의미 순서는
        추측하지 않습니다.
      </p>
      <div className="mobile-version-switcher" role="group" aria-label="Scenario version">
        {VERSION_ORDER.map((version) => (
          <button
            type="button"
            key={version}
            aria-pressed={mobileVersion === version}
            onClick={() => setMobileVersion(version)}
          >
            {version}
          </button>
        ))}
      </div>
      <div className="scenario-version-grid">
        {VERSION_ORDER.map((version) => {
          const data = successfulData[version];
          const excluded = data?.generationDiagnostics.excludedCandidates ?? [];
          return (
            <article
              className={`scenario-version-column ${
                mobileVersion === version ? "mobile-active" : ""
              }`}
              key={version}
            >
              <h4>
                {version} ·{" "}
                {version === "v4"
                  ? `${manifest.targetMarket} pressure`
                  : "Global LNG pressure"}
              </h4>
              {(alignmentKeys.length ? alignmentKeys : ["empty"]).map(
                (alignmentKey, index) => {
                const row = indexedRows[version].get(alignmentKey);
                if (!row || !data) {
                  const pressureBand = alignmentKey.startsWith("pressure:")
                    ? alignmentKey.slice("pressure:".length).split("::")[0]
                    : undefined;
                  const reason = excluded.find(
                    (candidate) =>
                      candidate.globalPressureBand === pressureBand
                  );
                  return (
                    <div className="scenario-empty" key={alignmentKey}>
                      <strong>생성되지 않음</strong>
                      <span>
                        {reason
                          ? `${reason.globalPressureBand}: ${reason.reason}`
                          : versions[version].error ||
                            versions[version].integrityIssues.join(" · ") ||
                            `${alignmentKey}에 대응하는 Scenario 또는 제외 사유가 없습니다.`}
                      </span>
                    </div>
                  );
                }
                const probability =
                  row.probabilityScore ?? row.metrics?.probabilityScore;
                return (
                  <details
                    className="scenario-card"
                    key={alignmentKey}
                    open={index < 2}
                  >
                    <summary>
                      <span>#{row.displayOrder}</span>
                      <strong>{row.title || "제목 없음"}</strong>
                      {row.baselineYn === "Y" && (
                        <span className="selected-marker">baseline</span>
                      )}
                    </summary>
                    <div className="scenario-card-body">
                      <p>{row.narrative || "narrative 없음"}</p>
                      <dl className="compact-definition">
                        <div>
                          <dt>Role</dt>
                          <dd>{row.scenarioRole ?? "—"}</dd>
                        </div>
                        <div>
                          <dt>Pressure band</dt>
                          <dd>{row.globalPressureBand ?? "—"}</dd>
                        </div>
                        <div>
                          <dt>Probability</dt>
                          <dd>{probability ?? "—"}</dd>
                        </div>
                        <div>
                          <dt>Event coverage</dt>
                          <dd>{scenarioEventCoverage(row, data, manifest)}</dd>
                        </div>
                      </dl>
                      <div>
                        <strong>Pressure rationale</strong>
                        <p>{row.globalPressureRationale || "근거 없음"}</p>
                      </div>
                      <div>
                        <strong>Dimension cells</strong>
                        <dl className="scenario-cells">
                          {Object.entries(row.cells).map(([key, value]) => (
                            <div key={key}>
                              <dt>{key}</dt>
                              <dd>{String(value ?? "null")}</dd>
                            </div>
                          ))}
                        </dl>
                      </div>
                    </div>
                  </details>
                );
              })}
            </article>
          );
        })}
      </div>
    </section>
  );
}
