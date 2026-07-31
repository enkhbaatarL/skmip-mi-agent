import type {
  ApiVersion,
  VersionedCreateScenariosData
} from "./apiTypes";

export type DeterministicCheckStatus = "pass" | "warn" | "fail";

export interface DeterministicCheckResult {
  id: string;
  label: string;
  status: DeterministicCheckStatus;
  evidence: string;
}

export interface DeterministicCheckManifest {
  miEventIds: readonly number[];
}

export interface ScenarioRoleCounts {
  baseline: number;
  floor: number;
  ceiling: number;
  mixed: number;
}

const DIMENSION_RANGES: Record<ApiVersion, readonly [number, number]> = {
  v2: [5, 8],
  v3: [4, 7],
  v4: [3, 6]
};

function check(
  id: string,
  label: string,
  status: DeterministicCheckStatus,
  evidence: string
): DeterministicCheckResult {
  return { id, label, status, evidence };
}

export function countScenarioRoles(
  data: VersionedCreateScenariosData | undefined
): ScenarioRoleCounts {
  const rows = data?.table.rows ?? [];
  return {
    baseline: rows.filter((row) => row.baselineYn === "Y").length,
    // Backend scenarioRole is deliberately open-ended. Only the exact role labels
    // currently emitted by the pipeline are classified; casing is not normalized.
    floor: rows.filter((row) => row.scenarioRole === "floor").length,
    ceiling: rows.filter((row) => row.scenarioRole === "ceiling").length,
    mixed: rows.filter((row) => row.scenarioRole === "mixed").length
  };
}

export function scenarioProbabilitySum(
  data: VersionedCreateScenariosData | undefined
): { sum: number; present: number; total: number; invalid: number } {
  const rows = data?.table.rows ?? [];
  let sum = 0;
  let present = 0;
  let invalid = 0;
  for (const row of rows) {
    const raw = row.probabilityScore ?? row.metrics?.probabilityScore;
    if (raw == null) continue;
    present += 1;
    const value = Number(raw);
    if (!Number.isFinite(value) || value < 0 || value > 100) {
      invalid += 1;
      continue;
    }
    sum += value;
  }
  return { sum, present, total: rows.length, invalid };
}

function unavailableChecks(
  version: ApiVersion
): DeterministicCheckResult[] {
  const base = [
    ["scenario-count", "Scenario 수 3~5"],
    ["baseline-count", "baseline 정확히 1개"],
    ["floor-count", "floor 정확히 1개"],
    ["ceiling-count", "ceiling 정확히 1개"],
    ["mixed-count", "mixed 최소 1개"],
    ["unique-scenario-combination", "Scenario dimension 조합 중복 없음"],
    ["unique-pressure-band", "pressure band 중복 없음"],
    ["probability-sum", "probability 합계"],
    ["dimension-count", `${version} dimension 수 범위`],
    ["dimension-identifiers", "dimension 식별자와 Scenario cell 정합성"],
    ["event-lineage-coverage", "전체 입력 Event lineage coverage"]
  ].map(([id, label]) =>
    check(id, label, "fail", "비교 가능한 응답 데이터가 없습니다.")
  );
  return base;
}

