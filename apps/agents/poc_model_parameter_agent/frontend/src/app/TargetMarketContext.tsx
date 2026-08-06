import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

interface TargetMarketValue { targetMarket: string; setTargetMarket: (value: string) => void }
const TargetMarketContext = createContext<TargetMarketValue | null>(null);

export function TargetMarketProvider({ children }: { children: ReactNode }) {
  const [targetMarket, setTargetMarket] = useState("JKM");
  const value = useMemo(() => ({ targetMarket, setTargetMarket }), [targetMarket]);
  return <TargetMarketContext.Provider value={value}>{children}</TargetMarketContext.Provider>;
}

export function useTargetMarket() {
  const value = useContext(TargetMarketContext);
  if (!value) throw new Error("useTargetMarket must be used within TargetMarketProvider");
  return value;
}
