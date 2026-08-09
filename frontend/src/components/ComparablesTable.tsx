"use client";

import { Fragment, useMemo, useState } from "react";
import type { Comparable } from "@/lib/types";
import { money, num, shortDate } from "@/lib/format";
import { Badge } from "./ui";
import { SimilarityBreakdown } from "./SimilarityBreakdown";

type SortKey = "address" | "sale_price" | "sale_date" | "square_feet" | "distance" | "similarity";

export interface ComparablesTableProps {
  comparables: Comparable[];
  onToggleInclude: (comp: Comparable, included: boolean) => void;
  onExclusionReason: (comp: Comparable, reason: string) => void;
  onMultiplierChange: (comp: Comparable, value: number) => void;
  onDelete: (comp: Comparable) => void;
  busyId?: number | null;
}

function sortValue(comp: Comparable, key: SortKey): string | number {
  switch (key) {
    case "address":
      return comp.address.toLowerCase();
    case "sale_price":
      return comp.sale_price;
    case "sale_date":
      return comp.sale_date;
    case "square_feet":
      return comp.square_feet;
    case "distance":
      return comp.effective_distance_miles ?? Number.POSITIVE_INFINITY;
    case "similarity":
      return comp.selection?.similarity_score ?? -1;
  }
}

function staleness(saleDate: string): "recent" | "aging" | "stale" {
  const months = (Date.now() - new Date(saleDate).getTime()) / (1000 * 3600 * 24 * 30.44);
  if (months <= 6) return "recent";
  if (months <= 12) return "aging";
  return "stale";
}

