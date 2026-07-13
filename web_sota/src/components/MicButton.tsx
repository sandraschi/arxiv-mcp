/**
 * MicButton — Voice input button for chat pages.
 *
 * Drop into any fleet chat page next to the text input.
 * Captures speech via Web Speech API and inserts into the input field.
 * Shows interim transcript as italic preview above the input.
 * Auto-hides when STT is unavailable (Chrome/Edge only).
 *
 * Usage:
 *   import { MicButton } from "@/components/MicButton";
 *   // Inside the chat form, before the input:
 *   <MicButton input={input} setInput={setInput} />
 *
 * Dependencies: lucide-react (Mic, MicOff icons), @/lib/speech-service
 * Import initSpeechService once at the app root or ChatPage mount.
 */

import { Mic, MicOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  createStt,
  isSttAvailable,
  type SttSession,
} from "@/lib/speech-service";

export function MicButton({
  input,
  setInput,
}: {
  input: string;
  setInput: (val: string) => void;
}) {
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const sttRef = useRef<SttSession | null>(null);

  useEffect(() => {
    if (!isSttAvailable()) return;
    sttRef.current = createStt(
      (transcript, isFinal) => {
        if (isFinal) {
          setInput(input + (input ? " " : "") + transcript);
          setInterim("");
        } else {
          setInterim(transcript);
        }
      },
      () => setListening(false),
    );
    return () => {
      sttRef.current?.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!isSttAvailable()) return null;

  return (
    <>
      {interim && (
        <p className="text-xs text-slate-500 mb-1 italic">
          &ldquo;{interim}&rdquo;
        </p>
      )}
      <button
        type="button"
        onClick={() => {
          if (!sttRef.current) return;
          if (listening) {
            sttRef.current.stop();
            setListening(false);
          } else {
            sttRef.current.start();
            setListening(true);
          }
        }}
        className={
          listening
            ? "p-2 rounded-md border border-slate-700 text-red-400 border-red-500/50 bg-red-500/10 animate-pulse flex-shrink-0"
            : "p-2 rounded-md border border-slate-700 text-slate-400 hover:bg-slate-800 flex-shrink-0"
        }
        title={listening ? "Stop listening" : "Voice input"}
      >
        {listening ? (
          <MicOff className="h-4 w-4" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>
    </>
  );
}
