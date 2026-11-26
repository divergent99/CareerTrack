export default function TypingIndicator({ status = "Thinking" }) {
  return (
    <div className="flex justify-start mb-3">
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl px-4 py-3 flex items-center gap-2 text-sm text-neutral-400">
        <span>{status}</span>
        <span className="flex gap-1">
          <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-1.5 h-1.5 bg-neutral-500 rounded-full animate-bounce" />
        </span>
      </div>
    </div>
  );
}
