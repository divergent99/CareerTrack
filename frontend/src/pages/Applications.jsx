import { useEffect, useState } from "react";
import { getApplications, updateApplication, logInterviewRound, getInterviewRounds } from "../api";

const STATUS_OPTIONS = [
  "applied_confirmation", "screening_scheduled", "interview_scheduled",
  "interview_followup", "rejection_after_application", "rejection_after_interview",
  "offer", "ghosted", "feedback_request", "post_offer_onboarding", "other",
];

function ApplicationRow({ app, onUpdated }) {
  const [company, setCompany] = useState(app.company || "");
  const [status, setStatus] = useState(app.status || "other");
  const [expanded, setExpanded] = useState(false);
  const [rounds, setRounds] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    round_number: 1, round_type: "", questions_asked: "", self_rating: 3, outcome: "pending", notes: ""
  });

  const needsAttention = !app.company || app.status === "other";

  const toggleExpand = async () => {
    if (!expanded) {
      const data = await getInterviewRounds(app.id);
      setRounds(data);
    }
    setExpanded(!expanded);
  };

  const saveEdits = async () => {
    await updateApplication(app.id, { company, status });
    onUpdated();
  };

  const submitRound = async (e) => {
    e.preventDefault();
    await logInterviewRound(app.id, form);
    const data = await getInterviewRounds(app.id);
    setRounds(data);
    setShowForm(false);
    setForm({ round_number: rounds.length + 2, round_type: "", questions_asked: "", self_rating: 3, outcome: "pending", notes: "" });
  };

  return (
    <div className={`rounded-xl border p-4 mb-3 ${needsAttention ? "border-amber-700/50 bg-amber-950/10" : "border-neutral-800 bg-neutral-900"}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex-1 grid grid-cols-3 gap-3">
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Company (missing)"
            className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
          />
          <div className="text-sm text-neutral-400 flex items-center">{app.role || "no role logged"}</div>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
          >
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <button onClick={saveEdits} className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-white">
          Save
        </button>
        <button onClick={toggleExpand} className="text-xs px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 rounded-lg text-neutral-200">
          {expanded ? "Hide" : "Interviews"}
        </button>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-neutral-800">
          {rounds.length === 0 && <p className="text-xs text-neutral-500 mb-2">No interview rounds logged yet.</p>}
          {rounds.map((r, i) => (
            <div key={i} className="text-sm text-neutral-300 mb-2 pl-3 border-l-2 border-neutral-700">
              <span className="font-medium">Round {r.round_number} ({r.round_type || "unspecified"})</span>
              {r.questions_asked && <p className="text-neutral-400 mt-1">Q: {r.questions_asked}</p>}
              <p className="text-neutral-500 text-xs mt-1">Outcome: {r.outcome} · Self-rating: {r.self_rating}/5</p>
            </div>
          ))}

          {!showForm ? (
            <button onClick={() => setShowForm(true)} className="text-xs text-blue-400 hover:text-blue-300 mt-2">
              + Log an interview round
            </button>
          ) : (
            <form onSubmit={submitRound} className="mt-3 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number" placeholder="Round #"
                  value={form.round_number}
                  onChange={(e) => setForm({ ...form, round_number: parseInt(e.target.value) })}
                  className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
                />
                <input
                  placeholder="Type (DSA, system design, HR...)"
                  value={form.round_type}
                  onChange={(e) => setForm({ ...form, round_type: e.target.value })}
                  className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
                />
              </div>
              <textarea
                placeholder="Questions asked"
                value={form.questions_asked}
                onChange={(e) => setForm({ ...form, questions_asked: e.target.value })}
                className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
                rows={2}
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={form.outcome}
                  onChange={(e) => setForm({ ...form, outcome: e.target.value })}
                  className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
                >
                  <option value="pending">Pending</option>
                  <option value="passed">Passed</option>
                  <option value="failed">Failed</option>
                </select>
                <select
                  value={form.self_rating}
                  onChange={(e) => setForm({ ...form, self_rating: parseInt(e.target.value) })}
                  className="bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-100"
                >
                  {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>Self-rating: {n}/5</option>)}
                </select>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-white">
                  Save round
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="text-xs px-3 py-1.5 bg-neutral-800 rounded-lg text-neutral-300">
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

export default function Applications() {
  const [apps, setApps] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = () => getApplications().then(setApps);
  useEffect(() => { load(); }, []);

  const filtered = filter === "needs_attention"
    ? apps.filter((a) => !a.company || a.status === "other")
    : apps;

  return (
    <div className="flex-1 h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold text-white">Applications</h1>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-1.5 text-sm text-neutral-200"
          >
            <option value="all">All applications</option>
            <option value="needs_attention">Needs attention</option>
          </select>
        </div>
        {filtered.map((app) => (
          <ApplicationRow key={app.id} app={app} onUpdated={load} />
        ))}
      </div>
    </div>
  );
}