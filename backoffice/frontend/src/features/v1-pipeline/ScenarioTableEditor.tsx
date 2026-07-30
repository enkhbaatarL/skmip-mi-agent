import { ArrowDown, ArrowUp, Plus, RotateCcw, Trash2 } from "lucide-react";
import type {
  ScenarioTable,
  ScenarioTableRow
} from "../../domain/apiTypes";

interface ScenarioTableEditorProps {
  table: ScenarioTable;
  lastServerTable: ScenarioTable;
  onChange: (table: ScenarioTable) => void;
  disabled?: boolean;
}

function normalizeRows(rows: ScenarioTableRow[]): ScenarioTableRow[] {
  return rows.map((row, index) => ({ ...row, displayOrder: index + 1 }));
}

function cloneRow(row: ScenarioTableRow): ScenarioTableRow {
  return {
    ...row,
    cells: { ...row.cells },
    ...(row.metrics ? { metrics: { ...row.metrics } } : {}),
    ...(row.signposts
      ? { signposts: row.signposts.map((signpost) => ({ ...signpost })) }
      : {})
  };
}

export function normalizeScenarioTable(table: ScenarioTable): ScenarioTable {
  return {
    headers: table.headers.map((header) => ({ ...header })),
    rows: normalizeRows(table.rows.map(cloneRow))
  };
}

