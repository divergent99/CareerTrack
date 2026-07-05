import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { generateRoadmap, lookupApplication, getApplications } from "../api";

const LOADING_PHRASES = [
  "Curating your roadmap",
  "Cross-referencing past interviews",
  "Pulling company context",
  "Almost there",
];

function LoadingAnimation() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % LOADING_PHRASES.length), 1600);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-8 flex flex-col items-center gap-3">
      <div className="flex gap-1.5">
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
      </div>
      <p className="text-sm text-neutral-400">{LOADING_PHRASES[i]}</p>
    </div>
  );
}

export default function Roadmap() {
  const [applications, setApplications] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [mode, setMode] = useState("existing");

  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [jdText, setJdText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getApplications().then(setApplications);
  }, []);

  const handleSelectExisting = async (companyName) => {
    setSelectedCompany(companyName);
    const res = await lookupApplication(companyName);
    if (res.found) {
      setCompany(companyName);
      setRole(res.role || "");
      setJdText(res.jd_text || "");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!company.trim()) return;
    setLoading(true);
    setResult(null);
    const res = await generateRoadmap(company, role, jdText);
    setResult(res.roadmap);
    setLoading(false);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-2xl font-semibold text-white">Interview Roadmap</h1>
        <p className="text-sm text-neutral-400">
          Pick a company you've already applied to, or set up a new one. Job description is optional.
        </p>

        <div className="flex gap-2">
          <button
            onClick={() => setMode("existing")}
            className={`px-4 py-2 rounded-lg text-sm ${mode === "existing" ? "bg-blue-600 text-white" : "bg-neutral-900 text-neutral-400 border border-neutral-800"}`}
          >
            Existing application
          </button>
          <button
            onClick={() => { setMode("manual"); setCompany(""); setRole(""); setJdText(""); }}
            className={`px-4 py-2 rounded-lg text-sm ${mode === "manual" ? "bg-blue-600 text-white" : "bg-neutral-900 text-neutral-400 border border-neutral-800"}`}
          >
            New / not tracked yet
          </button>
        </div>

        {mode === "existing" ? (
          <div className="space-y-2">
            {applications.length === 0 && (
              <p className="text-sm text-neutral-500">No applications tracked yet.</p>
            )}
            {applications.map((a) => (
              <button
                key={a.id}
                onClick={() => handleSelectExisting(a.company)}
                className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                  selectedCompany === a.company
                    ? "bg-blue-600/10 border-blue-600/40"
                    : "bg-neutral-900 border-neutral-800 hover:border-neutral-700"
                }`}
              >
                <span className="text-sm font-medium text-neutral-100">{a.company}</span>
                <span className="text-xs text-neutral-500 ml-2">{a.role || "no role logged"}</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Company"
              className="bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2 text-sm text-neutral-100"
            />
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="Role"
              className="bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2 text-sm text-neutral-100"
            />
          </div>
        )}

        {(company || mode === "manual") && (
          <form onSubmit={handleSubmit} className="space-y-3">
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the job description here (optional, skip if you don't have it)"
              rows={8}
              className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-3 text-sm text-neutral-100"
            />
            <button
              type="submit"
              disabled={loading || !company.trim()}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 disabled:text-neutral-600 rounded-lg text-white text-sm font-medium transition-colors"
            >
              Generate roadmap
            </button>
          </form>
        )}

        {loading && <LoadingAnimation />}

        {result && !loading && (
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 prose prose-invert prose-sm max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}