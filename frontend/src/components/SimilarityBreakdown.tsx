"use client";

import type { SimilarityBreakdown as Breakdown } from "@/lib/types";
import { titleCase } from "@/lib/format";

// Per-component score table with visual bars — the "show the work" view.
export function SimilarityBreakdown({ breakdown }: { breakdown: Breakdown }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
        Similarity breakdown — total {breakdown.score ?? "n/a"} / 100 (as of {breakdown.as_of})
      </h4>
      <div className="overflow-x-auto">
        <table className="data-table bg-white">
          <thead>
            <tr>
              <th scope="col">Component</th>
              <th scope="col">Subject</th>
              <th scope="col">Comparable</th>
              <th scope="col">Basis</th>
              <th scope="col" className="num">Weight</th>
              <th scope="col" className="num">Score</th>
              <th scope="col" className="num">Contribution</th>
            </tr>
          </thead>
          <tbody>
            {breakdown.components.map((c) => (
              <tr key={c.name} className={c.missing ? "text-slate-400" : ""}>
                <td className="font-medium">{titleCase(c.name)}</td>
                <td>{c.subject_value ?? "—"}</td>
                <td>{c.comparable_value ?? "—"}</td>
                <td className="text-xs">{c.detail ?? "—"}</td>
                <td className="num">
                  {(c.effective_weight * 100).toFixed(1)}%
                  {c.effective_weight !== c.weight && (
                    <span className="block text-xxs text-slate-400">
                      (configured {(c.weight * 100).toFixed(0)}%)
                    </span>
                  )}
                </td>
                <td className="num">
                  {c.missing ? (
                    <span title="Data missing — excluded from the score">missing</span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5">
                      <span
                        aria-hidden="true"
                        className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-slate-200"
                      >
                        <span
                          className="block h-full rounded-full bg-accent-600"
                          style={{ width: `${c.score ?? 0}%` }}
                        />
                      </span>
                      {c.score?.toFixed(0)}
                    </span>
                  )}
                </td>
                <td className="num">{c.missing ? "—" : c.contribution.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {breakdown.missing_components.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          Missing data excluded these components:{" "}
          {breakdown.missing_components.map(titleCase).join(", ")}. Remaining weights were
          renormalized.
        </p>
      )}
    </div>
  );
}
