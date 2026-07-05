import { useEffect, useRef, useState } from "react";
import { Paperclip, X, ArrowUp } from "lucide-react";
import {
  sendMessage,
  saveFastPathExchange,
  getSessionMessages,
  getSummary,
  getFunnel,
  getCompanyStatusWithResearch,
} from "../api";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

const ACK_PATTERNS = /^(thanks?|thank you|thx|ok(ay)?|cool|got it|nice|sheesh|great|awesome|perfect)[\s!.]*$/i;

function isAcknowledgment(text) {
  return ACK_PATTERNS.test(text.trim());
}

const SUGGESTIONS = [
  {
    label: "How many applications am I tracking?",
    fastPath: async () => {
      const s = await getSummary();
      return `You're tracking **${s.total_applications} applications**, with **${s.total_rejections} rejections** and **${s.pending_leads} pending leads** you haven't applied to yet.`;
    },
  },
  {
    label: "Where do I keep getting rejected?",
    fastPath: async () => {
      const f = await getFunnel();
      const rows = Object.entries(f.funnel)
        .map(([stage, count]) => `| ${stage.replace(/_/g, " ")} | ${count} |`)
        .join("\n");
      return `Here's your pipeline breakdown:\n\n| Stage | Count |\n|---|---|\n${rows}`;
    },
  },
  {
    label: "What's the status of my Coforge application?",
    fastPath: async () => {
      const res = await getCompanyStatusWithResearch("Coforge");
      if (!res.found) return "No application found matching that company.";
      return res.reply;
    },
  },
  {
    label: "Summarize my job search so far",
    fastPath: async () => {
      const s = await getSummary();
      const statusLines = Object.entries(s.by_status)
        .map(([status, count]) => `- **${status.replace(/_/g, " ")}**: ${count}`)
        .join("\n");
      return `You have **${s.total_applications} applications** tracked.\n\n${statusLines}\n\n${s.total_rejections} rejections so far, and ${s.pending_leads} leads you haven't acted on yet.`;
    },
  },
];

export default function ChatWindow({ sessionId, onSessionCreated }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastSentText, setLastSentText] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);
  const fileInputRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      getSessionMessages(sessionId).then(setMessages);
    } else {
      setMessages([]);
    }
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) setAttachedFile(file);
  };

  const handleSend = async (overrideText, fastPath) => {
    const text = overrideText ?? input;
    if (!text.trim() && !attachedFile) return;

    const finalText = attachedFile ? `${text}\n\n[Attached: ${attachedFile.name}]` : text;

    const userMsg = { role: "user", content: finalText };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setAttachedFile(null);
    setLastSentText(text);
    setLoading(true);

    if (fastPath) {
      const reply = await fastPath();
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      setLoading(false);

      const res = await saveFastPathExchange(finalText, reply, sessionId);
      if (!sessionId) onSessionCreated(res.session_id);
      return;
    }

    const res = await sendMessage(sessionId, finalText);
    if (!sessionId) onSessionCreated(res.session_id);
    setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    setLoading(false);
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="h-14 flex items-center px-6 border-b border-neutral-800 shrink-0 bg-neutral-950">
        <span className="text-sm text-neutral-300 font-medium">
          {sessionId ? "CareerTrack" : "New chat"}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col relative z-10">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-6 pb-16">
            <p className="text-base text-neutral-400 mb-2">{getGreeting()}, Abhineet</p>
            <h1 className="text-3xl font-semibold text-white mb-2">
              Ask about your job search
            </h1>
            <p className="text-sm text-neutral-400 max-w-md mb-10">
              CareerTrack remembers every application, interview, and outcome.
            </p>
            <div className="grid grid-cols-2 gap-3 w-full max-w-xl">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => handleSend(s.label, s.fastPath)}
                  className="text-left text-sm px-5 py-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 hover:border-neutral-700 text-neutral-200 transition-all shadow-lg shadow-black/40 hover:-translate-y-0.5"
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl w-full mx-auto px-6 py-8">
            {messages.map((m, i) => (
              <Message key={i} role={m.role} content={m.content} />
            ))}
            {loading && <TypingIndicator isSimple={isAcknowledgment(lastSentText)} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="shrink-0 px-6 pb-6 pt-2">
        <div className="max-w-3xl mx-auto">
          {attachedFile && (
            <div className="mb-2 flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-1.5 w-fit text-xs text-neutral-300">
              <Paperclip size={12} />
              {attachedFile.name}
              <button onClick={() => setAttachedFile(null)} className="text-neutral-500 hover:text-red-400">
                <X size={12} />
              </button>
            </div>
          )}

          <div className="flex items-end gap-2 bg-neutral-900 border border-neutral-700 rounded-2xl px-3 py-2 shadow-lg shadow-black/50">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.png,.jpg,.jpeg"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-neutral-500 hover:text-neutral-200 transition-colors shrink-0"
              title="Attach a file"
            >
              <Paperclip size={18} />
            </button>

            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about your applications..."
              className="flex-1 bg-transparent text-neutral-100 outline-none py-2 text-sm"
            />

            <button
              onClick={() => handleSend()}
              disabled={!input.trim() && !attachedFile}
              className="p-2 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 rounded-lg text-white transition-colors shrink-0"
              title="Send"
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}