// Inline two-step delete: native confirm() dialogs are blocked in some
// embedded webviews and are poor UX; this keeps the confirmation visible,
// accessible, and testable.
function DeleteControl({
  comp,
  onDelete,
}: {
  comp: Comparable;
  onDelete: (comp: Comparable) => void;
}) {
  const [arming, setArming] = useState(false);
  if (!arming) {
    return (
      <button
        type="button"
        className="cursor-pointer text-xs text-red-700 underline-offset-2 hover:underline"
        onClick={() => setArming(true)}
      >
        Delete<span className="sr-only"> {comp.address}</span>
      </button>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <button
        type="button"
        className="cursor-pointer rounded bg-red-700 px-1.5 py-0.5 text-xs font-medium text-white hover:bg-red-800"
        onClick={() => onDelete(comp)}
      >
        Confirm delete<span className="sr-only"> {comp.address}</span>
      </button>
      <button
        type="button"
        className="cursor-pointer text-xs text-slate-500 underline-offset-2 hover:underline"
        onClick={() => setArming(false)}
      >
        Cancel
      </button>
    </span>
  );
}

export function ComparablesTable({
  comparables,
  onToggleInclude,
  onExclusionReason,
  onMultiplierChange,
  onDelete,
  busyId,
}: ComparablesTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("similarity");
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState("");
  const [includedOnly, setIncludedOnly] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const rows = useMemo(() => {
    let out = [...comparables];
    const query = filter.trim().toLowerCase();
    if (query) {
      out = out.filter((comp) =>
        `${comp.address} ${comp.city ?? ""} ${comp.zip_code ?? ""}`.toLowerCase().includes(query),
      );
    }
    if (includedOnly) out = out.filter((comp) => comp.selection?.included !== false);
    out.sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });
    return out;
  }, [comparables, filter, includedOnly, sortKey, sortAsc]);

  function header(key: SortKey, label: string, numeric = false) {
    const active = sortKey === key;
    return (
      <th scope="col" className={numeric ? "num" : ""} aria-sort={active ? (sortAsc ? "ascending" : "descending") : undefined}>
        <button
          type="button"
          className="inline-flex items-center gap-1 font-semibold uppercase"
          onClick={() => {
            if (active) setSortAsc(!sortAsc);
            else {
              setSortKey(key);
              setSortAsc(key === "address");
            }
          }}
        >
          {label}
          <span aria-hidden="true" className="text-slate-400">
            {active ? (sortAsc ? "↑" : "↓") : "↕"}
          </span>
        </button>
      </th>
    );
  }

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="grow sm:max-w-xs">
          <label htmlFor="comp-filter" className="sr-only">
            Filter comparables by address
          </label>
          <input
            id="comp-filter"
            type="search"
            className="field-input"
            placeholder="Filter by address, city, ZIP…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300"
            checked={includedOnly}
            onChange={(e) => setIncludedOnly(e.target.checked)}
          />
          Included only
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <caption>
            {rows.length} of {comparables.length} comparable(s) shown. Toggle
            &ldquo;Include&rdquo; to control which sales enter the valuation; expand a row
            for its full similarity breakdown.
          </caption>
          <thead>
            <tr>
              <th scope="col">
                <span className="sr-only">Include in analysis</span>Incl.
              </th>
              {header("address", "Address")}
              {header("sale_price", "Sale price", true)}
              {header("sale_date", "Sale date")}
              {header("square_feet", "Sq ft", true)}
              <th scope="col" className="num">Bd/Ba</th>
              {header("distance", "Dist (mi)", true)}
              {header("similarity", "Similarity", true)}
              <th scope="col" className="num">Weight ×</th>
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((comp) => {
              const included = comp.selection?.included !== false;
              const similarity = comp.selection?.similarity_score;
              const expanded = expandedId === comp.id;
              const age = staleness(comp.sale_date);
              return (
                <Fragment key={comp.id}>
                  <tr className={included ? "" : "bg-slate-50 text-slate-400"}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Include ${comp.address} in the analysis`}
                        className="h-4 w-4 rounded border-slate-300"
                        checked={included}
                        disabled={busyId === comp.id}
                        onChange={(e) => onToggleInclude(comp, e.target.checked)}
                      />
                    </td>
                    <td>
                      <span className={`font-medium ${included ? "text-slate-800" : ""}`}>
                        {comp.address}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {comp.city ?? ""} {comp.zip_code ?? ""}
                        {comp.source ? ` · ${comp.source}` : ""}
                      </span>
                      {!included && (
                        <span className="mt-1 block">
                          <label className="sr-only" htmlFor={`excl-${comp.id}`}>
                            Reason for excluding {comp.address}
                          </label>
                          <input
                            id={`excl-${comp.id}`}
                            type="text"
                            className="field-input max-w-xs text-xs"
                            placeholder="Reason for exclusion (recorded in audit trail)"
                            defaultValue={comp.selection?.exclusion_reason ?? ""}
                            onBlur={(e) => {
                              if (e.target.value !== (comp.selection?.exclusion_reason ?? ""))
                                onExclusionReason(comp, e.target.value);
                            }}
                          />
                        </span>
                      )}
                    </td>
                    <td className="num">{money(comp.sale_price)}</td>
                    <td className="whitespace-nowrap">
                      {shortDate(comp.sale_date)}{" "}
                      {age !== "recent" && (
                        <Badge tone={age === "aging" ? "amber" : "red"}>
                          {age === "aging" ? "6–12 mo" : ">12 mo"}
                        </Badge>
                      )}
                    </td>
                    <td className="num">{num(comp.square_feet)}</td>
                    <td className="num whitespace-nowrap">
                      {comp.bedrooms}/{comp.bathrooms}
                    </td>
                    <td className="num">
                      {comp.effective_distance_miles === null
                        ? "—"
                        : comp.effective_distance_miles.toFixed(2)}
                    </td>
                    <td className="num">
                      {similarity === null || similarity === undefined ? (
                        <span className="text-slate-400">not scored</span>
                      ) : (
                        <button
                          type="button"
                          className="font-semibold text-accent-700 underline-offset-2 hover:underline"
                          aria-expanded={expanded}
                          onClick={() => setExpandedId(expanded ? null : comp.id)}
                        >
                          {similarity.toFixed(0)}
                          <span className="sr-only"> — toggle breakdown</span>
                        </button>
                      )}
                    </td>
                    <td className="num">
                      <label className="sr-only" htmlFor={`mult-${comp.id}`}>
                        Weight multiplier for {comp.address}
                      </label>
                      <input
                        id={`mult-${comp.id}`}
                        type="number"
                        min={0}
                        max={10}
                        step={0.1}
                        className="field-input w-16 text-right"
                        defaultValue={comp.selection?.user_weight_multiplier ?? 1}
                        disabled={!included || busyId === comp.id}
                        onBlur={(e) => {
                          const value = Number(e.target.value);
                          if (
                            !Number.isNaN(value) &&
                            value !== (comp.selection?.user_weight_multiplier ?? 1)
                          )
                            onMultiplierChange(comp, value);
                        }}
                      />
                    </td>
                    <td>
                      <DeleteControl comp={comp} onDelete={onDelete} />
                    </td>
                  </tr>
                  {expanded && comp.selection?.similarity_breakdown && (
                    <tr>
                      <td colSpan={10} className="bg-slate-50">
                        <SimilarityBreakdown breakdown={comp.selection.similarity_breakdown} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
