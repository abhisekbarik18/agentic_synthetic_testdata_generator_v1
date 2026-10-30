import React from "react";

interface ProgressBarProps {
  progress: number; // 0 to 100
  label?: string;
  status?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({ progress, label, status }) => {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className="w-full space-y-1.5">
      <div className="flex justify-between items-center text-xs font-medium text-slate-400">
        <span>{label || "Execution Progress"}</span>
        <span className="font-semibold text-slate-200">{Math.round(clampedProgress)}%</span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden p-0.5 border border-slate-700/60">
        <div
          className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-1.5 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
      {status && <p className="text-xs text-slate-500 italic truncate">{status}</p>}
    </div>
  );
};

