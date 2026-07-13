/**
 * SpeakButton — "Read aloud" button for assistant messages.
 *
 * Drop into any fleet chat page. Place next to each assistant message.
 * Auto-hides when speech is unavailable (no browser support, no speech-mcp).
 *
 * Usage:
 *   import { SpeakButton } from "@/components/SpeakButton";
 *   // Inside message render loop:
 *   <SpeakButton text={msg.content} />
 *
 * Dependencies: lucide-react (Volume2 icon), @/lib/speech-service
 * Import initSpeechService once at the app root or ChatPage mount.
 */

import { Volume2 } from "lucide-react";
import { useRef, useState } from "react";
import { isTtsAvailable, speak, type TtsSession } from "@/lib/speech-service";

export function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);
  const sessionRef = useRef<TtsSession | null>(null);

  if (!isTtsAvailable()) return null;

  return (
    <button
      type="button"
      onClick={async () => {
        if (speaking && sessionRef.current) {
          sessionRef.current.cancel();
          sessionRef.current = null;
          setSpeaking(false);
          return;
        }
        setSpeaking(true);
        const session = await speak(text);
        sessionRef.current = session;
        await session.done;
        sessionRef.current = null;
        setSpeaking(false);
      }}
      className={
        speaking
          ? "p-1.5 rounded transition-colors text-amber-400 bg-amber-500/20"
          : "p-1.5 rounded transition-colors text-slate-400 hover:text-white hover:bg-white/10"
      }
      title={speaking ? "Stop" : "Speak"}
    >
      <Volume2 className="h-3.5 w-3.5" />
    </button>
  );
}