export function runDeterministicChecks(
  version: ApiVersion,
  data: VersionedCreateScenariosData | undefined,
  manifest: DeterministicCheckManifest
): DeterministicCheckResult[] {
  if (!data) return unavailableChecks(version);

  const rows = data.table.rows;
  const roleCounts = countScenarioRoles(data);
  const results: DeterministicCheckResult[] = [];

  results.push(
    check(
      "scenario-count",
      "Scenario 수 3~5",
      rows.length >= 3 && rows.length <= 5 ? "pass" : "fail",
      `실제 Scenario ${rows.length}개`
    ),
    check(
      "baseline-count",
      "baseline 정확히 1개",
      roleCounts.baseline === 1 ? "pass" : "fail",
      `baselineYn="Y" ${roleCounts.baseline}개`
    ),
    check(
      "floor-count",
      "floor 정확히 1개",
      roleCounts.floor === 1 ? "pass" : "fail",
      `scenarioRole="floor" ${roleCounts.floor}개`
    ),
    check(
      "ceiling-count",
      "ceiling 정확히 1개",
      roleCounts.ceiling === 1 ? "pass" : "fail",
      `scenarioRole="ceiling" ${roleCounts.ceiling}개`
    ),
    check(
      "mixed-count",
      "mixed 최소 1개",
      roleCounts.mixed >= 1 ? "pass" : "fail",
      `scenarioRole="mixed" ${roleCounts.mixed}개`
    )
  );

  const scenarioCombinations = new Map<string, number[]>();
  for (const row of rows) {
    const combination = JSON.stringify(
      Object.fromEntries(
        Object.entries(row.cells).sort(([left], [right]) =>
          left.localeCompare(right)
        )
      )
    );
    const orders = scenarioCombinations.get(combination) ?? [];
    orders.push(row.displayOrder);
    scenarioCombinations.set(combination, orders);
  }
  const duplicateScenarioCombinations = [...scenarioCombinations.values()]
    .filter((orders) => orders.length > 1)
    .map((orders) => `displayOrder [${orders.join(", ")}]`);
  results.push(
    check(
      "unique-scenario-combination",
      "Scenario dimension 조합 중복 없음",
      duplicateScenarioCombinations.length > 0 ? "fail" : "pass",
      duplicateScenarioCombinations.length > 0
        ? `동일 cells 조합: ${duplicateScenarioCombinations.join("; ")}`
        : `${scenarioCombinations.size}개 cells 조합 모두 고유`
    )
  );

  const pressureBands = new Map<string, number[]>();
  let missingPressureBands = 0;
  for (const row of rows) {
    if (!row.globalPressureBand) {
      missingPressureBands += 1;
      continue;
    }
    const orders = pressureBands.get(row.globalPressureBand) ?? [];
    orders.push(row.displayOrder);
    pressureBands.set(row.globalPressureBand, orders);
  }
  const duplicatePressureBands = [...pressureBands.entries()]
    .filter(([, orders]) => orders.length > 1)
    .map(([band, orders]) => `${band} [${orders.join(", ")}]`);
  results.push(
    check(
      "unique-pressure-band",
      "pressure band 중복 없음",
      duplicatePressureBands.length > 0
        ? "fail"
        : missingPressureBands > 0
          ? "warn"
          : "pass",
      duplicatePressureBands.length > 0
        ? `중복: ${duplicatePressureBands.join("; ")}`
        : missingPressureBands > 0
          ? `중복 없음, pressure band 누락 ${missingPressureBands}개`
          : `${pressureBands.size}개 pressure band 모두 고유`
    )
  );

  const probability = scenarioProbabilitySum(data);
  // Persistence normalizes active scenario probability scores to 100. A 0.01
  // tolerance only absorbs decimal serialization/rounding, not domain drift.
  const probabilityDifference = Math.abs(probability.sum - 100);
  results.push(
    check(
      "probability-sum",
      "probability 합계",
      probability.invalid > 0
        ? "fail"
        : probability.present !== probability.total
          ? "warn"
          : probabilityDifference <= 0.01
            ? "pass"
            : "warn",
      `합계 ${probability.sum.toFixed(4)}, 값 존재 ${probability.present}/${probability.total}, 유효 범위 밖 ${probability.invalid}개, 기대 합계 100±0.01`
    )
  );

  const [minimumDimensions, maximumDimensions] = DIMENSION_RANGES[version];
  const dimensionCount = data.dimensionDefinitions.length;
  results.push(
    check(
      "dimension-count",
      `${version} dimension 수 ${minimumDimensions}~${maximumDimensions}`,
      dimensionCount >= minimumDimensions && dimensionCount <= maximumDimensions
        ? "pass"
        : "fail",
      `실제 dimension ${dimensionCount}개`
    )
  );

  const dimensionIds = data.dimensionDefinitions.map(
    (dimension) => dimension.dimensionId
  );
  const dimensionIdSet = new Set(dimensionIds);
  const duplicateDimensionIds = dimensionIds.filter(
    (dimensionId, index) => dimensionIds.indexOf(dimensionId) !== index
  );
  const headerIds = data.table.headers.map((header) => header.key);
  const missingHeaders = dimensionIds.filter(
    (dimensionId) => !headerIds.includes(dimensionId)
  );
  const extraHeaders = headerIds.filter(
    (headerId) => !dimensionIdSet.has(headerId)
  );
  const rowCellIssues = rows.flatMap((row) => {
    const cellIds = Object.keys(row.cells);
    const missing = dimensionIds.filter(
      (dimensionId) => !cellIds.includes(dimensionId)
    );
    const extra = cellIds.filter((cellId) => !dimensionIdSet.has(cellId));
    return missing.length || extra.length
      ? [
          `#${row.displayOrder} 누락 [${missing.join(", ")}] 추가 [${extra.join(", ")}]`
        ]
      : [];
  });
  const identifierIssueCount =
    duplicateDimensionIds.length +
    missingHeaders.length +
    extraHeaders.length +
    rowCellIssues.length;
  results.push(
    check(
      "dimension-identifiers",
      "dimension 식별자와 Scenario cell 정합성",
      identifierIssueCount > 0 ? "fail" : "pass",
      identifierIssueCount > 0
        ? `중복 dimension [${[...new Set(duplicateDimensionIds)].join(", ")}], header 누락 [${missingHeaders.join(", ")}], header 추가 [${extraHeaders.join(", ")}]${rowCellIssues.length ? `, ${rowCellIssues.join("; ")}` : ""}`
        : `${dimensionIds.length}개 definition/header와 ${rows.length}개 Scenario cell key 일치`
    )
  );

  const lineageIds = new Set<number>();
  for (const dimension of data.dimensionDefinitions) {
    dimension.sourceEventIds.forEach((eventId) => lineageIds.add(eventId));
    dimension.sourceRefs.forEach((source) => lineageIds.add(source.eventId));
    dimension.values.forEach((value) =>
      value.sourceAssignments.forEach((source) =>
        lineageIds.add(source.eventId)
      )
    );
  }
  const missingIds = manifest.miEventIds.filter(
    (eventId) => !lineageIds.has(eventId)
  );
  const extraIds = [...lineageIds].filter(
    (eventId) => !manifest.miEventIds.includes(eventId)
  );
  results.push(
    check(
      "event-lineage-coverage",
      "전체 입력 Event lineage coverage",
      missingIds.length > 0 ? "fail" : extraIds.length > 0 ? "warn" : "pass",
      `manifest [${manifest.miEventIds.join(", ")}], lineage [${[...lineageIds].join(", ")}], 누락 [${missingIds.join(", ")}], 추가 [${extraIds.join(", ")}]`
    )
  );

  return results;
}

export function summarizeChecks(
  checks: readonly DeterministicCheckResult[]
): Record<DeterministicCheckStatus, number> {
  return checks.reduce(
    (summary, item) => {
      summary[item.status] += 1;
      return summary;
    },
    { pass: 0, warn: 0, fail: 0 }
  );
}
