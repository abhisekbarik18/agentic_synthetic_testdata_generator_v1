import React from "react";
import { AgentStatusInfo } from "@/types";
import { CheckCircle2, CircleDashed, AlertCircle, Clock, Cpu } from "lucide-react";

interface AgentStatusProps {
  statuses: AgentStatusInfo[];
  activeAgent?: string;
}

const AGENT_ORDER = [
  { key: "exploration", label: "Scenario Exploration Agent", desc: "Mapping domain workflows, assumptions & realism rules" },
  { key: "requirement_analysis", label: "Requirement Analysis Agent", desc: "Extracting schemas, types & constraints" },
  { key: "planning", label: "Planning Agent", desc: "Dependency ordering & batch strategies" },
  { key: "generation", label: "Data Generation Agent", desc: "Synthesizing realistic records & edge cases" },
  { key: "validation", label: "Validation Agent", desc: "Schema, business rules & referential checks" },
  { key: "export", label: "Export Agent", desc: "Compiling multi-format downloads" },
];

export const AgentStatus: React.FC<AgentStatusProps> = ({ statuses, activeAgent }) => {
  const statusMap = new Map(statuses.map((s) => [s.name, s]));

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-800">
        <Cpu className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">Multi-Agent Workflow</h3>
      </div>

      <div className="space-y-3">
        {AGENT_ORDER.map((agent, index) => {
          const info = statusMap.get(agent.key);
          const status = info?.status || "pending";
          const isCurrent = activeAgent === agent.key;

          return (
            <div
              key={agent.key}
              className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
                status === "completed"
                  ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-300"
                  : status === "running" || isCurrent
                  ? "bg-indigo-950/30 border-indigo-500/50 text-indigo-200 animate-pulse"
                  : status === "failed"
                  ? "bg-rose-950/20 border-rose-800/40 text-rose-300"
                  : "bg-slate-950/40 border-slate-800/40 text-slate-400"
              }`}
            >
              <div className="mt-0.5">
                {status === "completed" && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
                {(status === "running" || isCurrent) && <CircleDashed className="w-5 h-5 text-indigo-400 animate-spin" />}
                {status === "failed" && <AlertCircle className="w-5 h-5 text-rose-400" />}
                {status === "pending" && !isCurrent && <Clock className="w-5 h-5 text-slate-500" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-200">
                    {index + 1}. {agent.label}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase tracking-wider ${
                      status === "completed"
                        ? "bg-emerald-900/40 text-emerald-300"
                        : status === "running" || isCurrent
                        ? "bg-indigo-900/50 text-indigo-300 font-bold"
                        : status === "failed"
                        ? "bg-rose-900/40 text-rose-300"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {isCurrent && status !== "completed" ? "RUNNING" : status}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">{info?.message || agent.desc}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
