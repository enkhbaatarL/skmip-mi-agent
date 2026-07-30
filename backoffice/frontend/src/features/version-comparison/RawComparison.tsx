import type { ApiVersion } from "../../domain/apiTypes";
import { JsonViewer } from "../evidence/JsonViewer";
import {
  VERSION_ORDER,
  type VersionRunState
} from "./types";

interface RawComparisonProps {
  versions: Record<ApiVersion, VersionRunState>;
}

export function RawComparison({ versions }: RawComparisonProps) {
  return (
    <section aria-labelledby="raw-comparison-title">
      <h3 id="raw-comparison-title">Raw request / response</h3>
      <p className="comparison-help">
        무결성 불일치나 API failure도 숨기지 않고 요청된 version 영역에 원본 그대로
        보존합니다.
      </p>
      <div className="version-detail-grid raw-version-grid">
        {VERSION_ORDER.map((version) => {
          const state = versions[version];
          return (
            <article className="detail-column" key={version}>
              <h4>
                {version} · {state.status}
              </h4>
              {state.integrityIssues.length > 0 && (
                <div className="callout error compact-callout" role="alert">
                  {state.integrityIssues.map((issue) => (
                    <span key={issue}>{issue}</span>
                  ))}
                </div>
              )}
              <JsonViewer
                value={state.request}
                label={`${version} request`}
                defaultOpen
              />
              <JsonViewer
                value={state.response}
                label={`${version} parsed response`}
                defaultOpen={false}
              />
              <JsonViewer
                value={state.call?.rawText}
                label={`${version} raw response text`}
                defaultOpen={false}
              />
            </article>
          );
        })}
      </div>
    </section>
  );
}
