"use client";

import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { CMADetail } from "@/lib/types";
import { WarningBox } from "./ui";

// Shown wherever derived numbers appear once the CMA's inputs have changed
// after the last valuation. The backend also refuses to generate a report in
// this state, so this banner is the early, visible version of that gate; the
// button repairs it in one click instead of sending the user step-hopping.
export function StaleBanner({
  cma,
  onRefreshed,
}: {
  cma: CMADetail;
  onRefreshed?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!cma.latest_valuation?.stale) return null;

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      // Full repair chain. Outdated suggested adjustments must be regenerated
      // FIRST, or the recalculated valuation still fails the report gate.
      const config = await api.getConfig(cma.id);
      if (config.suggestions_outdated !== false) {
        await api.suggestAdjustments(cma.id);
      }
      await api.recalcValuation(cma.id);
      await api.generateStrategies(cma.id);
      onRefreshed?.();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <WarningBox>
      <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span>
          Inputs have changed since the last valuation was calculated, so the numbers
          shown may be outdated.
        </span>
        <button
          type="button"
          className="btn-secondary whitespace-nowrap"
          disabled={busy}
          onClick={refresh}
        >
          {busy ? "Refreshing…" : "Refresh the full analysis"}
        </button>
        <span>
          or review it on the{" "}
          <Link href={`/cma/${cma.id}/valuation`} className="font-medium underline">
            valuation step
          </Link>
          .
        </span>
      </span>
      {error && (
        <p role="alert" className="mt-1 text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </WarningBox>
  );
}
