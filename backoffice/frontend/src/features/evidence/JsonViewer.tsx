import { useMemo, useState } from "react";
import { Check, ChevronDown, Clipboard, Search } from "lucide-react";

interface JsonViewerProps {
  value: unknown;
  label?: string;
  defaultOpen?: boolean;
}

export function stringifyJson(value: unknown): string {
  if (value === undefined) return "표시할 데이터가 없습니다.";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function JsonViewer({
  value,
  label = "JSON",
  defaultOpen = true
}: JsonViewerProps) {
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const text = useMemo(() => stringifyJson(value), [value]);
  const matchCount = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return 0;
    return text
      .toLocaleLowerCase()
      .split(needle)
      .slice(1).length;
  }, [query, text]);

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  }

  return (
    <details className="json-viewer" open={defaultOpen}>
      <summary>
        <ChevronDown aria-hidden="true" size={16} />
        {label}
      </summary>
      <div className="json-toolbar">
        <label className="json-search">
          <Search aria-hidden="true" size={15} />
          <span className="sr-only">{label} 검색</span>
          <input
            type="search"
            value={query}
            placeholder="JSON 검색"
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
        </label>
        <span aria-live="polite">
          {query.trim() ? `${matchCount}개 일치` : "검색어 없음"}
        </span>
        <button
          className="button quiet compact"
          type="button"
          onClick={() => void copy()}
        >
          {copied ? (
            <Check aria-hidden="true" size={16} />
          ) : (
            <Clipboard aria-hidden="true" size={16} />
          )}
          {copied ? "복사됨" : "JSON 복사"}
        </button>
      </div>
      <pre tabIndex={0} aria-label={`${label} raw text`}>
        {text}
      </pre>
    </details>
  );
}
