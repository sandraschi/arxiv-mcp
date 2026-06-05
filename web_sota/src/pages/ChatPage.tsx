import { useEffect, useRef, useState } from "react";
import { apiGet } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { PageHero } from "@/components/layout/PageHero";
import { useLogger } from "@/context/LoggerContext";

const OLLAMA = "http://localhost:11434";

type Msg = { role: "user" | "assistant"; content: string };

async function ollamaChat(model: string, messages: Msg[]): Promise<string> {
  const r = await fetch(`${OLLAMA}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
      stream: false,
    }),
  });
  if (!r.ok) throw new Error(`Ollama HTTP ${r.status}`);
  const data = (await r.json()) as { message?: { content?: string } };
  return data.message?.content ?? "(empty)";
}

export function ChatPage() {
  const { log } = useLogger();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("llama3.2");
  const [ollamaUp, setOllamaUp] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await apiGet<{ ollama_detected?: boolean; configured_model?: string }>("/api/llm/discover");
        setOllamaUp(Boolean(d.ollama_detected));
        if (d.configured_model) setModel(d.configured_model);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || loading) return;
    const user: Msg = { role: "user", content: input.trim() };
    const next = [...messages, user];
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const reply = await ollamaChat(model, next);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: String(e) }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 flex flex-col h-[calc(100vh-8rem)]">
      <PageHero eyebrow="Local LLM" title="Chat" lead="Direct Ollama chat for quick research prompts (zero API cost)." />
      <div className="flex flex-wrap gap-2 items-center text-xs">
        {ollamaUp === null ? (
          <span className="text-muted-foreground">Detecting Ollama…</span>
        ) : ollamaUp ? (
          <span className="text-primary">Ollama on :11434</span>
        ) : (
          <span className="text-destructive">Ollama not detected — start Ollama for chat</span>
        )}
        <input
          className="rounded border border-border bg-background px-2 py-1 font-mono"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          aria-label="Model name"
        />
      </div>
      <Card className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground">Ask about arXiv workflows, paper summaries, or epistemic analysis.</p>
          )}
          {messages.map((m, i) => (
            <div key={`${i}-${m.role}`} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  m.role === "user" ? "bg-primary/15" : "bg-muted/50"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {loading && <p className="text-xs text-muted-foreground animate-pulse">Thinking…</p>}
          <div ref={bottomRef} />
        </div>
        <div className="border-t border-border p-3 flex gap-2">
          <input
            className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Message…"
          />
          <Button onClick={send} disabled={loading || !ollamaUp}>
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
}
