import React from "react";
import { ValidationReportData } from "@/types";
import { ShieldCheck, AlertTriangle, XCircle, CheckCircle } from "lucide-react";

interface ValidationReportProps {
  report?: ValidationReportData;
}

export const ValidationReport: React.FC<ValidationReportProps> = ({ report }) => {
  if (!report) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center text-slate-500">
        <ShieldCheck className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm">Validation report will appear after the Validation Agent verifies records.</p>
      </div>
    );
  }

  const { is_valid, errors, warnings, records_checked, records_passed, records_failed } = report;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <ShieldCheck className={`w-5 h-5 ${is_valid ? "text-emerald-400" : "text-rose-400"}`} />
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
            Validation & Data Quality Report
          </h3>
        </div>
        <span
          className={`text-xs font-mono font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
            is_valid
              ? "bg-emerald-950 border border-emerald-800 text-emerald-300"
              : "bg-rose-950 border border-rose-800 text-rose-300"
          }`}
        >
          {is_valid ? "PASSED (100% Validated)" : "FAILED CHECKS"}
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-3 text-center">
          <span className="text-[11px] text-slate-400">Total Checked</span>
          <p className="text-lg font-bold text-slate-100 font-mono mt-0.5">{records_checked}</p>
        </div>
        <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-3 text-center">
          <span className="text-[11px] text-emerald-400">Passed</span>
          <p className="text-lg font-bold text-emerald-300 font-mono mt-0.5">{records_passed}</p>
        </div>
        <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-3 text-center">
          <span className="text-[11px] text-rose-400">Errors</span>
          <p className="text-lg font-bold text-rose-300 font-mono mt-0.5">{errors.length}</p>
        </div>
        <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-3 text-center">
          <span className="text-[11px] text-amber-400">Warnings</span>
          <p className="text-lg font-bold text-amber-300 font-mono mt-0.5">{warnings.length}</p>
        </div>
      </div>

      {/* Error List */}
      {errors.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
            <XCircle className="w-4 h-4" />
            Validation Errors ({errors.length})
          </h4>
          <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
            {errors.map((err, i) => (
              <div
                key={i}
                className="bg-rose-950/20 border border-rose-900/40 rounded p-2 text-xs flex items-start gap-2"
              >
                <span className="font-mono bg-rose-900/40 text-rose-300 text-[10px] px-1.5 py-0.5 rounded">
                  {err.entity}
                  {err.field ? `.${err.field}` : ""}
                </span>
                <span className="text-rose-200 flex-1">{err.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warning List */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" />
            Quality Warnings ({warnings.length})
          </h4>
          <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1">
            {warnings.map((warn, i) => (
              <div
                key={i}
                className="bg-amber-950/20 border border-amber-900/40 rounded p-2 text-xs flex items-start gap-2"
              >
                <span className="font-mono bg-amber-900/40 text-amber-300 text-[10px] px-1.5 py-0.5 rounded">
                  {warn.entity}
                </span>
                <span className="text-amber-200 flex-1">{warn.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {is_valid && (
        <div className="p-3 bg-emerald-950/30 border border-emerald-800/40 rounded-lg flex items-center gap-2 text-emerald-300 text-xs">
          <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>All schema types, constraints, and relational foreign keys passed validation successfully.</span>
        </div>
      )}
    </div>
  );
};

