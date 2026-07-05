import { useState, useEffect } from "react";
import { Upload, CheckCircle2, AlertTriangle, TrendingUp } from "lucide-react";
import { analyzeResume } from "../api";

const FIT_COLOR = {
  strong: "bg-green-500/15 text-green-400 border-green-500/30",
  moderate: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  weak: "bg-red-500/15 text-red-400 border-red-500/30",
};

const ANALYZING_PHRASES = [
  "Reading your resume",
  "Cross-referencing your applications",
  "Checking interview patterns",
  "Almost done",
];

function AnalyzingIndicator() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % ANALYZING_PHRASES.length), 1600);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="mt-6 flex flex-col items-center gap-3">
      <div className="flex gap-1.5">
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
        <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" />
      </div>
      <p className="text-sm text-neutral-400">{ANALYZING_PHRASES[i]}</p>
    </div>
  );
}

export default function ResumeReview() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (f) setFile(f);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    const res = await analyzeResume(file);
    setResult(res);
    setLoading(false);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-2xl font-semibold text-white">Resume Review</h1>
        <p className="text-sm text-neutral-400">
          Upload your resume to see how it holds up against your actual application history.
        </p>

        <div className="bg-neutral-900 border border-neutral-800 border-dashed rounded-xl p-8 text-center">
          <input type="file" accept=".pdf" onChange={handleFile} className="hidden" id="resume-upload" />
          <label htmlFor="resume-upload" className="cursor-pointer flex flex-col items-center gap-2">
            <Upload className="text-neutral-500" size={28} />
            <span className="text-sm text-neutral-300">
              {file ? file.name : "Click to upload a PDF resume"}
            </span>
          </label>

          {file && !loading && (
            <button
              onClick={handleAnalyze}
              className="mt-4 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-white text-sm font-medium transition-colors"
            >
              Analyze resume
            </button>
          )}

          {loading && <AnalyzingIndicator />}
        </div>

        {result && !loading && (
          <div className="space-y-6">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <h2 className="text-sm font-medium text-neutral-300 mb-2">Overall</h2>
              <p className="text-sm text-neutral-400">{result.overall_summary}</p>
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
                <h2 className="text-sm font-medium text-neutral-300 mb-3 flex items-center gap-2">
                  <CheckCircle2 className="text-green-400" size={16} /> Strengths
                </h2>
                <ul className="space-y-2">
                  {result.strengths.map((s, i) => (
                    <li key={i} className="text-sm text-neutral-400">• {s}</li>
                  ))}
                </ul>
              </div>

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
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <h2 className="text-sm font-medium text-neutral-300 mb-3">Company fit</h2>
              <div className="space-y-2">
                {result.company_fit.map((c, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2 rounded-lg bg-neutral-950">
                    <div>
                      <span className="text-sm font-medium text-neutral-100">{c.company}</span>
                      <span className="text-xs text-neutral-500 ml-2">{c.role}</span>
                      <p className="text-xs text-neutral-500 mt-1">{c.reason}</p>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full border shrink-0 ml-3 ${FIT_COLOR[c.fit] || FIT_COLOR.moderate}`}>
                      {c.fit}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
              <h2 className="text-sm font-medium text-neutral-300 mb-3 flex items-center gap-2">
                <TrendingUp className="text-blue-400" size={16} /> Suggested edits
              </h2>
              <ul className="space-y-2">
                {result.suggested_edits.map((e, i) => (
                  <li key={i} className="text-sm text-neutral-400">• {e}</li>
                ))}
              </ul>
            </div>

            {result.pattern_from_rejections && (
              <div className="bg-amber-950/10 border border-amber-700/30 rounded-xl p-6">
                <h2 className="text-sm font-medium text-amber-400 mb-2">Pattern in rejections</h2>
                <p className="text-sm text-neutral-300">{result.pattern_from_rejections}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}