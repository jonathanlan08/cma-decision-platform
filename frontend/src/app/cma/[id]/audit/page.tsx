"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";
import { Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";
import { Badge } from "@/components/ui";
import { dateTime, titleCase } from "@/lib/format";
import { useCma } from "../cma-context";

const EVENT_TONES: Record<string, "green" | "amber" | "red" | "slate" | "blue"> = {
  comparable_excluded: "amber",
  comparable_deleted: "red",
  adjustment_deleted: "red",
  weight_override: "amber",
  adjustment_edited: "amber",
  strategy_price_changed: "amber",
  valuation_recalculated: "blue",
  report_generated: "green",
};

export default function AuditPage() {
  const { cma } = useCma();
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = useCallback(() => {
    setError(null);
    api
      .listAudit(cma.id)
      .then(setEvents)
      .catch((e: ApiError) => setError(e.message));
  }, [cma.id]);

  useEffect(load, [load]);

  return (
    <Card title="Audit trail">
      <p className="mb-4 text-sm text-slate-500">
        Every change that can affect a number in this analysis, newest first: data edits,
        inclusion decisions, weight and assumption changes, overrides, recalculations, and
        report generation. Each event records who acted, when, and under which calculation
        version.
      </p>
      {error && <ErrorBox message={error} onRetry={load} />}
      {!events && !error && <Spinner label="Loading audit trail…" />}
      {events && events.length === 0 && (
        <EmptyState title="No events recorded yet" />
      )}
      {events && events.length > 0 && (
        <ol className="space-y-0 divide-y divide-slate-100">
          {events.map((event) => (
            <li key={event.id} className="py-2.5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <time
                  dateTime={event.timestamp}
                  className="w-40 shrink-0 text-xs tabular-nums text-slate-500"
                >
                  {dateTime(event.timestamp)}
                </time>
                <Badge tone={EVENT_TONES[event.event_type] ?? "slate"}>
                  {titleCase(event.event_type)}
                </Badge>
                <p className="min-w-[12rem] flex-1 text-sm text-slate-800">{event.summary}</p>
                <span className="text-xxs text-slate-500">
                  {event.actor} · {event.calc_version}
                </span>
                {event.details && (
                  <button
                    type="button"
                    className="text-xs text-accent-700 underline-offset-2 hover:underline"
                    aria-expanded={expandedId === event.id}
                    onClick={() => setExpandedId(expandedId === event.id ? null : event.id)}
                  >
                    {expandedId === event.id ? "Hide details" : "Details"}
                  </button>
                )}
              </div>
              {expandedId === event.id && event.details && (
                <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-3 text-xs text-slate-700">
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              )}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}
