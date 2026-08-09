"use client";

import { useState } from "react";
import type { Config } from "@/lib/types";
import { titleCase } from "@/lib/format";

// Similarity-weight editor. Weights are per-CMA settings, not standards; the
// backend renormalizes, so they need not sum to exactly 1.
export function WeightsEditor({
  config,
  onSave,
  saving,
}: {
  config: Config;
  onSave: (weights: Record<string, number>) => void;
  saving?: boolean;
}) {
  const [weights, setWeights] = useState<Record<string, number>>({ ...config.weights });
  const total = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSave(weights);
      }}
      aria-label="Similarity component weights"
    >
      <p className="mb-3 text-xs text-slate-500">
        These weights are settings for <em>this analysis only</em>: demonstration
        defaults, not appraisal standards. They are renormalized over the components that
        can actually be computed. Changes are recorded in the audit trail.
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Object.entries(weights).map(([name, value]) => (
          <div key={name}>
            <label htmlFor={`weight-${name}`} className="field-label">
              {titleCase(name)}
            </label>
            <input
              id={`weight-${name}`}
              type="number"
              min={0}
              max={1}
              step={0.01}
              className="field-input"
              value={value}
              onChange={(e) =>
                setWeights((w) => ({ ...w, [name]: Number(e.target.value) || 0 }))
              }
            />
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between">
        <p className={`text-xs ${Math.abs(total - 1) > 0.001 ? "text-amber-700" : "text-slate-500"}`}>
          Total: {total.toFixed(2)}
          {Math.abs(total - 1) > 0.001 && " (will be normalized to 1.00)"}
        </p>
        <button type="submit" className="btn-secondary" disabled={saving}>
          {saving ? "Saving…" : "Save weights"}
        </button>
      </div>
    </form>
  );
}
