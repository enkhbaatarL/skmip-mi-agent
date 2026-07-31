import type { ApiVersion } from "../../domain/apiTypes";
import { JsonViewer } from "../evidence/JsonViewer";
import {
  VERSION_ORDER,
  type VersionRunState
} from "./types";

interface DiagnosticsComparisonProps {
  versions: Record<ApiVersion, VersionRunState>;
}

function stringList(values: readonly string[]): string {
  return values.length ? values.join(", ") : "없음";
}

export function DiagnosticsComparison({
  versions
}: DiagnosticsComparisonProps) {
  return (
    <section aria-labelledby="diagnostics-title">
      <h3 id="diagnostics-title">Generation Diagnostics</h3>
      <div className="version-detail-grid">
        {VERSION_ORDER.map((version) => {
          const data =
            versions[version].status === "success"
              ? versions[version].response?.data
              : undefined;
          if (!data) {
            return (
              <article className="detail-column" key={version}>
                <h4>{version}</h4>
                <p className="empty-hint">성공한 diagnostics가 없습니다.</p>
              </article>
            );
          }
          const diagnostics = data.generationDiagnostics;
          return (
            <article className="detail-column diagnostics-column" key={version}>
              <h4>{version}</h4>
              <dl className="diagnostic-summary">
                <div>
                  <dt>Coverage status</dt>
                  <dd>{diagnostics.coverageStatus ?? "—"}</dd>
                </div>
                <div>
                  <dt>Target pressure bands</dt>
                  <dd>{stringList(diagnostics.targetPressureBands)}</dd>
                </div>
                <div>
                  <dt>Covered dimensions</dt>
                  <dd>{stringList(diagnostics.coveredDimensions)}</dd>
                </div>
                <div>
                  <dt>Uncovered dimensions</dt>
                  <dd>{stringList(diagnostics.uncoveredDimensions)}</dd>
                </div>
                {version === "v4" && (
                  <>
                    <div>
                      <dt>Impact catalog version</dt>
                      <dd>{diagnostics.impactCatalogVersion ?? "—"}</dd>
                    </div>
                    <div>
                      <dt>Unsupported levers</dt>
                      <dd>{stringList(diagnostics.unsupportedLevers)}</dd>
                    </div>
                  </>
                )}
              </dl>

              <details className="diagnostic-section">
                <summary>
                  Excluded candidates · {diagnostics.excludedCandidates.length}
                </summary>
                {diagnostics.excludedCandidates.length ? (
                  <ul className="compact-list">
                    {diagnostics.excludedCandidates.map((candidate, index) => (
                      <li
                        key={`${candidate.globalPressureBand}-${candidate.reasonCode}-${index}`}
                      >
                        <strong>{candidate.globalPressureBand}</strong> ·{" "}
                        {candidate.reasonCode}: {candidate.reason}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-hint">없음</p>
                )}
              </details>
              <JsonViewer
                value={diagnostics.excludedDimensions}
                label={`Excluded dimensions · ${diagnostics.excludedDimensions.length}`}
                defaultOpen={false}
              />
              <JsonViewer
                value={diagnostics.eventImpactFacts}
                label={`Event impact facts · ${diagnostics.eventImpactFacts.length}`}
                defaultOpen={false}
              />
              <JsonViewer
                value={diagnostics.eventInteractions}
                label={`Event interactions · ${diagnostics.eventInteractions.length}`}
                defaultOpen={false}
              />
              {version === "v4" && (
                <JsonViewer
                  value={diagnostics.unsupportedLeverDetails}
                  label={`Unsupported lever details · ${diagnostics.unsupportedLeverDetails.length}`}
                  defaultOpen={false}
                />
              )}
              <JsonViewer
                value={diagnostics}
                label={`${version} diagnostics raw JSON`}
                defaultOpen={false}
              />
            </article>
          );
        })}
      </div>
    </section>
  );
}
