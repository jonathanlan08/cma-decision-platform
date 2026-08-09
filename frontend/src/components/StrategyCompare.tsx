"use client";

import { useState } from "react";
import type { Strategy } from "@/lib/types";
import { money, pct } from "@/lib/format";
import { Badge, levelTone, riskTone } from "./ui";

export interface StrategyCompareProps {
  strategies: Strategy[];
  centralEstimate: number;
  onPriceChange: (strategy: Strategy, price: number) => void;
  busyId?: number | null;
}

// Side-by-side scenario cards with editable list prices.
export function StrategyCompare({
  strategies,
  centralEstimate,
  onPriceChange,
  busyId,
}: StrategyCompareProps) {
  const [drafts, setDrafts] = useState<Record<number, string>>({});

  function commit(strategy: Strategy) {
    const raw = drafts[strategy.id];
    if (raw === undefined) return;
    // Accept "$" and thousands separators so pasted prices work too.
    const value = Number(raw.replace(/[$,\s]/g, ""));
    if (!Number.isNaN(value) && Number.isFinite(value) && value > 0
        && value !== strategy.list_price) {
      onPriceChange(strategy, value);
    }
    setDrafts((d) => {
      const next = { ...d };
      delete next[strategy.id];
      return next;
    });
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {strategies.map((strategy) => (
        <article
          key={strategy.id}
          aria-label={`${strategy.name} strategy`}
          className={`rounded-lg border bg-white p-4 shadow-sm ${
            strategy.key === "competitive" ? "border-accent-600" : "border-slate-200"
          }`}
        >
          <header className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">{strategy.name}</h3>
            {strategy.is_user_modified && <Badge tone="slate">agent-set price</Badge>}
          </header>

          <label htmlFor={`price-${strategy.id}`} className="field-label">
            Proposed list price
          </label>
          <div className="relative">
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-500"
            >
              $
            </span>
            <input
              id={`price-${strategy.id}`}
              type="text"
              inputMode="numeric"
              className="field-input pl-7 text-lg font-semibold tabular-nums"
              value={drafts[strategy.id] ?? strategy.list_price.toLocaleString("en-US")}
              disabled={busyId === strategy.id}
              onChange={(e) => setDrafts((d) => ({ ...d, [strategy.id]: e.target.value }))}
              onBlur={() => commit(strategy)}
              onKeyDown={(e) => {
                // Commit directly; routing Enter through blur() is fragile in
                // some embedded webviews.
                if (e.key === "Enter") {
                  e.preventDefault();
                  commit(strategy);
                }
              }}
            />
          </div>

          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">vs. indicated value</dt>
              <dd className="font-medium tabular-nums">
                {pct(strategy.derived.pct_vs_value)} ({money(strategy.derived.dollar_vs_value)})
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Position among comps</dt>
              <dd className="tabular-nums">
                {strategy.derived.position_percentile === null
                  ? "—"
                  : `above ${strategy.derived.position_percentile.toFixed(0)}% of adjusted values`}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Expected buyer interest</dt>
              <dd>
                <Badge tone={levelTone(strategy.derived.buyer_interest)}>
                  {strategy.derived.buyer_interest}
                </Badge>
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Price-reduction risk</dt>
              <dd>
                <Badge tone={riskTone(strategy.derived.price_reduction_risk)}>
                  {strategy.derived.price_reduction_risk}
                </Badge>
              </dd>
            </div>
          </dl>

          {strategy.derived.description && (
            <p className="mt-3 text-xs text-slate-600">{strategy.derived.description}</p>
          )}
          <p className="mt-2 text-xs text-slate-500">{strategy.derived.marketing_notes}</p>
          <p className="mt-2 border-t border-slate-100 pt-2 text-xxs text-slate-500">
            Scenario estimate vs. central {money(centralEstimate)}
            {strategy.valuation_id !== null && ` (valuation #${strategy.valuation_id})`}.{" "}
            {strategy.derived.assumptions}
          </p>
        </article>
      ))}
    </div>
  );
}
