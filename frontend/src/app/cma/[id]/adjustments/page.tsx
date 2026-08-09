"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Comparable, Config } from "@/lib/types";
import { Card, EmptyState, ErrorBox, Spinner, WarningBox } from "@/components/ui";
import { AdjustmentGrid } from "@/components/AdjustmentGrid";
import { titleCase } from "@/lib/format";
import { useCma } from "../cma-context";

const ASSUMPTION_LABELS: Record<string, string> = {
  monthly_market_pct: "Market movement (fraction/month, e.g. 0.003 = 0.3%)",
  gla_per_sqft: "Living area ($/sq ft)",
  lot_per_sqft: "Lot size ($/sq ft)",
  per_bedroom: "Per bedroom ($)",
  per_bathroom: "Per bathroom ($)",
  per_condition_step: "Per condition step ($)",
  per_parking_space: "Per parking space ($)",
  pool_value: "Pool (flat $)",
};

export default function AdjustmentsPage() {
  const { cma, reload } = useCma();
  const [comparables, setComparables] = useState<Comparable[] | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [assumptions, setAssumptions] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [savingAssumptions, setSavingAssumptions] = useState(false);

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.listComparables(cma.id), api.getConfig(cma.id)])
      .then(([comps, cfg]) => {
        setComparables(comps);
        setConfig(cfg);
        setAssumptions({ ...cfg.assumptions });
      })
      .catch((e: ApiError) => setError(e.message));
  }, [cma.id]);

  useEffect(load, [load]);

  async function guard(work: () => Promise<void>) {
    setError(null);
    try {
      await work();
    } catch (e) {
      setError((e as ApiError).message);
    }
  }

  const assumptionsDirty =
    config !== null &&
    Object.keys(assumptions).some((key) => assumptions[key] !== config.assumptions[key]);

  async function saveAssumptions() {
    setSavingAssumptions(true);
    await guard(async () => {
      setConfig(await api.updateConfig(cma.id, { assumptions }));
    });
    setSavingAssumptions(false);
  }

  // Generating always uses the assumptions the user can SEE: unsaved edits are
  // persisted first, so the backend never computes from values the screen no
  // longer shows.
  async function generateSuggestions() {
    setSuggesting(true);
    await guard(async () => {
      if (assumptionsDirty) {
        setConfig(await api.updateConfig(cma.id, { assumptions }));
      }
      setComparables(await api.suggestAdjustments(cma.id));
      // Refetch: generating clears the outdated-suggestions flag server-side.
      setConfig(await api.getConfig(cma.id));
      reload();
    });
    setSuggesting(false);
  }

  const included = (comparables ?? []).filter((c) => c.selection?.included !== false);

  return (
    <div className="space-y-4">
      <Card title="Adjustment assumptions (sample values: review before relying on them)">
        <p className="mb-3 text-sm text-slate-500">
          Suggested adjustments are computed from these per-analysis assumptions. They are
          demonstration defaults, not market standards. Set them from your own market
          knowledge. Changes are recorded in the audit trail.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveAssumptions();
          }}
        >
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Object.entries(assumptions).map(([key, value]) => (
              <div key={key}>
                <label htmlFor={`assume-${key}`} className="field-label">
                  {ASSUMPTION_LABELS[key] ?? titleCase(key)}
                </label>
                <input
                  id={`assume-${key}`}
                  type="number"
                  step="any"
                  className="field-input"
                  value={value}
                  onChange={(e) =>
                    setAssumptions((a) => ({ ...a, [key]: Number(e.target.value) || 0 }))
                  }
                />
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
            {assumptionsDirty && (
              <p className="text-xs font-medium text-amber-700">
                Unsaved changes (saved automatically when you generate)
              </p>
            )}
            <button type="submit" className="btn-secondary" disabled={savingAssumptions}>
              {savingAssumptions ? "Saving…" : "Save assumptions"}
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={suggesting || !cma.subject}
              onClick={generateSuggestions}
            >
              {suggesting ? "Generating…" : "Generate suggested adjustments"}
            </button>
          </div>
        </form>
        <p className="mt-2 text-xs text-slate-500">
          Regenerating replaces earlier <em>suggested</em> rows with fresh ones from the
          current assumptions; manual adjustments and your edits are preserved.
        </p>
      </Card>

      {!cma.subject && (
        <WarningBox>
          Enter the <Link href={`/cma/${cma.id}/subject`} className="underline">subject
          property</Link> before generating adjustments.
        </WarningBox>
      )}
      {config?.suggestions_outdated && (
        <WarningBox>
          The suggested adjustments below were generated from an earlier assumption
          set. Press “Generate suggested adjustments” so the amounts match the
          assumptions shown above; the valuation and report are blocked until then.
        </WarningBox>
      )}
      {error && <ErrorBox message={error} onRetry={load} />}
      {!comparables && !error && <Spinner label="Loading adjustments…" />}

      {comparables && included.length === 0 && (
        <EmptyState title="No included comparables">
          <p>
            Include at least one comparable on the{" "}
            <Link href={`/cma/${cma.id}/comparables`} className="text-accent-700 underline">
              comparables step
            </Link>
            .
          </p>
        </EmptyState>
      )}

      {included.map((comp) => (
        <Card key={comp.id}>
          <AdjustmentGrid
            comparable={comp}
            onEditAmount={(adj, amount) =>
              guard(async () => {
                await api.updateAdjustment(adj.id, { amount });
                setComparables(await api.listComparables(cma.id));
                reload(); // refresh the header's staleness flag
              })
            }
            onDeleteAdjustment={(adj) =>
              guard(async () => {
                await api.deleteAdjustment(adj.id);
                setComparables(await api.listComparables(cma.id));
                reload(); // refresh the header's staleness flag
              })
            }
            onAddManual={async (values) => {
              // Rethrows on failure so the grid keeps the user's draft.
              setError(null);
              try {
                await api.addAdjustment(comp.id, {
                  category: values.category,
                  amount: values.amount,
                  explanation: values.explanation || null,
                });
                setComparables(await api.listComparables(cma.id));
                reload(); // refresh the header's staleness flag
              } catch (e) {
                setError((e as ApiError).message);
                throw e;
              }
            }}
          />
        </Card>
      ))}

      {included.length > 0 && (
        <div className="flex justify-end">
          <Link href={`/cma/${cma.id}/valuation`} className="btn-primary">
            Next: valuation →
          </Link>
        </div>
      )}
    </div>
  );
}
