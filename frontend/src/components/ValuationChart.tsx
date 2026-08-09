"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Valuation } from "@/lib/types";
import { money } from "@/lib/format";

// Adjusted values per comparable against the indicated range. The chart is
// decorative reinforcement; the accessible data lives in the tables around it.
export function ValuationChart({ valuation }: { valuation: Valuation }) {
  const rows = (valuation.per_comparable ?? []).map((entry) => ({
    name:
      entry.address && entry.address.length > 18
        ? `${entry.address.slice(0, 17)}…`
        : entry.address ?? `#${entry.comp_id}`,
    fullName: entry.address ?? `Comparable ${entry.comp_id}`,
    value: entry.adjusted_price,
    influence: entry.influence_pct,
  }));

  if (rows.length === 0 || valuation.central_estimate === null) return null;

  return (
    <figure aria-hidden="true" className="mt-4">
      <figcaption className="mb-1 text-xs text-slate-500">
        Adjusted comparable values vs. the indicated range (shaded band; center line =
        central estimate). Table equivalent below.
      </figcaption>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} margin={{ top: 8, right: 16, bottom: 40, left: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="name"
              angle={-35}
              textAnchor="end"
              interval={0}
              tick={{ fontSize: 10, fill: "#475569" }}
            />
            <YAxis
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 11, fill: "#475569" }}
              width={56}
            />
            <Tooltip
              formatter={(value: number | string, key) =>
                key === "value" ? [money(Number(value)), "Adjusted value"] : [String(value), key]
              }
              labelFormatter={(label, payload) =>
                payload?.[0]?.payload?.fullName ?? String(label)
              }
            />
            {valuation.low_estimate !== null && valuation.high_estimate !== null && (
              <ReferenceArea
                y1={valuation.low_estimate}
                y2={valuation.high_estimate}
                fill="#1d4ed8"
                fillOpacity={0.07}
              />
            )}
            <ReferenceLine
              y={valuation.central_estimate}
              stroke="#1d4ed8"
              strokeWidth={2}
              strokeDasharray="6 3"
            />
            <Bar dataKey="value" radius={[3, 3, 0, 0]}>
              {rows.map((row) => (
                <Cell key={row.fullName} fill="#64748b" fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
