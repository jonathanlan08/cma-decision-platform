"use client";

import type { Sensitivity } from "@/lib/types";
import { money, titleCase } from "@/lib/format";

const ASSUMPTION_LABELS: Record<string, string> = {
  monthly_market_pct: "Market movement /mo",
  gla_per_sqft: "Living area $/sq ft",
  lot_per_sqft: "Lot $/sq ft",
  per_bedroom: "Per bedroom",
  per_bathroom: "Per bathroom",
  per_condition_step: "Per condition step",
  per_parking_space: "Per parking space",
  pool_value: "Pool",
};

function signedMoney(value: number | null): string {
  if (value === null) return "—";
  const rounded = Math.round(value);
  if (rounded === 0) return "$0";
  return `${rounded > 0 ? "+" : "−"}${money(Math.abs(rounded))}`;
}

// Tornado view: one bar per assumption spanning the central estimate's move
// when that assumption is varied down/up by variation_pct.
export function SensitivityPanel({ data }: { data: Sensitivity }) {
  const maxAbs = Math.max(
    1,
    ...data.items.flatMap((item) => [
      Math.abs(item.delta_low ?? 0),
      Math.abs(item.delta_high ?? 0),
    ]),
  );
  const pctLabel = `±${Math.round(data.variation_pct * 100)}%`;

  return (
    <div>
      <p className="mb-3 text-sm text-slate-500">
        How much the central estimate moves when each assumption is varied {pctLabel},
        one at a time, largest impact first. Wide bars mean the result leans on that
        assumption, so verify those against your market knowledge first.
      </p>
      <div className="overflow-x-auto">
        <table className="data-table">
          <caption className="sr-only">
            Assumption sensitivity: change in central estimate at {pctLabel}
          </caption>
          <thead>
            <tr>
              <th scope="col">Assumption</th>
              <th scope="col" className="num">Current value</th>
              <th scope="col" className="w-2/5">
                Central estimate shift ({pctLabel})
              </th>
              <th scope="col" className="num">−{Math.round(data.variation_pct * 100)}%</th>
              <th scope="col" className="num">+{Math.round(data.variation_pct * 100)}%</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => {
              const low = item.delta_low ?? 0;
              const high = item.delta_high ?? 0;
              const leftmost = Math.min(low, high, 0);
              const rightmost = Math.max(low, high, 0);
              const left = 50 + (leftmost / maxAbs) * 48;
              const width = ((rightmost - leftmost) / maxAbs) * 48;
              const negligible = Math.abs(low) < 1 && Math.abs(high) < 1;
              return (
                <tr key={item.assumption}>
                  <td className="font-medium">
                    {ASSUMPTION_LABELS[item.assumption] ?? titleCase(item.assumption)}
                  </td>
                  <td className="num">
                    {item.assumption === "monthly_market_pct"
                      ? `${(item.value * 100).toFixed(2)}%`
                      : money(item.value)}
                  </td>
                  <td aria-hidden="true">
                    <div className="relative h-4 w-full min-w-40 rounded bg-slate-100">
                      <span className="absolute inset-y-0 left-1/2 w-px bg-slate-400" />
                      {!negligible && (
                        <span
                          className="absolute inset-y-0.5 rounded-sm bg-accent-600/70"
                          style={{ left: `${left}%`, width: `${Math.max(width, 0.75)}%` }}
                        />
                      )}
                    </div>
                  </td>
                  <td className="num tabular-nums">{signedMoney(item.delta_low)}</td>
                  <td className="num tabular-nums">{signedMoney(item.delta_high)}</td>
                </tr>
              );
            })}
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center text-slate-400">
                  No non-zero assumptions to vary.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-500">{data.note}</p>
    </div>
  );
}