export function ScenarioTableEditor({
  table,
  lastServerTable,
  onChange,
  disabled = false
}: ScenarioTableEditorProps) {
  const hasRole = table.rows.some((row) => row.scenarioRole != null);
  const hasPressure = table.rows.some(
    (row) =>
      row.globalPressureBand != null || row.globalPressureRationale != null
  );

  function updateRow(
    index: number,
    updater: (row: ScenarioTableRow) => ScenarioTableRow
  ) {
    onChange({
      ...table,
      rows: table.rows.map((row, rowIndex) =>
        rowIndex === index ? updater(cloneRow(row)) : row
      )
    });
  }

  function addRow() {
    const row: ScenarioTableRow = {
      scenarioId: null,
      displayOrder: table.rows.length + 1,
      title: "",
      narrative: null,
      cells: Object.fromEntries(table.headers.map((header) => [header.key, null])),
      metrics: { probabilityScore: null, probabilityDelta: 0 },
      baselineYn: "N",
      signposts: []
    };
    onChange({ ...table, rows: [...table.rows, row] });
  }

  function deleteRow(index: number) {
    onChange({
      ...table,
      rows: normalizeRows(table.rows.filter((_, rowIndex) => rowIndex !== index))
    });
  }

  function moveRow(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= table.rows.length) return;
    const rows = table.rows.map(cloneRow);
    [rows[index], rows[target]] = [rows[target], rows[index]];
    onChange({ ...table, rows: normalizeRows(rows) });
  }

  function resetRow(index: number) {
    const current = table.rows[index];
    const serverRow =
      current.scenarioId == null
        ? undefined
        : lastServerTable.rows.find(
            (row) => row.scenarioId === current.scenarioId
          );
    if (serverRow) {
      updateRow(index, () => ({
        ...cloneRow(serverRow),
        displayOrder: index + 1
      }));
      return;
    }
    updateRow(index, (row) => ({
      ...row,
      title: "",
      narrative: null,
      cells: Object.fromEntries(
        table.headers.map((header) => [header.key, null])
      ),
      metrics: { ...(row.metrics ?? {}), probabilityScore: null },
      baselineYn: "N"
    }));
  }

  function setBaseline(index: number) {
    onChange({
      ...table,
      rows: table.rows.map((row, rowIndex) => ({
        ...row,
        baselineYn: rowIndex === index ? "Y" : "N"
      }))
    });
  }

  return (
    <section className="scenario-editor" aria-labelledby="scenario-editor-title">
      <div className="section-heading compact-heading">
        <div>
          <h3 id="scenario-editor-title">Editable Scenario Table</h3>
          <p>가로로 스크롤해 모든 dimension을 확인할 수 있습니다.</p>
        </div>
        <div className="editor-actions">
          <button
            className="button secondary compact"
            type="button"
            disabled={disabled}
            onClick={addRow}
          >
            <Plus aria-hidden="true" size={16} />
            행 추가
          </button>
          <button
            className="button quiet compact"
            type="button"
            disabled={disabled}
            onClick={() => onChange(normalizeScenarioTable(lastServerTable))}
          >
            <RotateCcw aria-hidden="true" size={16} />
            전체 Reset
          </button>
        </div>
      </div>

      <div
        className="table-scroll scenario-table-scroll"
        tabIndex={0}
        aria-label="편집 가능한 Scenario table, 가로 스크롤 가능"
      >
        <table className="scenario-table">
          <thead>
            <tr>
              <th scope="col">순서</th>
              <th scope="col">Baseline</th>
              <th scope="col">Title</th>
              <th scope="col">Narrative</th>
              <th scope="col">Probability</th>
              {hasRole && <th scope="col">Role</th>}
              {hasPressure && <th scope="col">Pressure</th>}
              {table.headers.map((header) => (
                <th scope="col" key={header.key}>
                  {header.label}
                  <small>{header.key}</small>
                </th>
              ))}
              <th scope="col">행 작업</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, index) => (
              <tr key={`${row.scenarioId ?? "new"}-${index}`}>
                <td>
                  <strong>{row.displayOrder}</strong>
                  <div className="row-order-actions">
                    <button
                      className="icon-button small"
                      type="button"
                      aria-label={`${row.displayOrder}번 Scenario 위로 이동`}
                      disabled={disabled || index === 0}
                      onClick={() => moveRow(index, -1)}
                    >
                      <ArrowUp aria-hidden="true" size={14} />
                    </button>
                    <button
                      className="icon-button small"
                      type="button"
                      aria-label={`${row.displayOrder}번 Scenario 아래로 이동`}
                      disabled={disabled || index === table.rows.length - 1}
                      onClick={() => moveRow(index, 1)}
                    >
                      <ArrowDown aria-hidden="true" size={14} />
                    </button>
                  </div>
                </td>
                <td>
                  <input
                    type="radio"
                    name="scenario-baseline"
                    aria-label={`${row.displayOrder}번 Scenario를 baseline으로 지정`}
                    checked={row.baselineYn === "Y"}
                    disabled={disabled}
                    onChange={() => setBaseline(index)}
                  />
                </td>
                <td>
                  <textarea
                    aria-label={`${row.displayOrder}번 Scenario title`}
                    value={row.title}
                    disabled={disabled}
                    onChange={(event) =>
                      updateRow(index, (current) => ({
                        ...current,
                        title: event.currentTarget.value
                      }))
                    }
                  />
                  <small>ID {row.scenarioId ?? "신규"}</small>
                </td>
                <td>
                  <textarea
                    aria-label={`${row.displayOrder}번 Scenario narrative`}
                    value={row.narrative ?? ""}
                    disabled={disabled}
                    onChange={(event) =>
                      updateRow(index, (current) => ({
                        ...current,
                        narrative: event.currentTarget.value
                      }))
                    }
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="0.01"
                    aria-label={`${row.displayOrder}번 Scenario probability`}
                    value={
                      row.metrics?.probabilityScore ??
                      row.probabilityScore ??
                      ""
                    }
                    disabled={disabled}
                    onChange={(event) =>
                      updateRow(index, (current) => ({
                        ...current,
                        metrics: {
                          ...(current.metrics ?? {}),
                          probabilityScore:
                            event.currentTarget.value === ""
                              ? null
                              : Number(event.currentTarget.value)
                        }
                      }))
                    }
                  />
                </td>
                {hasRole && <td>{row.scenarioRole ?? "—"}</td>}
                {hasPressure && (
                  <td>
                    {row.globalPressureBand ?? "—"}
                    {row.globalPressureRationale && (
                      <small>{row.globalPressureRationale}</small>
                    )}
                  </td>
                )}
                {table.headers.map((header) => (
                  <td key={header.key}>
                    <textarea
                      aria-label={`${row.displayOrder}번 ${header.label}`}
                      value={String(row.cells[header.key] ?? "")}
                      disabled={disabled}
                      onChange={(event) =>
                        updateRow(index, (current) => ({
                          ...current,
                          cells: {
                            ...current.cells,
                            [header.key]: event.currentTarget.value
                          }
                        }))
                      }
                    />
                    {row.cells[header.key] === null && (
                      <small>미입력 값은 null로 전송</small>
                    )}
                  </td>
                ))}
                <td>
                  <div className="row-actions">
                    <button
                      className="icon-button small"
                      type="button"
                      aria-label={`${row.displayOrder}번 Scenario 원본값으로 reset`}
                      disabled={disabled}
                      onClick={() => resetRow(index)}
                    >
                      <RotateCcw aria-hidden="true" size={14} />
                    </button>
                    <button
                      className="icon-button small danger"
                      type="button"
                      aria-label={`${row.displayOrder}번 Scenario 삭제`}
                      disabled={disabled || table.rows.length === 1}
                      onClick={() => deleteRow(index)}
                    >
                      <Trash2 aria-hidden="true" size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
