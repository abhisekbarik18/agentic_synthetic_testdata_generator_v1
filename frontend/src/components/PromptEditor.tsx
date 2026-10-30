import React, { useState } from "react";
import { ExportFormat } from "@/types";
import { Sparkles, Play, RefreshCw, Send, Check } from "lucide-react";

interface PromptEditorProps {
  onGenerate: (prompt: string, formats: ExportFormat[]) => void;
  onFollowup?: (prompt: string, regenerate: boolean) => Promise<boolean>;
  isLoading: boolean;
  hasExistingJob: boolean;
}

const TEMPLATES = [
  {
    title: "Financial Statements",
    prompt:
      "Create synthetic, internally consistent financial statements for a fictional company for the most recently completed fiscal year, with comparative prior-year figures and USD currency. Generate four entities: StatementOfIncome (SOI) with revenue, cost of goods sold, gross profit, operating expenses, operating income, taxes, and net income; BalanceSheet with current and non-current assets, current and long-term liabilities, and equity; CashFlowStatement with operating, investing, and financing cash flows; and StatementOfChangesInEquity. Include columns for period, line_item, amount, currency, and statement_section. Include subtotals and totals, ensure SOI net income reconciles, assets equal liabilities plus equity, cash flows reconcile opening to closing cash, and equity roll-forward reconciles. Use realistic positive and negative amounts and clearly identify totals.",
  },
  {
    title: "FinTech Transactions & Fraud",
    prompt:
      "Generate 200 financial transactions across 20 user accounts with columns: transaction_id, user_id, amount (positive/negative), currency (USD/EUR/GBP), category, timestamp, merchant, and is_fraudulent boolean. Include 5 edge-case fraudulent transactions with extreme amounts.",
  },
  {
    title: "Relational E-Commerce",
    prompt:
      "Create a multi-table relational dataset: 'customers' (50 rows: id, full_name, email, tier, signup_date) and 'orders' (150 rows: order_id, customer_id referencing customers, total_amount, status [pending/shipped/delivered], order_date). Ensure foreign-key integrity.",
  },
  {
    title: "Healthcare Patient Records",
    prompt:
      "Generate 100 realistic anonymized patient records with patient_id, full_name, dob, blood_type, primary_condition, systolic_bp (90-180), diastolic_bp (60-120), last_visit_date. Include edge cases with boundary blood pressure readings.",
  },
];

const AVAILABLE_FORMATS: { format: ExportFormat; label: string }[] = [
  { format: "csv", label: "CSV" },
  { format: "json", label: "JSON" },
  { format: "xlsx", label: "Excel (XLSX)" },
  { format: "sql", label: "SQL Inserts" },
  { format: "parquet", label: "Parquet" },
  { format: "xml", label: "XML" },
  { format: "pdf", label: "PDF" },
  { format: "html", label: "HTML" },
  { format: "markdown", label: "Markdown" },
  { format: "docx", label: "Word (DOCX)" },
];

export const PromptEditor: React.FC<PromptEditorProps> = ({
  onGenerate,
  onFollowup,
  isLoading,
  hasExistingJob,
}) => {
  const [prompt, setPrompt] = useState("");
  const [selectedFormats, setSelectedFormats] = useState<ExportFormat[]>(["csv", "json"]);
  const [followupPrompt, setFollowupPrompt] = useState("");
  const [regenerateFollowup, setRegenerateFollowup] = useState(false);

  const toggleFormat = (fmt: ExportFormat) => {
    setSelectedFormats((prev) =>
      prev.includes(fmt) ? (prev.length > 1 ? prev.filter((f) => f !== fmt) : prev) : [...prev, fmt]
    );
  };

  const handleGenerateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    onGenerate(prompt.trim(), selectedFormats);
  };

  const handleFollowupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!followupPrompt.trim() || isLoading || !onFollowup) return;
    const succeeded = await onFollowup(followupPrompt.trim(), regenerateFollowup);
    if (succeeded) setFollowupPrompt("");
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Natural-Language Data Specification
          </label>
          <span className="text-xs text-slate-400">Describe entities, columns, rules & counts</span>
        </div>

        <form onSubmit={handleGenerateSubmit} className="space-y-4">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Generate 100 enterprise employees across 5 departments with foreign keys, realistic salaries, emails, and edge cases..."
            rows={4}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-y"
          />

          {/* Quick Templates */}
          <div>
            <p className="text-xs font-medium text-slate-400 mb-2">Quick Starter Templates:</p>
            <div className="flex flex-wrap gap-2">
              {TEMPLATES.map((tpl, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setPrompt(tpl.prompt)}
                  className="text-xs bg-slate-800 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 rounded-md px-2.5 py-1 transition-colors"
                >
                  {tpl.title}
                </button>
              ))}
            </div>
          </div>

          {/* Export Formats Selector */}
          <div>
            <p className="text-xs font-medium text-slate-400 mb-2">Requested Export Formats:</p>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_FORMATS.map(({ format, label }) => {
                const isSelected = selectedFormats.includes(format);
                return (
                  <button
                    key={format}
                    type="button"
                    onClick={() => toggleFormat(format)}
                    className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-all ${
                      isSelected
                        ? "bg-indigo-600/30 border-indigo-500 text-indigo-200 shadow-sm shadow-indigo-500/20"
                        : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            type="submit"
            disabled={!prompt.trim() || isLoading}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white font-medium text-sm py-2.5 px-4 rounded-lg shadow-md transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Synthesizing Data with LangGraph Agents...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Agentic Data Generation
              </>
            )}
          </button>
        </form>
      </div>

      {/* Follow-up / Natural Language Refinement Section */}
      {hasExistingJob && onFollowup && (
        <div className="pt-4 border-t border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
              Follow-Up Instruction / Natural-Language Export
            </span>
            <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={regenerateFollowup}
                onChange={(e) => setRegenerateFollowup(e.target.checked)}
                className="rounded border-slate-700 text-indigo-600 focus:ring-0"
              />
              Regenerate Records
            </label>
          </div>

          <form onSubmit={handleFollowupSubmit} className="flex gap-2">
            <input
              type="text"
              value={followupPrompt}
              onChange={(e) => setFollowupPrompt(e.target.value)}
              placeholder="e.g., Convert this dataset to Parquet and SQL"
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            />
            <button
              type="submit"
              disabled={!followupPrompt.trim() || isLoading}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
              Apply
            </button>
          </form>
          <p className="text-[11px] text-slate-500">
            Name one or more output formats to export the current data. Enable Regenerate Records to change records or the schema.
          </p>
        </div>
      )}
    </div>
  );
};
