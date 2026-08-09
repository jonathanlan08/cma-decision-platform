"use client";

import { useState } from "react";
import type { Adjustment, Comparable } from "@/lib/types";
import { money, num, titleCase } from "@/lib/format";
import { Badge } from "./ui";

export interface AdjustmentGridProps {
  comparable: Comparable;
  onEditAmount: (adjustment: Adjustment, amount: number) => void;
  onDeleteAdjustment: (adjustment: Adjustment) => void;
  onAddManual: (values: { category: string; amount: number; explanation: string }) => void;
}

// One comparable's adjustment grid: category, subject vs comp, unit basis,
// editable dollar amount, direction, origin, and running total.
export function AdjustmentGrid({
  comparable,
  onEditAmount,
  onDeleteAdjustment,
  onAddManual,
}: AdjustmentGridProps) {
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [explanation, setExplanation] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const total = comparable.adjustments.reduce((sum, adj) => sum + adj.amount, 0);

  function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    const parsed = Number(amount);
    if (!category.trim()) {
      setFormError("Category is required.");
      return;
    }
    if (amount.trim() === "" || Number.isNaN(parsed)) {
      setFormError("Enter a dollar amount (negative adjusts the comparable downward).");
      return;
    }
    setFormError(null);
    onAddManual({ category: category.trim(), amount: parsed, explanation: explanation.trim() });
    setCategory("");
    setAmount("");
    setExplanation("");
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-800">
          {comparable.address}
          <span className="ml-2 font-normal text-slate-500">
            sold {money(comparable.sale_price)} · {num(comparable.square_feet)} sq ft
          </span>
        </h3>
        {comparable.gross_adjustment_pct !== null &&
          comparable.gross_adjustment_pct > 0.25 && (
            <Badge tone="amber">
              Gross adjustments {(comparable.gross_adjustment_pct * 100).toFixed(0)}% of price
            </Badge>
          )}
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <caption className="sr-only">Adjustments for {comparable.address}</caption>
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col">Subject</th>
              <th scope="col">Comparable</th>
              <th scope="col">Unit basis</th>
              <th scope="col" className="num">Amount ($)</th>
              <th scope="col">Direction</th>
              <th scope="col">Origin</th>
              <th scope="col"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {comparable.adjustments.length === 0 && (
              <tr>
                <td colSpan={8} className="text-center text-slate-400">
                  No adjustments. The comparable matches the subject on every priced
                  characteristic, or suggestions have not been generated yet.
                </td>
              </tr>
            )}
            {comparable.adjustments.map((adj) => (
              <tr key={adj.id}>
                <td className="font-medium">{titleCase(adj.category)}</td>
                <td>{adj.subject_value ?? "—"}</td>
                <td>{adj.comparable_value ?? "—"}</td>
                <td className="text-xs">
                  {adj.unit_description ?? "—"}
                  {adj.explanation && (
                    <span className="block text-slate-500">{adj.explanation}</span>
                  )}
                </td>
                <td className="num">
                  <label className="sr-only" htmlFor={`adj-${adj.id}`}>
                    {titleCase(adj.category)} adjustment amount for {comparable.address}
                  </label>
                  <input
                    id={`adj-${adj.id}`}
                    type="number"
                    step={100}
                    className="field-input w-28 text-right"
                    defaultValue={adj.amount}
                    onBlur={(e) => {
                      const value = Number(e.target.value);
                      if (!Number.isNaN(value) && value !== adj.amount)
                        onEditAmount(adj, value);
                    }}
                  />
                </td>
                <td>
                  {adj.direction === "upward" && <Badge tone="green">upward ↑</Badge>}
                  {adj.direction === "downward" && <Badge tone="red">downward ↓</Badge>}
                  {adj.direction === "none" && <Badge tone="slate">none</Badge>}
                </td>
                <td>
                  <Badge tone={adj.source === "suggested" ? "blue" : "slate"}>
                    {adj.source}
                  </Badge>
                </td>
                <td>
                  <button
                    type="button"
                    className="text-xs text-red-700 underline-offset-2 hover:underline"
                    onClick={() => onDeleteAdjustment(adj)}
                  >
                    Delete
                    <span className="sr-only">
                      {" "}{titleCase(adj.category)} adjustment for {comparable.address}
                    </span>
                  </button>
                </td>
              </tr>
            ))}
            <tr className="bg-slate-50 font-semibold">
              <td colSpan={4}>Adjusted value</td>
              <td className="num">
                {money(comparable.adjusted_price)}
                <span className="block text-xs font-normal text-slate-500">
                  net {total >= 0 ? "+" : ""}{money(total)}
                  {comparable.adjusted_ppsf !== null &&
                    ` · ${money(comparable.adjusted_ppsf)}/sq ft`}
                </span>
              </td>
              <td colSpan={3} />
            </tr>
          </tbody>
        </table>
      </div>

      <form onSubmit={handleAdd} className="mt-2 flex flex-wrap items-end gap-2" noValidate>
        <div>
          <label htmlFor={`add-cat-${comparable.id}`} className="field-label">
            Add manual adjustment
          </label>
          <input
            id={`add-cat-${comparable.id}`}
            type="text"
            className="field-input w-40"
            placeholder="Category (e.g. view)"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor={`add-amt-${comparable.id}`} className="field-label">
            Amount ($)
          </label>
          <input
            id={`add-amt-${comparable.id}`}
            type="number"
            step={100}
            className="field-input w-32"
            placeholder="-10000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <div className="grow">
          <label htmlFor={`add-why-${comparable.id}`} className="field-label">
            Explanation
          </label>
          <input
            id={`add-why-${comparable.id}`}
            type="text"
            className="field-input"
            placeholder="Why this adjustment applies"
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
          />
        </div>
        <button type="submit" className="btn-secondary">
          Add
        </button>
        {formError && (
          <p role="alert" className="w-full text-xs font-medium text-red-700">
            {formError}
          </p>
        )}
      </form>
    </div>
  );
}
