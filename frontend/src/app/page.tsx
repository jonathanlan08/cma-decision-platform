"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { CMAStatus, CMASummary } from "@/lib/types";
import { money, dateTime } from "@/lib/format";
import { Badge, Card, EmptyState, ErrorBox, Spinner } from "@/components/ui";

const STATUS_TONE = { draft: "amber", completed: "green", archived: "slate" } as const;

// The lifecycle transitions each status offers on the dashboard.
const STATUS_ACTIONS: Record<CMAStatus, { label: string; to: CMAStatus }[]> = {
  draft: [
    { label: "Mark completed", to: "completed" },
    { label: "Archive", to: "archived" },
  ],
  completed: [
    { label: "Reopen as draft", to: "draft" },
    { label: "Archive", to: "archived" },
  ],
  archived: [{ label: "Restore to draft", to: "draft" }],
};

export default function DashboardPage() {
  const router = useRouter();
  const [cmas, setCmas] = useState<CMASummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [statusBusyId, setStatusBusyId] = useState<number | null>(null);

  async function changeStatus(cma: CMASummary, status: CMAStatus) {
    setStatusBusyId(cma.id);
    setError(null);
    try {
      const updated = await api.updateCma(cma.id, { status });
      setCmas((list) =>
        (list ?? []).map((c) => (c.id === cma.id ? { ...c, status: updated.status } : c)),
      );
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setStatusBusyId(null);
    }
  }

  const load = useCallback(() => {
    setError(null);
    api
      .listCmas()
      .then(setCmas)
      .catch((e: ApiError) => setError(e.message));
  }, []);

  useEffect(load, [load]);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const cma = await api.createCma("Untitled CMA");
      router.push(`/cma/${cma.id}/subject`);
    } catch (e) {
      setError((e as ApiError).message);
      setCreating(false);
    }
  }

  const visible = (cmas ?? []).filter((c) => showArchived || c.status !== "archived");
  const archivedCount = (cmas ?? []).filter((c) => c.status === "archived").length;
  const counts = {
    total: cmas?.length ?? 0,
    draft: (cmas ?? []).filter((c) => c.status === "draft").length,
    completed: (cmas ?? []).filter((c) => c.status === "completed").length,
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Your CMA analyses</h1>
          <p className="mt-1 text-sm text-slate-500">
            Comparative market analyses with a fully transparent calculation trail.
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={handleCreate} disabled={creating}>
          {creating ? "Creating…" : "+ Create new CMA"}
        </button>
      </div>

      {cmas && cmas.length > 0 && (
        <dl className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Analyses", value: counts.total },
            { label: "Drafts", value: counts.draft },
            { label: "Completed", value: counts.completed },
            { label: "Archived", value: archivedCount },
          ].map((stat) => (
            <div
              key={stat.label}
              className="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
            >
              <dt className="text-xxs font-semibold uppercase tracking-wide text-slate-500">
                {stat.label}
              </dt>
              <dd className="mt-0.5 text-xl font-bold tabular-nums text-slate-900">
                {stat.value}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {error && <ErrorBox message={error} onRetry={load} />}
      {!cmas && !error && <Spinner label="Loading analyses…" />}

      {cmas && visible.length === 0 && (
        <EmptyState title="No CMA analyses yet">
          <p>
            Create your first CMA (the{" "}
            <a href="/guide" className="text-accent-700 underline-offset-2 hover:underline">
              how-to-use guide
            </a>{" "}
            walks through every step), or seed the demo analysis by running{" "}
            <code className="rounded bg-slate-100 px-1">python -m app.seed</code> in the
            backend.
          </p>
        </EmptyState>
      )}

      {visible.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="data-table">
              <caption>
                {visible.length} analysis(es). Value ranges are analytical estimates from
                each analysis&apos;s latest calculation.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Analysis</th>
                  <th scope="col">Subject property</th>
                  <th scope="col">Status</th>
                  <th scope="col" className="num">Comparables</th>
                  <th scope="col" className="num">Estimated value range</th>
                  <th scope="col">Last updated</th>
                  <th scope="col"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {visible.map((cma) => (
                  <tr key={cma.id} className="hover:bg-slate-50">
                    <td>
                      <a
                        href={`/cma/${cma.id}/subject`}
                        className="font-medium text-accent-700 underline-offset-2 hover:underline"
                      >
                        {cma.title}
                      </a>
                    </td>
                    <td>{cma.subject_address ?? <span className="text-slate-400">Not entered</span>}</td>
                    <td>
                      <Badge tone={STATUS_TONE[cma.status]}>{cma.status}</Badge>
                    </td>
                    <td className="num">
                      {cma.included_count}/{cma.comparable_count}
                    </td>
                    <td className="num">
                      {cma.latest_valuation?.central_estimate ? (
                        <>
                          <span className="font-medium">
                            {money(cma.latest_valuation.central_estimate)}
                          </span>
                          <span className="block text-xs text-slate-500">
                            {money(cma.latest_valuation.low_estimate)} –{" "}
                            {money(cma.latest_valuation.high_estimate)}
                          </span>
                        </>
                      ) : (
                        <span className="text-slate-400">Not calculated</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap text-slate-500">{dateTime(cma.updated_at)}</td>
                    <td className="whitespace-nowrap">
                      <span className="inline-flex items-center gap-2">
                        {STATUS_ACTIONS[cma.status].map((action) => (
                          <button
                            key={action.to + action.label}
                            type="button"
                            className="cursor-pointer text-xs text-accent-700 underline-offset-2 hover:underline disabled:text-slate-400"
                            disabled={statusBusyId === cma.id}
                            onClick={() => changeStatus(cma, action.to)}
                          >
                            {action.label}
                            <span className="sr-only"> {cma.title}</span>
                          </button>
                        ))}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {archivedCount > 0 && (
            <button
              type="button"
              className="btn-ghost mt-3"
              onClick={() => setShowArchived((v) => !v)}
            >
              {showArchived ? "Hide" : "Show"} {archivedCount} archived
            </button>
          )}
        </Card>
      )}
    </div>
  );
}
