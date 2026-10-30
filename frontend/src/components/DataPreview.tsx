import React, { useState } from "react";
import { Table, Search, Database } from "lucide-react";

interface DataPreviewProps {
  entities: Record<string, Record<string, any>[]>;
  totalCounts?: Record<string, number>;
}

export const DataPreview: React.FC<DataPreviewProps> = ({ entities, totalCounts }) => {
  const entityNames = Object.keys(entities);
  const [selectedEntity, setSelectedEntity] = useState<string>(entityNames[0] || "");
  const [searchQuery, setSearchQuery] = useState("");

  const currentEntity = selectedEntity && entities[selectedEntity] ? selectedEntity : entityNames[0] || "";
  const records = entities[currentEntity] || [];

  const columns = records.length > 0 ? Object.keys(records[0]) : [];

  const filteredRecords = records.filter((row) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return Object.values(row).some((val) => String(val).toLowerCase().includes(query));
  });

  if (entityNames.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500">
        <Database className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm">No dataset generated yet. Submit a prompt above to preview data.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      {/* Entity Tabs and Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        {/* Entity Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Table className="w-4 h-4 text-indigo-400 mr-1" />
          {entityNames.map((name) => {
            const count = totalCounts?.[name] || entities[name]?.length || 0;
            const isSelected = name === currentEntity;
            return (
              <button
                key={name}
                onClick={() => {
                  setSelectedEntity(name);
                  setSearchQuery("");
                }}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-slate-950/70 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                <span>{name}</span>
                <span className="text-[10px] bg-slate-850 px-1.5 py-0.2 rounded-full opacity-80">{count}</span>
              </button>
            );
          })}
        </div>

        {/* Filter Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={`Filter ${currentEntity}...`}
            className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 w-full sm:w-48"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-slate-800/80 rounded-lg max-h-96 overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-slate-950 sticky top-0 border-b border-slate-800 z-10">
            <tr>
              <th className="py-2.5 px-3 font-semibold text-slate-400 w-12 text-center">#</th>
              {columns.map((col) => (
                <th key={col} className="py-2.5 px-3 font-semibold text-slate-300 whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {filteredRecords.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                <td className="py-2 px-3 text-slate-500 text-center font-mono text-[11px]">{idx + 1}</td>
                {columns.map((col) => {
                  const val = row[col];
                  const isNull = val === null || val === undefined;
                  return (
                    <td key={col} className="py-2 px-3 text-slate-300 font-mono text-[11px] whitespace-nowrap">
                      {isNull ? (
                        <span className="text-amber-500/80 italic">NULL</span>
                      ) : typeof val === "boolean" ? (
                        <span className={val ? "text-emerald-400" : "text-rose-400"}>{String(val)}</span>
                      ) : (
                        String(val)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
            {filteredRecords.length === 0 && (
              <tr>
                <td colSpan={columns.length + 1} className="py-6 text-center text-slate-500">
                  No records match your filter query.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="text-[11px] text-slate-500 flex justify-between items-center pt-1">
        <span>
          Showing {filteredRecords.length} of {records.length} preview records
        </span>
        <span>Table: {currentEntity}</span>
      </div>
    </div>
  );
};

