"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Config, Sensitivity, Valuation } from "@/lib/types";
import { Card, EmptyState, ErrorBox, Spinner, WarningBox } from "@/components/ui";
import { SensitivityPanel } from "@/components/SensitivityPanel";
import { ValuationChart } from "@/components/ValuationChart";
import { money, num, pct } from "@/lib/format";
import { useCma } from "../cma-context";

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <dt className="text-xxs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-lg font-bold tabular-nums text-slate-900">{value}</dd>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export default function ValuationPage() {
  const { cma, reload } = useCma();
  const [valuation, setValuation] = useState<Valuation | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [sensitivity, setSensitivity] = useState<Sensitivity | null>(null);
  const [rangeK, setRangeK] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [calculating, setCalculating] = useState(false);

  const load = useCallback(() => {
    setError(null);
    Promise.all([
      api.getValuation(cma.id).catch((e: ApiError) => {
        if (e.status === 404) return null;
        throw e;
      }),
      api.getConfig(cma.id),
    ])
      .then(([val, cfg]) => {
        setValuation(val);
        setConfig(cfg);
        setRangeK(String(cfg.reconciliation.range_k ?? 1));
        setLoaded(true);
        if (val?.central_estimate != null) {
          api.getSensitivity(cma.id).then(setSensitivity).catch(() => setSensitivity(null));
        }
      })
      .catch((e: ApiError) => setError(e.message));
  }, [cma.id]);

  useEffect(load, [load]);

  async function recalc() {
    setCalculating(true);
    setError(null);
    try {
      const k = Number(rangeK);
      if (!Number.isNaN(k) && k > 0 && k !== config?.reconciliation.range_k) {
        setConfig(await api.updateConfig(cma.id, { reconciliation: { range_k: k } }));
      }
      setValuation(await api.recalcValuation(cma.id));
      api.getSensitivity(cma.id).then(setSensitivity).catch(() => setSensitivity(null));
      reload();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setCalculating(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card
        title="Value reconciliation"
        actions={
          <div className="flex items-end gap-2">
            <div>
              <label htmlFor="range-k" className="field-label">
                Range width (k × std dev)
              </label>
              <input
                id="range-k"
                type="number"
                min={0.1}
                max={3}
                step={0.1}
                className="field-input w-20"
                value={rangeK}
                onChange={(e) => setRangeK(e.target.value)}
              />
            </div>
            <button
              type="button"
              className="btn-primary"
              onClick={recalc}
              disabled={calculating || !cma.subject}
            >
              {calculating ? "Calculating…" : valuation ? "Recalculate valuation" : "Calculate valuation"}
            </button>
          </div>
        }
      >
        <p className="mb-2 text-sm text-slate-500">
          Included comparables are weighted by similarity × your weight multiplier, then
          reconciled into a central estimate with a dispersion-based range. This is an
          analytical estimate, not a statistical confidence interval or an appraisal.
        </p>
        {!cma.subject && (
          <WarningBox>
            Enter the <Link href={`/cma/${cma.id}/subject`} className="underline">subject
            property</Link> first.
          </WarningBox>
        )}
        {error && <ErrorBox message={error} onRetry={load} />}
        {!loaded && !error && <Spinner label="Loading valuation…" />}
        {loaded && !valuation && (
          <EmptyState title="No valuation yet">
            <p>Press “Calculate valuation” to reconcile the included comparables.</p>
          </EmptyState>
        )}

        {valuation && (
          <>
            <div className="overflow-hidden rounded-lg border-2 border-accent-700">
              <dl className="grid grid-cols-1 divide-y divide-slate-200 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
                <div className="bg-white px-4 py-4 text-center">
                  <dt className="text-xxs font-semibold uppercase tracking-wide text-slate-500">
                    Low estimate
                  </dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-700 sm:text-xl">
                    {money(valuation.low_estimate)}
                  </dd>
                </div>
                <div className="bg-accent-50 px-4 py-4 text-center">
                  <dt className="text-xxs font-semibold uppercase tracking-wide text-accent-800">
                    Central estimate
                  </dt>
                  <dd className="mt-1 text-2xl font-bold tabular-nums text-accent-800 sm:text-3xl">
                    {money(valuation.central_estimate)}
                  </dd>
                  <p className="mt-0.5 text-xxs text-slate-500">
                    {valuation.included_count} comparable(s) · {valuation.calc_version}
                  </p>
                </div>
                <div className="bg-white px-4 py-4 text-center">
                  <dt className="text-xxs font-semibold uppercase tracking-wide text-slate-500">
                    High estimate
                  </dt>
                  <dd className="mt-1 text-lg font-semibold tabular-nums text-slate-700 sm:text-xl">
                    {money(valuation.high_estimate)}
                  </dd>
                </div>
              </dl>
            </div>
            <dl className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Stat label="Median adjusted" value={money(valuation.median_adjusted)} />
              <Stat
                label="Weighted $/sq ft"
                value={valuation.weighted_ppsf ? money(valuation.weighted_ppsf) : "—"}
              />
              <Stat
                label="Dispersion"
                value={valuation.dispersion ? money(valuation.dispersion) : "—"}
                sub={valuation.cov !== null ? `CV ${pct(valuation.cov, 1)}` : undefined}
              />
            </dl>

            {(valuation.warnings ?? []).map((warning, index) => (
              <WarningBox key={index}>{warning.message}</WarningBox>
            ))}

            <ValuationChart valuation={valuation} />

            {valuation.per_comparable && valuation.per_comparable.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="data-table">
                  <caption>
                    How much each comparable influenced the central estimate. Weight =
                    (similarity ÷ 100) × your multiplier, normalized to sum to 100%.
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Comparable</th>
                      <th scope="col" className="num">Adjusted value</th>
                      <th scope="col" className="num">Similarity</th>
                      <th scope="col" className="num">Your multiplier</th>
                      <th scope="col" className="num">Influence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {valuation.per_comparable.map((entry) => (
                      <tr key={entry.comp_id}>
                        <td>{entry.address}</td>
                        <td className="num">{money(entry.adjusted_price)}</td>
                        <td className="num">
                          {entry.similarity === null ? "—" : num(entry.similarity)}
                        </td>
                        <td className="num">{entry.multiplier.toFixed(2)}×</td>
                        <td className="num font-semibold">{entry.influence_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 flex justify-end">
              <Link href={`/cma/${cma.id}/strategies`} className="btn-primary">
                Next: listing strategies →
              </Link>
            </div>
          </>
        )}
      </Card>

      {valuation && sensitivity && sensitivity.items.length > 0 && (
        <Card title="Which assumptions move the estimate?">
          <SensitivityPanel data={sensitivity} />
        </Card>
      )}
    </div>
  );
}
