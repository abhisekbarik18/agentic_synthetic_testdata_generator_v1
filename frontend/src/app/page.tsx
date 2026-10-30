"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  createGenerationJob,
  getJob,
  getJobDataPreview,
  requestAdditionalExport,
  submitFollowup,
} from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import { JobData, ExportFormat, DataPreviewResponse } from "@/types";
import { PromptEditor } from "@/components/PromptEditor";
import { AgentStatus } from "@/components/AgentStatus";
import { DataPreview } from "@/components/DataPreview";
import { SchemaEditor } from "@/components/SchemaEditor";
import { ValidationReport } from "@/components/ValidationReport";
import { ExportPanel } from "@/components/ExportPanel";
import { ProgressBar } from "@/components/ProgressBar";
import {
  Cpu,
  Database,
  Table,
  Layers,
  ShieldCheck,
  Download,
  Terminal,
  Activity,
  AlertCircle,
  Settings2,
  Sun,
  Moon,
} from "lucide-react";
import { useTheme } from "@/components/ThemeProvider";

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  const [currentJob, setCurrentJob] = useState<JobData | null>(null);
  const [previewData, setPreviewData] = useState<DataPreviewResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"preview" | "schema" | "validation" | "export">("preview");
  const [isLoading, setIsLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeAgent, setActiveAgent] = useState<string | undefined>();
  const [progressVal, setProgressVal] = useState<number>(0);
  const [progressLabel, setProgressLabel] = useState<string>("Ready");

  // WebSocket for real-time orchestration streaming
  const handleWsMessage = useCallback((msg: any) => {
    if (msg.type === "agent_status") {
      setActiveAgent(msg.agent);
      setProgressLabel(`Running: ${msg.agent}...`);
      if (msg.agent === "exploration") setProgressVal(10);
      else if (msg.agent === "requirement_analysis") setProgressVal(25);
      else if (msg.agent === "planning") setProgressVal(40);
      else if (msg.agent === "generation") setProgressVal(65);
      else if (msg.agent === "validation") setProgressVal(85);
      else if (msg.agent === "export") setProgressVal(95);
    } else if (msg.type === "job_status") {
      if (msg.status === "completed") {
        setProgressVal(100);
        setProgressLabel("Completed");
        setActiveAgent(undefined);
        setIsLoading(false);
      } else if (msg.status === "failed") {
        setErrorMsg(msg.message || "Pipeline execution failed");
        setIsLoading(false);
      }
    }
  }, []);

  const { isConnected } = useWebSocket(currentJob?.job_id || null, handleWsMessage);

  // Poll for job updates and preview data when running
  useEffect(() => {
    if (!currentJob?.job_id) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getJob(currentJob.job_id);
        setCurrentJob(updated);

        if (updated.status === "completed" || updated.status === "failed") {
          setIsLoading(false);
          clearInterval(interval);

          // Fetch preview records
          if (updated.status === "completed") {
            const preview = await getJobDataPreview(currentJob.job_id);
            setPreviewData(preview);
          }
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentJob?.job_id, currentJob?.status]);

  // Handle generation submission
  const handleGenerate = async (prompt: string, formats: ExportFormat[]) => {
    setErrorMsg(null);
    setIsLoading(true);
    setProgressVal(5);
    setProgressLabel("Exploring real-world scenario...");
    setActiveAgent("exploration");

    try {
      const job = await createGenerationJob(prompt, formats);
      setCurrentJob(job);
      setPreviewData(null);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start generation");
      setIsLoading(false);
    }
  };

  // Handle on-demand export request
  const handleRequestExport = async (formats: ExportFormat[]) => {
    if (!currentJob) return;
    setIsExporting(true);
    try {
      const res = await requestAdditionalExport(currentJob.job_id, formats);
      const updated = await getJob(currentJob.job_id);
      setCurrentJob(updated);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to export formats");
    } finally {
      setIsExporting(false);
    }
  };

  // Handle follow-up prompt
  const handleFollowup = async (prompt: string, regenerate: boolean): Promise<boolean> => {
    if (!currentJob) return false;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const updated = await submitFollowup(currentJob.job_id, prompt, regenerate);
      setCurrentJob(updated);
      if (regenerate) {
        setProgressVal(10);
        setProgressLabel("Regenerating with follow-up instructions...");
        setPreviewData(null);
      } else {
        setIsLoading(false);
      }
      return true;
    } catch (err: any) {
      setErrorMsg(err.message || "Follow-up failed");
      setIsLoading(false);
      return false;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-tr from-indigo-600 to-purple-600 rounded-lg shadow-md shadow-indigo-500/20">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-100 tracking-tight flex items-center gap-2">
                Agentic Test Data Simulator
                <span className="text-[10px] uppercase font-mono bg-indigo-950 text-indigo-300 border border-indigo-800/60 px-1.5 py-0.2 rounded font-medium">
                  v1.0 • Multi-Agent
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">Natural-Language to Validated Synthetic Test Datasets</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Activity className={`w-3.5 h-3.5 ${isConnected ? "text-emerald-400 animate-pulse" : "text-slate-500"}`} />
              <span>{isConnected ? "WS Connected" : "HTTP Polling"}</span>
            </div>
            <div className="bg-slate-850 px-2.5 py-1 rounded border border-slate-700/60 text-slate-300">
              LangGraph + FastAPI
            </div>
            <button
              type="button"
              onClick={toggleTheme}
              aria-pressed={theme === "light"}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/60 bg-slate-850 px-2.5 py-1.5 text-slate-300 transition-colors hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <Settings2 className="h-4 w-4" aria-hidden="true" />
              {theme === "dark" ? (
                <Sun className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <Moon className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span className="sr-only">Theme settings</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full space-y-6">
        {/* Error Banner */}
        {errorMsg && (
          <div className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-4 flex items-center gap-3 text-rose-200 text-xs">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <div className="flex-1">{errorMsg}</div>
            <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-200">
              ✕
            </button>
          </div>
        )}

        {/* Top Grid: Prompt Editor & Agent Pipeline State */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-4">
            <PromptEditor
              onGenerate={handleGenerate}
              onFollowup={handleFollowup}
              isLoading={isLoading}
              hasExistingJob={!!currentJob}
            />

            {isLoading && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
                <ProgressBar progress={progressVal} label={progressLabel} status={`Job ID: ${currentJob?.job_id || "..."}`} />
              </div>
            )}
          </div>

          <div className="lg:col-span-5">
            <AgentStatus
              statuses={currentJob?.agent_statuses || []}
              activeAgent={activeAgent}
            />
          </div>
        </div>

        {/* Bottom Section: Tabs for Data Preview, Schema, Validation & Exports */}
        <div className="space-y-4">
          {/* Tab Headers */}
          <div className="flex items-center border-b border-slate-800 gap-2">
            <button
              onClick={() => setActiveTab("preview")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === "preview"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Table className="w-4 h-4" />
              Dataset Preview {currentJob ? `(${currentJob.record_count} records)` : ""}
            </button>

            <button
              onClick={() => setActiveTab("schema")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === "schema"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Layers className="w-4 h-4" />
              Extracted Schema
            </button>

            <button
              onClick={() => setActiveTab("validation")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === "validation"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              Validation Report
            </button>

            <button
              onClick={() => setActiveTab("export")}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                activeTab === "export"
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              <Download className="w-4 h-4" />
              Exports & Downloads {currentJob ? `(${currentJob.export_files?.length || 0})` : ""}
            </button>
          </div>

          {/* Tab Contents */}
          <div>
            {activeTab === "preview" && (
              <DataPreview
                entities={previewData?.entities || currentJob?.generated_data || {}}
                totalCounts={previewData?.total_records}
              />
            )}

            {activeTab === "schema" && <SchemaEditor spec={currentJob?.requirement_spec} />}

            {activeTab === "validation" && <ValidationReport report={currentJob?.validation_result} />}

            {activeTab === "export" && (
              <ExportPanel
                jobId={currentJob?.job_id || ""}
                files={currentJob?.export_files || []}
                onRequestExport={handleRequestExport}
                isExporting={isExporting}
              />
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/40 py-4 text-center text-xs text-slate-500 font-mono">
        Agentic Test Data Simulator • Built with Next.js, FastAPI, LangGraph, Pydantic & Modular LLM Adapters
      </footer>
    </div>
  );
}
