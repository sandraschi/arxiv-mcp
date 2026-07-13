/**
 * speech-service.ts — Unified speech abstraction for fleet webapp chat pages.
 *
 * Two backends, auto-detected:
 *   Tier 2 — speech-mcp (http://127.0.0.1:10909): better TTS voices, cross-browser STT
 *   Tier 1 — Web Speech API (browser built-in): zero-dep fallback, Chrome/Edge only
 *   None   — both unavailable: components render nothing
 *
 * Usage in any chat page:
 *   import { initSpeechService, isTtsAvailable, speak, isSttAvailable, createStt } from "@/common/speech-service";
 *   import { SpeakButton } from "@/components/SpeakButton";
 *   import { MicButton } from "@/components/MicButton";
 */

const SPEECH_MCP_URL = "http://127.0.0.1:10909";
let _useMcp = false;
let _mcpProbed = false;

/** Call once at app mount (e.g. in Layout or ChatPage useEffect). Probes speech-mcp. */
export async function initSpeechService(): Promise<void> {
  if (_mcpProbed) return;
  _mcpProbed = true;
  try {
    const r = await fetch(`${SPEECH_MCP_URL}/api/v1/health`, {
      signal: AbortSignal.timeout(2000),
    });
    _useMcp = r.ok;
  } catch {
    _useMcp = false;
  }
}

// -- TTS -------------------------------------------------------------------

export function isTtsAvailable(): boolean {
  return _useMcp || (typeof window !== "undefined" && !!window.speechSynthesis);
}

export interface TtsSession {
  cancel: () => void;
  done: Promise<void>;
}

/**
 * Speak text aloud. Returns a session with cancel() and a done promise
 * that resolves when playback finishes naturally.
 * Uses speech-mcp when available (WAV fetch + Audio playback).
 * Falls back to window.speechSynthesis (utterance onend).
 */
export async function speak(text: string): Promise<TtsSession> {
  const plain = stripMarkdown(text);
  if (!plain) return { cancel: () => {}, done: Promise.resolve() };

  if (_useMcp) {
    const controller = new AbortController();
    try {
      const res = await fetch(
        `${SPEECH_MCP_URL}/api/v1/tts/wav?text=${encodeURIComponent(plain)}&provider=windows`,
        { signal: controller.signal },
      );
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        const cancel = () => {
          audio.pause();
          audio.currentTime = 0;
          URL.revokeObjectURL(url);
        };
        const done = new Promise<void>((resolve) => {
          audio.onended = () => {
            URL.revokeObjectURL(url);
            resolve();
          };
          audio.onerror = () => {
            URL.revokeObjectURL(url);
            resolve();
          };
        });
        audio.play().catch(() => {});
        return { cancel, done };
      }
    } catch {
      // speech-mcp failed — fall through to Web Speech API
    }
  }

  // Fallback: Web Speech API
  if (typeof window === "undefined" || !window.speechSynthesis)
    return { cancel: () => {}, done: Promise.resolve() };
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(plain);
  u.rate = 1;
  u.pitch = 1;
  const done = new Promise<void>((resolve) => {
    u.onend = () => resolve();
  });
  window.speechSynthesis.speak(u);
  return { cancel: () => window.speechSynthesis.cancel(), done };
}

// -- STT (Web Speech API only; speech-mcp STT is documented separately) ----

export function isSttAvailable(): boolean {
  if (typeof window === "undefined") return false;
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: (event: SpeechRecognitionEvent) => void;
  onend: () => void;
  onerror: (event: Event) => void;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
}
declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const _Recognition =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

export interface SttSession {
  start: () => void;
  stop: () => void;
}

/**
 * Create a speech recognition session. Falls back to no-op when STT is
 * unavailable (the UI should hide the mic button via isSttAvailable()).
 */
export function createStt(
  onResult: (transcript: string, isFinal: boolean) => void,
  onEnd: () => void,
): SttSession {
  if (!_Recognition) return { start: () => {}, stop: () => {} };
  const recognition = new _Recognition() as SpeechRecognition;
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = navigator.language || "en-US";
  recognition.onresult = (e: SpeechRecognitionEvent) => {
    let transcript = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
    }
    onResult(transcript, e.results[e.results.length - 1].isFinal);
  };
  recognition.onend = onEnd;
  recognition.onerror = () => onEnd();
  return {
    start: () => {
      try {
        recognition.start();
      } catch {
        onEnd();
      }
    },
    stop: () => {
      try {
        recognition.abort();
      } catch {}
      onEnd();
    },
  };
}

// -- Utils -----------------------------------------------------------------

function stripMarkdown(md: string): string {
  return md
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*_`#~]/g, "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\n+/g, " ")
    .trim();
}
