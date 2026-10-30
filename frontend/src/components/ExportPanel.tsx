import React, { useState } from "react";
import { ExportFileInfo, ExportFormat } from "@/types";
import { getDownloadUrl } from "@/lib/api";
import { Download, FileText, Plus, Check } from "lucide-react";

interface ExportPanelProps {
  jobId: string;
  files: ExportFileInfo[];
  onRequestExport: (formats: ExportFormat[]) => void;
  isExporting: boolean;
}

const ALL_FORMATS: { format: ExportFormat; label: string }[] = [
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

export const ExportPanel: React.FC<ExportPanelProps> = ({
  jobId,
  files,
  onRequestExport,
  isExporting,
}) => {
  const [selectedNewFormats, setSelectedNewFormats] = useState<ExportFormat[]>([]);

  const existingFormats = new Set(files.map((f) => f.format.toLowerCase()));
  const getEntityKey = (file: ExportFileInfo) =>
    file.entity_name ||
    file.filename
      .replace(/\.[^.]+$/, "")
      .replace(/_\d{8}T\d{6}_\d{6}Z$/, "");
  const orderedFiles = files
    .map((file, index) => ({ file, index }))
    .sort((a, b) => {
      const aTime = a.file.created_at ? Date.parse(a.file.created_at) : NaN;
      const bTime = b.file.created_at ? Date.parse(b.file.created_at) : NaN;
      if (Number.isFinite(aTime) && Number.isFinite(bTime) && aTime !== bTime) {
        return bTime - aTime;
      }
      return b.index - a.index;
    });
  const latestFileByOutput = new Map<string, number>();
  orderedFiles.forEach(({ file, index }) => {
    const outputKey = `${getEntityKey(file)}:${file.format.toLowerCase()}`;
    if (!latestFileByOutput.has(outputKey)) {
      latestFileByOutput.set(outputKey, index);
    }
  });

  const toggleFormat = (fmt: ExportFormat) => {
    setSelectedNewFormats((prev) =>
      prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
    );
  };

  const handleRequestMore = () => {
    if (selectedNewFormats.length === 0) return;
    onRequestExport(selectedNewFormats);
    setSelectedNewFormats([]);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Download className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
            Export Downloads & Multi-Format Generation
          </h3>
        </div>
        <span className="text-xs text-slate-400">{files.length} file version(s) available</span>
      </div>

      {/* Available Download Files */}
      {files.length === 0 ? (
        <div className="p-6 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg">
          <FileText className="w-6 h-6 mx-auto mb-1.5 opacity-40" />
          <p className="text-xs">No export files generated yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {orderedFiles.map(({ file, index }) => {
            const downloadUrl = getDownloadUrl(jobId, file.filename);
            const isLatest =
              latestFileByOutput.get(`${getEntityKey(file)}:${file.format.toLowerCase()}`) === index;
            const createdAt = file.created_at ? new Date(file.created_at) : null;
            return (
              <div
                key={`${file.filename}:${file.created_at ?? "legacy"}:${index}`}
                className="bg-slate-950/70 border border-slate-800 hover:border-indigo-500/50 rounded-lg p-4 flex items-start justify-between gap-3 transition-colors group"
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <div className="mt-0.5 rounded-md bg-indigo-950 p-2 text-indigo-400">
                    <FileText className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="inline-flex rounded border border-indigo-800/60 bg-indigo-950 px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase text-indigo-300">
                        {file.format}
                      </span>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                        isLatest
                          ? "bg-emerald-950 text-emerald-300"
                          : "bg-slate-800 text-slate-400"
                      }`}>
                        {isLatest ? "Latest" : "Previous version"}
                      </span>
                    </div>
                    <p className="mt-1.5 break-all text-sm font-medium leading-5 text-slate-100">
                      {file.filename}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {file.record_count} records <span aria-hidden="true">·</span> {formatBytes(file.size_bytes)}
                    </p>
                    {createdAt && Number.isFinite(createdAt.getTime()) && (
                      <p className="mt-1 text-[11px] text-slate-500">
                        Generated {createdAt.toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>

                <a
                  href={downloadUrl}
                  download={file.filename}
                  aria-label={`Download ${file.filename}`}
                  className="shrink-0 rounded-md bg-indigo-600/30 p-2 text-indigo-200 transition-colors hover:bg-indigo-600 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                </a>
              </div>
            );
          })}
        </div>
      )}

      {/* On-Demand Additional Formats */}
      <div className="pt-3 border-t border-slate-800 space-y-3">
        <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
          <Plus className="w-3.5 h-3.5 text-indigo-400" />
          Convert Existing Dataset to Additional Formats:
        </span>

        <div className="flex flex-wrap items-center gap-2">
          {ALL_FORMATS.map(({ format, label }) => {
            const isAlreadyExported = existingFormats.has(format);
            const isSelected = selectedNewFormats.includes(format);

            return (
              <button
                key={format}
                type="button"
                disabled={isAlreadyExported || isExporting}
                onClick={() => toggleFormat(format)}
                className={`text-xs px-2.5 py-1 rounded-md border flex items-center gap-1 transition-all ${
                  isAlreadyExported
                    ? "bg-slate-950/40 border-slate-850 text-slate-600 cursor-not-allowed"
                    : isSelected
                    ? "bg-indigo-600/30 border-indigo-500 text-indigo-200 font-semibold"
                    : "bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700"
                }`}
              >
                {isSelected && <Check className="w-3 h-3 text-indigo-400" />}
                {label}
                {isAlreadyExported && <span className="text-[9px] text-slate-500">(ready)</span>}
              </button>
            );
          })}

          <button
            type="button"
            disabled={selectedNewFormats.length === 0 || isExporting}
            onClick={handleRequestMore}
            className="text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-medium px-3 py-1 rounded-md transition-colors ml-auto"
          >
            {isExporting ? "Converting..." : "Export Selected"}
          </button>
        </div>
      </div>
    </div>
  );
};
