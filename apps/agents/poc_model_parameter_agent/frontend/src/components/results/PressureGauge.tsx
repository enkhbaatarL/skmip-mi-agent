import { StatusBadge } from "../common/StatusBadge";

const bands = [
  { key: "strong_bearish", label: "Strong Bearish", short: "강한 하락" },
  { key: "bearish", label: "Bearish", short: "하락" },
  { key: "balanced", label: "Balanced", short: "균형" },
  { key: "bullish", label: "Bullish", short: "상승" },
  { key: "strong_bullish", label: "Strong Bullish", short: "강한 상승" },
];

const indexFor = (value?: string) => Math.max(0, bands.findIndex((band) => band.key === value));

export function PressureGauge({ declared, computed, score, consistency }: { declared?: string; computed?: string; score?: number; consistency?: string }) {
  const declaredIndex = indexFor(declared);
  const computedIndex = indexFor(computed);
  return (
    <section className="pressure-gauge" aria-label="Target Market Pressure Gauge">
      <div className="section-heading section-heading--inline">
        <div><span className="eyebrow">MARKET SIGNAL</span><h3>Target Market Pressure Gauge</h3></div>
        <StatusBadge>{consistency ?? "unknown"}</StatusBadge>
      </div>
      <div className="pressure-scale" role="img" aria-label={`선언 ${declared ?? "없음"}, 계산 ${computed ?? "없음"}, 점수 ${score?.toFixed(2) ?? "없음"}`}>
        {bands.map((band, index) => (
          <div className={`pressure-band pressure-band--${band.key}`} key={band.key}>
            {index === declaredIndex && declared && <span className="pressure-marker pressure-marker--declared" title="선언 Band">D</span>}
            {index === computedIndex && computed && <span className="pressure-marker pressure-marker--computed" title="계산 Net Pressure">N</span>}
            <span>{band.label}</span><small>{band.short}</small>
          </div>
        ))}
      </div>
      <div className="pressure-legend"><span><i className="legend-dot legend-dot--declared" />D · 선언 Band</span><span><i className="legend-dot legend-dot--computed" />N · 계산 Net Pressure</span><strong>Net score {score?.toFixed(2) ?? "—"}%</strong></div>
    </section>
  );
}
