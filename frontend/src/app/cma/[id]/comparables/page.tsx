"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Comparable, Config } from "@/lib/types";
import { Card, EmptyState, ErrorBox, Spinner, WarningBox } from "@/components/ui";
import { CompMap } from "@/components/CompMap";
import { ComparablesTable } from "@/components/ComparablesTable";
import { ComparableForm, type ComparableFormValues } from "@/components/ComparableForm";
import { CsvUpload } from "@/components/CsvUpload";
import { WeightsEditor } from "@/components/WeightsEditor";
import { useCma } from "../cma-context";

export default function ComparablesPage() {
  const { cma, reload } = useCma();
  const [comparables, setComparables] = useState<Comparable[] | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [scoring, setScoring] = useState(false);
  const [savingWeights, setSavingWeights] = useState(false);
  const [adding, setAdding] = useState(false);

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.listComparables(cma.id), api.getConfig(cma.id)])
      .then(([comps, cfg]) => {
        setComparables(comps);
        setConfig(cfg);
      })
      .catch((e: ApiError) => setError(e.message));
  }, [cma.id]);

  useEffect(load, [load]);

  async function guard<T>(work: () => Promise<T>) {
    setError(null);
    try {
      await work();
    } catch (e) {
      setError((e as ApiError).message);
    }
  }

  async function recalcSimilarity() {
    setScoring(true);
    await guard(async () => {
      const updated = await api.recalcSimilarity(cma.id);
      setComparables(updated);
    });
    setScoring(false);
  }

  const replaceComp = (updated: Comparable) =>
    setComparables((list) => (list ?? []).map((c) => (c.id === updated.id ? updated : c)));

  return (
    <div className="space-y-4">
      <Card title="Import comparable sales">
        <CsvUpload
          cmaId={cma.id}
          onImported={() => {
            load();
            reload();
          }}
        />
      </Card>

      <Card title="Add a comparable manually">
        <details>
          <summary className="cursor-pointer text-sm font-medium text-accent-700">
            Show manual entry form
          </summary>
          <div className="mt-3">
            <ComparableForm
              saving={adding}
              onSave={async (values: ComparableFormValues) => {
                setAdding(true);
                await guard(async () => {
                  await api.addComparable(cma.id, {
                    ...values,
                    city: values.city || null,
                    zip_code: values.zip_code || null,
                    notes: values.notes || null,
                    source: "manual-entry",
                  });
                  load();
                  reload();
                });
                setAdding(false);
              }}
            />
          </div>
        </details>
      </Card>

      <Card
        title={`Comparables (${comparables?.length ?? "…"})`}
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={recalcSimilarity}
              disabled={scoring || !cma.subject}
            >
              {scoring ? "Scoring…" : "Recalculate similarity"}
            </button>
            <Link href={`/cma/${cma.id}/adjustments`} className="btn-primary">
              Next: adjustments →
            </Link>
          </div>
        }
      >
        {!cma.subject && (
          <WarningBox>
            Enter the <Link href={`/cma/${cma.id}/subject`} className="underline">subject
            property</Link> first — similarity scoring needs it.
          </WarningBox>
        )}
        {error && <ErrorBox message={error} onRetry={load} />}
        {!comparables && !error && <Spinner label="Loading comparables…" />}
        {comparables && comparables.length === 0 && (
          <EmptyState title="No comparables yet">
            <p>Upload a CSV above or add sales manually. The bundled synthetic sample is at
              <code className="mx-1 rounded bg-slate-100 px-1">data/sample/comparables_sample.csv</code>.
            </p>
          </EmptyState>
        )}
        {comparables && comparables.length > 0 && (
          <ComparablesTable
            comparables={comparables}
            busyId={busyId}
            onToggleInclude={(comp, included) =>
              guard(async () => {
                setBusyId(comp.id);
                replaceComp(await api.updateSelection(comp.id, { included }));
                setBusyId(null);
                reload();
              })
            }
            onExclusionReason={(comp, reason) =>
              guard(async () => {
                replaceComp(await api.updateSelection(comp.id, { exclusion_reason: reason }));
              })
            }
            onMultiplierChange={(comp, value) =>
              guard(async () => {
                replaceComp(
                  await api.updateSelection(comp.id, { user_weight_multiplier: value }),
                );
              })
            }
            onDelete={(comp) =>
              guard(async () => {
                if (!window.confirm(`Delete comparable "${comp.address}"? This is recorded in the audit trail.`)) return;
                await api.deleteComparable(comp.id);
                load();
                reload();
              })
            }
          />
        )}
      </Card>

      {cma.subject && comparables && comparables.length > 0 && (
        <Card title="Proximity map">
          <CompMap subject={cma.subject} comparables={comparables} />
        </Card>
      )}

      {config && (
        <Card title="Similarity weights (this analysis)">
          <WeightsEditor
            config={config}
            saving={savingWeights}
            onSave={(weights) =>
              guard(async () => {
                setSavingWeights(true);
                setConfig(await api.updateConfig(cma.id, { weights }));
                if (comparables && comparables.length > 0 && cma.subject) {
                  setComparables(await api.recalcSimilarity(cma.id));
                }
                setSavingWeights(false);
              })
            }
          />
        </Card>
      )}
    </div>
  );
}
