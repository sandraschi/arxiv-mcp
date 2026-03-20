import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type LogLevel = "info" | "warn" | "error" | "debug";

export type LogEntry = {
  id: string;
  ts: string;
  level: LogLevel;
  message: string;
};

type LoggerCtx = {
  entries: LogEntry[];
  log: (level: LogLevel, message: string) => void;
  clear: () => void;
};

const Ctx = createContext<LoggerCtx | null>(null);

export function LoggerProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<LogEntry[]>([]);

  const log = useCallback((level: LogLevel, message: string) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const ts = new Date().toISOString();
    setEntries((prev) => [...prev.slice(-200), { id, ts, level, message }]);
  }, []);

  const clear = useCallback(() => setEntries([]), []);

  const value = useMemo(() => ({ entries, log, clear }), [entries, log, clear]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useLogger() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useLogger outside LoggerProvider");
  return v;
}
