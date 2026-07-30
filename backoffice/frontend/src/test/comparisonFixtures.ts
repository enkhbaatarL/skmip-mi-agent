import type { ApiCallResult } from "../domain/apiCall";
import type {
  ApiVersion,
  DimensionDefinition,
  GenerationStrategy,
  TargetMarket,
  VersionedCreateScenariosData,
  VersionedCreateScenariosOut
} from "../domain/apiTypes";
import type { ComparisonManifest } from "../features/version-comparison/types";
import { VERSION_STRATEGIES } from "../features/version-comparison/types";

export function makeManifest(
  overrides: Partial<ComparisonManifest> = {}
): ComparisonManifest {
  return {
    runId: `workspace-${Math.random().toString(16).slice(2)}`,
    createdAt: "2026-07-30T00:00:00.000Z",
    agentBaseUrl: "http://127.0.0.1:8001",
    userId: 10001,
    timeoutMs: 10_000,
    comparisonRunId: "multi-event-test",
    miEventIds: [101, 202],
    selectedEvents: [],
    targetMarket: "JKM",
    targetMarketReason: "test",
    ...overrides
  };
}

function makeDimension(
  index: number,
  sourceEventIds: number[]
): DimensionDefinition {
  const eventId = sourceEventIds[index % sourceEventIds.length];
  return {
    dimensionId: `e${eventId}__dimension_${index + 1}`,
    label: `Dimension ${index + 1}`,
    description: `Description ${index + 1}`,
    required: false,
    displayOrder: index + 1,
    dimensionType: "magnitude",
    valueKind: "categorical",
    unit: null,
    sourceEventIds: [eventId],
    leverRefs: [],
    modelSupportStatus: "full",
    sourceRefs: [
      {
        eventId,
        eventTypeL2Id: 12,
        dimKey: `dimension_${index + 1}`,
        value: null,
        sourceType: "event_fact",
        assumptionYn: "N",
        rationale: "fixture"
      }
    ],
    values: [
      {
        valueId: `value-${index + 1}`,
        label: `Value ${index + 1}`,
        globalPressureContribution: null,
        sourceAssignments: []
      }
    ]
  };
}

