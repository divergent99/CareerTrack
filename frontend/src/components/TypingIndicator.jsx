import { useEffect, useState } from "react";

const QUERY_PHRASES = [
  "Thinking",
  "Querying your data",
  "Pulling from multiple tables",
  "This one's taking a bit longer",
];
const SIMPLE_PHRASES = ["Thinking"];

export default function TypingIndicator({ isSimple = false }) {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const phrases = isSimple ? SIMPLE_PHRASES : QUERY_PHRASES;

  useEffect(() => {
    if (isSimple) return;
    const interval = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % phrases.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [isSimple]);

  return (
    <div className="flex justify-start mb-3">
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl px-4 py-3 flex items-center gap-2 text-sm text-neutral-400">
        <span>{phrases[phraseIndex]}</span>
        <span className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce" />
        </span>
      </div>
    </div>
  );
}