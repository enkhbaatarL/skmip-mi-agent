import type {
  PresentationMarkdownSection,
  ScenarioGroupPresentationResponse
} from "../../domain/apiTypes";

interface ScenarioGroupPresentationProps {
  presentation: ScenarioGroupPresentationResponse;
}

function MarkdownSection({
  title,
  section
}: {
  title: string;
  section: PresentationMarkdownSection;
}) {
  return (
    <section aria-label={title} data-status={section.status}>
      <header>
        <h3>{title}</h3>
        <span>{section.status}</span>
        <span>{section.evidenceLevel}</span>
      </header>
      {section.markdown ? (
        <pre className="presentation-markdown">{section.markdown}</pre>
      ) : (
        <p className="empty-hint">아직 제공할 내용이 없습니다.</p>
      )}
    </section>
  );
}

export function ScenarioGroupPresentation({
  presentation
}: ScenarioGroupPresentationProps) {
  const design = presentation.sections.scenarioDesign;
  return (
    <div className="scenario-group-presentation">
      {presentation.warnings.length > 0 && (
        <ul aria-label="Presentation warnings" className="compact-list">
          {presentation.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      <MarkdownSection
        title="Event 분석"
        section={presentation.sections.eventAnalysis}
      />

      <section aria-label="Scenario 설계" data-status={design.status}>
        <header>
          <h3>Scenario 설계</h3>
          <span>{design.status}</span>
          <span>{design.evidenceLevel}</span>
        </header>
        <h4>Dimension definitions</h4>
        {design.dimensionDefinitions.items.length > 0 ? (
          <div className="dimension-list">
            {design.dimensionDefinitions.items.map((dimension) => (
              <article className="dimension-item" key={dimension.dimensionId}>
                <h5>{dimension.label}</h5>
                <p>{dimension.description ?? "설명 없음"}</p>
                <ul className="compact-list">
                  {dimension.values.map((value) => (
                    <li key={value.valueId}>
                      {value.label}
                      {value.rationale ? ` — ${value.rationale}` : ""}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-hint">준비된 Dimension이 없습니다.</p>
        )}

        <h4>Scenario dimension table</h4>
        <div className="table-scroll" tabIndex={0}>
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Scenario</th>
                {design.scenarioTable.headers.map((header) => (
                  <th key={header.key}>{header.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {design.scenarioTable.rows.map((row) => (
                <tr key={row.scenarioId ?? `${row.displayOrder}-${row.title}`}>
                  <th>{row.title}</th>
                  {design.scenarioTable.headers.map((header) => (
                    <td key={header.key}>{String(row.cells[header.key] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <MarkdownSection
        title="Ceiling/Floor/Mixed 선택 근거"
        section={presentation.sections.roleSelectionRationale}
      />
    </div>
  );
}
