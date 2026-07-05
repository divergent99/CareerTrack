import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Message({ role, content }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-xl px-4 py-2 rounded-2xl text-sm ${
          isUser
            ? "bg-[#5227FF] text-white"
            : "bg-neutral-900 border border-neutral-800 text-neutral-100"
        }`}
      >
        {isUser ? (
          content
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}