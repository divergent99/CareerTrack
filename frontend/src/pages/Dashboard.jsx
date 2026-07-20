import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, PieChart, Pie, Cell, Legend
} from "recharts";
import { Briefcase, XCircle, Clock } from "lucide-react";
import { getSummary, getFunnel, getTimeline, getApplications, getCompanyInsights } from "../api";
import PageLoading from "../components/PageLoading";

const COLORS = ["#5227FF", "#8B5CF6", "#A78BFA", "#C4B5FD", "#7C3AED", "#6D28D9", "#4C1D95"];

const STATUS_BADGE = {
  offer: "bg-green-500/15 text-green-400 border-green-500/30",
  interview_scheduled: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  screening_scheduled: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  rejection_after_application: "bg-red-500/15 text-red-400 border-red-500/30",
  rejection_after_interview: "bg-red-500/15 text-red-400 border-red-500/30",
  post_offer_onboarding: "bg-green-500/15 text-green-400 border-green-500/30",
  applied_confirmation: "bg-neutral-500/15 text-neutral-300 border-neutral-500/30",
};

function StatusBadge({ status }) {
  const cls = STATUS_BADGE[status] || "bg-neutral-500/15 text-neutral-300 border-neutral-500/30";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${cls}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function CompanyCard({ c }) {
  const cleanWebsite = c.website ? c.website.replace(/^https?:\/\//, "") : null;

  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-semibold text-neutral-100">{c.company}</span>
        {c.rating && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
            ★ {c.rating}
          </span>
        )}
      </div>

      <div className="text-xs text-neutral-500 mb-2">
        {c.role}
        {cleanWebsite && (
            <a
            href={`https://${cleanWebsite}`}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 text-blue-400 hover:underline"
          >
            {cleanWebsite}
          </a>
        )}
      </div>

      <p className="text-xs text-neutral-400 leading-relaxed mb-2">{c.summary}</p>

      {c.recent_move && (
        <p className="text-xs text-neutral-500 leading-relaxed border-t border-neutral-800 pt-2">
          <span className="text-neutral-400 font-medium">Recent: </span>
          {c.recent_move}
        </p>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [apps, setApps] = useState([]);
  const [insights, setInsights] = useState(null);

  useEffect(() => {
    getSummary().then(setSummary);
    getFunnel().then(setFunnel);
    getTimeline().then((d) => setTimeline(d.timeline));
    getApplications().then(setApps);
    getCompanyInsights().then((d) => setInsights(d.companies));
  }, []);

  if (!summary || !funnel || !timeline) {
    return <PageLoading page="dashboard" variant="dashboard" />;
  }

  const funnelData = Object.entries(funnel.funnel).map(([stage, count]) => ({
    stage: stage.replace(/_/g, " "),
    count,
  }));

  const pieData = Object.entries(summary.by_status).map(([status, count]) => ({
    name: status.replace(/_/g, " "),
    value: count,
  }));

  return (
    <div className="flex-1 h-full overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        <h1 className="text-2xl font-semibold text-white">Dashboard</h1>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex items-start justify-between">
            <div>
              <div className="text-4xl font-semibold text-white mb-1">{summary.total_applications}</div>
              <div className="text-sm text-neutral-400">Total applications</div>
              <div className="text-xs text-neutral-600 mt-2">
                Across {Object.keys(summary.by_status).length} pipeline stages
              </div>
            </div>
            <Briefcase className="text-neutral-700" size={28} />
          </div>

          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex items-start justify-between">
            <div>
              <div className="text-4xl font-semibold text-white mb-1">{summary.total_rejections}</div>
              <div className="text-sm text-neutral-400">Rejections</div>
              <div className="text-xs text-neutral-600 mt-2">
                {((summary.total_rejections / summary.total_applications) * 100).toFixed(0)}% of total
              </div>
            </div>
            <XCircle className="text-neutral-700" size={28} />
          </div>

          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex items-start justify-between">
            <div>
              <div className="text-4xl font-semibold text-white mb-1">{summary.pending_leads}</div>
              <div className="text-sm text-neutral-400">Pending leads</div>
              <div className="text-xs text-neutral-600 mt-2">Not yet applied to</div>
            </div>
            <Clock className="text-neutral-700" size={28} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <h2 className="text-sm font-medium text-neutral-300 mb-4">Pipeline funnel</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={funnelData} margin={{ bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis
                  dataKey="stage"
                  tick={{ fill: "#a3a3a3", fontSize: 10 }}
                  angle={-30}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fill: "#a3a3a3", fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#171717", border: "1px solid #262626", color: "#fff" }} />
                <Bar dataKey="count" fill="#5227FF" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
            <h2 className="text-sm font-medium text-neutral-300 mb-4">Status distribution</h2>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="45%" outerRadius={70}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#171717", border: "1px solid #262626", color: "#fff" }} />
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{ fontSize: 11, color: "#a3a3a3" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-300 mb-4">Applications over time</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="date" tick={{ fill: "#a3a3a3", fontSize: 10 }} />
              <YAxis tick={{ fill: "#a3a3a3", fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#171717", border: "1px solid #262626", color: "#fff" }} />
              <Line type="monotone" dataKey="count" stroke="#5227FF" strokeWidth={2} dot={{ fill: "#5227FF" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-300 mb-4">Company snapshots</h2>
          {!insights ? (
            <p className="text-sm text-neutral-500">Loading company research...</p>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {insights.map((c, i) => (
                <CompanyCard key={i} c={c} />
              ))}
            </div>
          )}
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-sm font-medium text-neutral-300 mb-4">Companies</h2>
          <div className="space-y-2">
            {apps.map((a) => (
              <div key={a.id} className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-neutral-950/50 transition-colors">
                <div>
                  <span className="text-sm text-neutral-100 font-medium">{a.company || "Unknown company"}</span>
                  <span className="text-sm text-neutral-500 ml-2">{a.role || "no role logged"}</span>
                </div>
                <StatusBadge status={a.status} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
