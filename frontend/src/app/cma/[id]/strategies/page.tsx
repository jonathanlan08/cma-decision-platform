"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { Strategy } from "@/lib/types";
import { Card, EmptyState, ErrorBox, Spinner, WarningBox } from "@/components/ui";
import { StaleBanner } from "@/components/StaleBanner";
import { StrategyCompare } from "@/components/StrategyCompare";
import { useCma } from "../cma-context";

export default function StrategiesPage() {
  const { cma, reload } = useCma();
  const [strategies, setStrategies] = useState<Strategy[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const central = cma.latest_valuation?.central_estimate ?? null;
  // Strategies remember which valuation produced them; a mismatch with the
  // latest valuation means their prices/labels reference an older estimate.
  const latestValuationId = cma.latest_valuation?.id ?? null;
  const strategiesOutdated =
    latestValuationId !== null &&
    (strategies ?? []).some(
      (s) => s.valuation_id !== null && s.valuation_id !== latestValuationId,
    );

  const load = useCallback(() => {
    setError(null);
    api
      .listStrategies(cma.id)
      .then(setStrategies)
      .catch((e: ApiError) => setError(e.message));
  }, [cma.id]);

  useEffect(load, [load]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      setStrategies(await api.generateStrategies(cma.id));
      reload();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card
        title="Listing strategy comparison"
        actions={
          <button
            type="button"
            className="btn-primary"
            onClick={generate}
            disabled={generating || central === null}
          >
            {generating
              ? "Generating…"
              : strategies && strategies.length > 0
                ? "Refresh from latest valuation"
                : "Generate strategies"}
          </button>
        }
      >
        <p className="mb-3 text-sm text-slate-500">
          Three scenarios priced off the central estimate. Edit any price to compare your
          own scenario; interest and risk labels update from documented thresholds. These
          are qualitative scenario estimates, not validated predictions of market outcomes.
        </p>
        <StaleBanner
          cma={cma}
          onRefreshed={() => {
            load();
            reload();
          }}
        />
        {!cma.latest_valuation?.stale && strategiesOutdated && (
          <WarningBox>
            These strategies were generated from an earlier valuation, so their
            prices and labels may not match the current central estimate.{" "}
            <button
              type="button"
              className="cursor-pointer font-medium underline"
              disabled={generating}
              onClick={generate}
            >
              Refresh them from the latest valuation
            </button>
            .
          </WarningBox>
        )}

        {central === null && (
          <EmptyState title="Valuation needed first">
            <p>
              Strategies are priced from the central estimate. Run the{" "}
              <Link href={`/cma/${cma.id}/valuation`} className="text-accent-700 underline">
                valuation step
              </Link>{" "}
              first.
            </p>
          </EmptyState>
        )}
        {error && <ErrorBox message={error} onRetry={load} />}
        {!strategies && !error && central !== null && <Spinner label="Loading strategies…" />}
        {strategies && strategies.length === 0 && central !== null && (
          <EmptyState title="No strategies yet">
            <p>Press “Generate strategies” to create the three standard scenarios.</p>
          </EmptyState>
        )}

        {strategies && strategies.length > 0 && central !== null && (
          <StrategyCompare
            strategies={strategies}
            centralEstimate={central}
            busyId={busyId}
            onPriceChange={async (strategy, price) => {
              setBusyId(strategy.id);
              setError(null);
              try {
                const updated = await api.updateStrategy(strategy.id, price);
                setStrategies((list) =>
                  (list ?? []).map((s) => (s.id === updated.id ? updated : s)),
                );
              } catch (e) {
                setError((e as ApiError).message);
              } finally {
                setBusyId(null);
              }
            }}
          />
        )}

        {strategies && strategies.length > 0 && (
          <div className="mt-4 flex justify-end">
            <Link href={`/cma/${cma.id}/report`} className="btn-primary">
              Next: report →
            </Link>
          </div>
        )}
      </Card>
    </div>
  );
}
