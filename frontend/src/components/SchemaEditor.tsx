import React from "react";
import { RequirementSpec } from "@/types";
import { Layers, Key, Link2, ShieldCheck } from "lucide-react";

interface SchemaEditorProps {
  spec?: RequirementSpec;
}

export const SchemaEditor: React.FC<SchemaEditorProps> = ({ spec }) => {
  if (!spec || !spec.entities || spec.entities.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center text-slate-500">
        <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm">No schema analyzed yet. Enter a prompt to generate data schemas.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-6">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
        <Layers className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-slate-100 uppercase tracking-wider">
          Extracted Schema & Entity Specifications
        </h3>
      </div>

      <div className="space-y-6">
        {spec.entities.map((entity) => (
          <div key={entity.name} className="border border-slate-800 rounded-lg bg-slate-950/60 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-sm font-bold text-slate-100">{entity.name}</span>
                {entity.description && <p className="text-xs text-slate-400">{entity.description}</p>}
              </div>
              <span className="text-xs bg-indigo-950 border border-indigo-800/60 text-indigo-300 font-mono px-2 py-0.5 rounded">
                Target: {entity.record_count} records
              </span>
            </div>

            {/* Fields Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 px-2">Field</th>
                    <th className="py-2 px-2">Type</th>
                    <th className="py-2 px-2">Attributes</th>
                    <th className="py-2 px-2">Constraints</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40 font-mono text-[11px]">
                  {entity.fields.map((field) => (
                    <tr key={field.name} className="hover:bg-slate-900/50">
                      <td className="py-2 px-2 text-slate-200 font-semibold flex items-center gap-1.5">
                        {field.unique && (
                          <span title="Unique key">
                            <Key className="w-3 h-3 text-amber-400" />
                          </span>
                        )}
                        {field.name}
                      </td>
                      <td className="py-2 px-2 text-indigo-300">{field.data_type}</td>
                      <td className="py-2 px-2 text-slate-400">
                        {field.nullable ? (
                          <span className="text-amber-400/80">Nullable</span>
                        ) : (
                          <span className="text-slate-500">Required</span>
                        )}
                        {field.unique && <span className="ml-2 text-purple-400">Unique</span>}
                      </td>
                      <td className="py-2 px-2 text-slate-400">
                        {field.constraints ? (
                          <span className="text-slate-400">
                            {Object.entries(field.constraints)
                              .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
                              .join(" | ")}
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Relationships & Foreign Keys */}
            {entity.relationships && entity.relationships.length > 0 && (
              <div className="pt-2 border-t border-slate-800/60">
                <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1 mb-1.5">
                  <Link2 className="w-3.5 h-3.5 text-indigo-400" />
                  Referential Relationships:
                </span>
                <div className="flex flex-wrap gap-2">
                  {entity.relationships.map((rel, i) => (
                    <div
                      key={i}
                      className="text-[11px] font-mono bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-300"
                    >
                      <span className="text-indigo-400">{rel.from_field}</span> →{" "}
                      <span className="text-emerald-400">{rel.to_entity}</span>.{rel.to_field}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Business Rules */}
            {entity.business_rules && entity.business_rules.length > 0 && (
              <div className="pt-2 border-t border-slate-800/60">
                <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1 mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Business Rules:
                </span>
                <ul className="list-disc list-inside text-[11px] text-slate-400 space-y-0.5">
                  {entity.business_rules.map((rule, idx) => (
                    <li key={idx}>{rule}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

