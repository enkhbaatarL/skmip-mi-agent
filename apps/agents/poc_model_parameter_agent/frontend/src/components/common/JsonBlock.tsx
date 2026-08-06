import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function JsonBlock({ value, label = "JSON" }: { value: unknown; label?: string }) {
  const [copied, setCopied] = useState(false);
  const text = typeof value === "string" ? value : JSON.stringify(value ?? {}, null, 2);
  const copy = async () => {
    await navigator.clipboard?.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_500);
  };
  return (
    <div className="json-block">
      <div className="json-block__header"><span>{label}</span><button className="text-button" type="button" onClick={copy}>{copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "복사됨" : "복사"}</button></div>
      <pre tabIndex={0}>{text}</pre>
    </div>
  );
}