export function makeVersionData(
  version: ApiVersion = "v2",
  options: {
    comparisonRunId?: string;
    eventIds?: number[];
    dimensionCount?: number;
    targetMarket?: TargetMarket | null;
    generationStrategy?: GenerationStrategy;
  } = {}
): VersionedCreateScenariosData {
  const eventIds = options.eventIds ?? [101, 202];
  const dimensionCount =
    options.dimensionCount ?? (version === "v2" ? 5 : version === "v3" ? 4 : 3);
  const dimensions = Array.from({ length: dimensionCount }, (_, index) =>
    makeDimension(index, eventIds)
  );
  const headers = dimensions.map((dimension) => ({
    key: dimension.dimensionId,
    label: dimension.label,
    displayOrder: dimension.displayOrder
  }));
  const cells = (scenario: string) =>
    Object.fromEntries(
      dimensions.map((dimension) => [
        dimension.dimensionId,
        `${scenario}-${dimension.dimensionId}`
      ])
    );

  return {
    apiVersion: version,
    generationStrategy:
      options.generationStrategy ?? VERSION_STRATEGIES[version],
    comparisonRunId: options.comparisonRunId ?? "multi-event-test",
    targetMarket:
      options.targetMarket === undefined
        ? version === "v4"
          ? "JKM"
          : null
        : options.targetMarket,
    impactCatalogVersion: version === "v4" ? "catalog-1" : null,
    scenarioGroup: {
      scenarioGroupId: Number(version.slice(1)),
      miEventId: null,
      eventTypeL2Id: null,
      title: `${version} fixture`,
      summary: null,
      description: null,
      dimensionSelected: dimensions.map((item) => item.dimensionId),
      scenarioCount: 4,
      status: "creating",
      stage: "ready",
      apiVersion: version,
      generationStrategy: VERSION_STRATEGIES[version],
      comparisonRunId: options.comparisonRunId ?? "multi-event-test",
      targetMarket: version === "v4" ? "JKM" : null,
      impactCatalogVersion: version === "v4" ? "catalog-1" : null,
      impactCatalogChecksum: null,
      templateChecksum: null,
      parameterMappingReady: false,
      dimensionDefinitions: []
    },
    events: eventIds.map((miEventId) => ({
      miEventId,
      eventTypeL2Id: 12,
      eventTitleKo: `Event ${miEventId}`,
      oneLineSummary: "",
      detailAnalysis: "",
      keyBullets: [],
      eventType: {},
      sourceMiRecordIds: [],
      createdAt: "",
      updatedAt: "",
      language: "ko",
      occurredAt: "",
      tags: []
    })),
    dimensionDefinitions: dimensions,
    table: {
      headers,
      rows: [
        {
          scenarioId: 1,
          displayOrder: 1,
          title: "Floor",
          narrative: "floor",
          cells: cells("floor"),
          metrics: { probabilityScore: 25, probabilityDelta: 0 },
          baselineYn: "N",
          scenarioRole: "floor",
          globalPressureBand: "strong_bearish",
          probabilityScore: 25,
          globalPressureRationale: "fixture",
          signposts: []
        },
        {
          scenarioId: 2,
          displayOrder: 2,
          title: "Mixed",
          narrative: "mixed",
          cells: cells("mixed"),
          metrics: { probabilityScore: 25, probabilityDelta: 0 },
          baselineYn: "N",
          scenarioRole: "mixed",
          globalPressureBand: "bearish",
          probabilityScore: 25,
          globalPressureRationale: "fixture",
          signposts: []
        },
        {
          scenarioId: 3,
          displayOrder: 3,
          title: "Baseline",
          narrative: "baseline",
          cells: cells("baseline"),
          metrics: { probabilityScore: 25, probabilityDelta: 0 },
          baselineYn: "Y",
          scenarioRole: "mixed",
          globalPressureBand: "balanced",
          probabilityScore: 25,
          globalPressureRationale: "fixture",
          signposts: []
        },
        {
          scenarioId: 4,
          displayOrder: 4,
          title: "Ceiling",
          narrative: "ceiling",
          cells: cells("ceiling"),
          metrics: { probabilityScore: 25, probabilityDelta: 0 },
          baselineYn: "N",
          scenarioRole: "ceiling",
          globalPressureBand: "strong_bullish",
          probabilityScore: 25,
          globalPressureRationale: "fixture",
          signposts: []
        }
      ]
    },
    generationDiagnostics: {
      targetPressureBands: [
        "strong_bullish",
        "bullish",
        "balanced",
        "bearish",
        "strong_bearish"
      ],
      excludedCandidates: [],
      excludedDimensions: [],
      targetMarket: version === "v4" ? "JKM" : null,
      impactCatalogVersion: version === "v4" ? "catalog-1" : null,
      coveredDimensions: dimensions.map((item) => item.dimensionId),
      uncoveredDimensions: [],
      unsupportedLevers: [],
      unsupportedLeverDetails: [],
      coverageStatus: "full",
      eventImpactFacts: [],
      eventInteractions: []
    },
    usage: { prompt_tokens: 10, completion_tokens: 20, total_tokens: 30 }
  };
}

export function makeApiResult(
  body: VersionedCreateScenariosOut,
  overrides: Partial<ApiCallResult<VersionedCreateScenariosOut>["record"]> = {}
): ApiCallResult<VersionedCreateScenariosOut> {
  return {
    ok: true,
    data: body,
    record: {
      id: `call-${Math.random()}`,
      url: "http://127.0.0.1:8001/v2/scenario-groups/sync",
      method: "POST",
      request: {},
      startedAt: "2026-07-30T00:00:00.000Z",
      finishedAt: "2026-07-30T00:00:00.100Z",
      elapsedMs: 100,
      httpStatus: 200,
      transportStatus: "success",
      judgment: "success",
      parsed: body,
      rawText: JSON.stringify(body),
      ...overrides
    }
  };
}

export function makeResponse(
  version: ApiVersion,
  options: Parameters<typeof makeVersionData>[1] = {}
): VersionedCreateScenariosOut {
  return {
    status: "success",
    message: "성공",
    data: makeVersionData(version, options)
  };
}
