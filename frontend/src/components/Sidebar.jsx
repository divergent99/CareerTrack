import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquarePlus, Trash2, LayoutDashboard, ListChecks } from "lucide-react";
import { getSessions, deleteSession } from "../api";
import { Map } from "lucide-react";
import { FileText } from "lucide-react";
import { GitBranch } from "lucide-react";

export default function Sidebar({ activeSessionId, onSelectSession, onNewChat }) {
  const [sessions, setSessions] = useState([]);

  const refresh = () => getSessions().then(setSessions);
  useEffect(() => { refresh(); }, [activeSessionId]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    await deleteSession(id);
    if (id === activeSessionId) onNewChat();
    refresh();
  };

  return (
    <div className="w-64 h-full bg-neutral-950 border-r border-neutral-800 flex flex-col shrink-0">
      <div className="h-14 flex items-center px-4 border-b border-neutral-800 shrink-0">
        <span className="text-sm font-semibold text-white">CareerTrack</span>
      </div>

      <div className="p-3 space-y-1 border-b border-neutral-800">
        <Link to="/dashboard" className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-neutral-300 hover:bg-neutral-900 transition-colors">
          <LayoutDashboard size={16} /> Dashboard
        </Link>
        <Link to="/applications" className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-neutral-300 hover:bg-neutral-900 transition-colors">
          <ListChecks size={16} /> Applications
        </Link>
        <Link to="/roadmap" className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-neutral-300 hover:bg-neutral-900 transition-colors">
        <Map size={16} /> Roadmap
        </Link>
        <Link to="/resume" className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-neutral-300 hover:bg-neutral-900 transition-colors">
        <FileText size={16} /> Resume Review
        </Link>
        <Link to="/github" className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-neutral-300 hover:bg-neutral-900 transition-colors">
        <GitBranch size={16} /> GitHub Analysis
        </Link>
      </div>

      <div className="p-3">
        <Link
          to="/"
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2.5 bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 rounded-lg text-sm text-neutral-100 font-medium transition-colors"
        >
          <MessageSquarePlus size={16} />
          New chat
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        <div className="text-xs text-neutral-600 uppercase tracking-wide px-2 py-2 font-medium">History</div>
        {sessions.length === 0 && (
          <div className="text-xs text-neutral-600 px-2 py-4 text-center">No conversations yet</div>
        )}
        {sessions.map((s) => (
          <Link
            to="/"
            key={s.id}
            onClick={() => onSelectSession(s.id)}
            className={`group flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
              s.id === activeSessionId ? "bg-neutral-800" : "hover:bg-neutral-900"
            }`}
          >
            <span className="truncate text-neutral-300">{s.title}</span>
            <button
              onClick={(e) => handleDelete(e, s.id)}
              className="opacity-0 group-hover:opacity-100 text-neutral-600 hover:text-red-400 transition-opacity ml-2 shrink-0"
              title="Delete chat"
            >
              <Trash2 size={14} />
            </button>
          </Link>
        ))}
      </div>

      <div className="p-3 border-t border-neutral-800">
        <div className="text-xs text-neutral-600 px-2">Tracking your job search</div>
      </div>
    </div>
  );
}