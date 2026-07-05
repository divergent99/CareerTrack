import { useState, useEffect } from "react";
import { GitBranch, TrendingUp, AlertTriangle, XCircle } from "lucide-react";
import { analyzeGithub } from "../api";

const RELEVANCE_COLOR = {
  high: "bg-green-500/15 text-green-400 border-green-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-neutral-500/15 text-neutral-400 border-neutral-500/30",
};

const STATUS_PHRASES = [
  "Pulling your repos from GitHub",
  "Digging through commit history",
  "Judging your tech stack (kindly)",
];
const FUN_FACTS = [
  "Fun fact: the first GitHub commit was in 2007, by a guy named Tom",
  "Fun fact: 'git' is British slang for an unpleasant person, Linus named it that on purpose",
  "Fun fact: the octocat has 8 arms because GitHub couldn't decide on a mascot pose",
];
const LOADING_PHRASES = [
  STATUS_PHRASES[0],
  FUN_FACTS[0],
  STATUS_PHRASES[1],
  FUN_FACTS[1],
  STATUS_PHRASES[2],
  FUN_FACTS[2],
  "Almost done, promise",
];

function AnalyzingIndicator() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % LOADING_PHRASES.length), 1600);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="mt-6 flex flex-col items-center gap-3">
      <div className="flex gap-1.5">
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
      </div>
      <p className="text-sm text-neutral-400">{LOADING_PHRASES[i]}</p>
    </div>
  );
}

export default function GithubAnalysis({ result, setResult }) {
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    setLoading(true);
    setResult(null);
    const res = await analyzeGithub();
    setResult(res);
    setLoading(false);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-2xl font-semibold text-white">GitHub Analysis</h1>
        <p className="text-sm text-neutral-400">
          See which repos are worth putting on your resume, based on your target roles.
          Only public repos are visible here, private work isn't factored in.
        </p>

        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-neutral-800 rounded-lg text-white text-sm font-medium transition-colors"
        >
          Analyze my GitHub
        </button>

        {loading && <AnalyzingIndicator />}

        {result && !loading && (
          <div className="space-y-6">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <h2 className="text-sm font-medium text-neutral-300 mb-2">Overview</h2>
              <p className="text-sm text-neutral-400">{result.overall_summary}</p>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <h2 className="text-sm font-medium text-neutral-300 mb-3 flex items-center gap-2">
                <TrendingUp className="text-blue-400" size={16} /> Top projects to feature
              </h2>
              <div className="space-y-3">
                {result.top_projects.map((p, i) => (
                  <div key={i} className="bg-neutral-950 border border-neutral-800 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-semibold text-neutral-100 flex items-center gap-2">
                        <GitBranch size={14} /> {p.name}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${RELEVANCE_COLOR[p.relevance] || RELEVANCE_COLOR.medium}`}>
                        {p.relevance} relevance
                      </span>
                    </div>
                    <p className="text-xs text-neutral-500 mb-2">{p.reason}</p>
                    <p className="text-xs text-neutral-300 bg-neutral-900 rounded-md px-3 py-2 border border-neutral-800">
                      {p.resume_bullet_suggestion}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
                <h2 className="text-sm font-medium text-neutral-300 mb-3 flex items-center gap-2">
                  <AlertTriangle className="text-amber-400" size={16} /> Gaps
                </h2>
                <ul className="space-y-2">
                  {result.gaps.map((g, i) => (
                    <li key={i} className="text-sm text-neutral-400">• {g}</li>
                  ))}
                </ul>
              </div>

              <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
                <h2 className="text-sm font-medium text-neutral-300 mb-3 flex items-center gap-2">
                  <XCircle className="text-red-400" size={16} /> Deprioritize
                </h2>
                <ul className="space-y-2 max-h-64 overflow-y-auto">
                  {result.projects_to_deprioritize.map((p, i) => (
                    <li key={i} className="text-sm text-neutral-400">• {p}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <h2 className="text-sm font-medium text-neutral-300 mb-3">Tech stack distribution</h2>
              <div className="flex flex-wrap gap-2">
                {Object.entries(result.tech_stack_summary).map(([tech, count]) => (
                  <span key={tech} className="text-xs px-3 py-1.5 rounded-full bg-neutral-950 border border-neutral-800 text-neutral-300">
                    {tech} <span className="text-neutral-500">×{count}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}