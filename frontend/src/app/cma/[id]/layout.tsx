"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { CMADetail } from "@/lib/types";
import { Badge, ErrorBox, Spinner } from "@/components/ui";
import { CmaContext } from "./cma-context";

const STEPS = [
  { slug: "subject", label: "Subject" },
  { slug: "comparables", label: "Comparables" },
  { slug: "adjustments", label: "Adjustments" },
  { slug: "valuation", label: "Valuation" },
  { slug: "strategies", label: "Strategies" },
  { slug: "report", label: "Report" },
  { slug: "audit", label: "Audit trail" },
];

const STATUS_TONE = { draft: "amber", completed: "green", archived: "slate" } as const;

// A step shows a check once the summary data proves it has produced something.
// Adjustments completion is ambiguous from the summary, so it stays neutral.
function isStepDone(slug: string, cma: CMADetail): boolean {
  switch (slug) {
    case "subject":
      return cma.subject != null;
    case "comparables":
      return cma.comparable_count > 0;
    case "valuation":
      return cma.latest_valuation?.central_estimate != null;
    case "strategies":
      return cma.strategy_count > 0;
    case "report":
      return cma.report_count > 0;
    default:
      return false;
  }
}

export default function CmaLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const cmaId = Number(params.id);
  const [cma, setCma] = useState<CMADetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    setError(null);
    api
      .getCma(cmaId)
      .then(setCma)
      .catch((e: ApiError) => setError(e.message));
  }, [cmaId]);

  useEffect(reload, [reload]);

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!cma) return <Spinner label="Loading analysis…" />;

  const activeStep = STEPS.find((s) => pathname.includes(`/${s.slug}`))?.slug;

  return (
    <CmaContext.Provider value={{ cma, reload }}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-slate-900">{cma.title}</h1>
          <Badge tone={STATUS_TONE[cma.status]}>{cma.status}</Badge>
        </div>
        {cma.latest_valuation?.central_estimate != null && (
          <p className="text-sm text-slate-600">
            Central estimate:{" "}
            <span className="font-semibold tabular-nums">
              {cma.latest_valuation.central_estimate.toLocaleString("en-US", {
                style: "currency",
                currency: "USD",
                maximumFractionDigits: 0,
              })}
            </span>
          </p>
        )}
      </div>

      <nav aria-label="CMA workflow steps" className="mb-6 overflow-x-auto">
        <ol className="flex min-w-max gap-1 border-b border-slate-200">
          {STEPS.map((step, index) => {
            const active = step.slug === activeStep;
            const done = isStepDone(step.slug, cma);
            return (
              <li key={step.slug}>
                <Link
                  href={`/cma/${cmaId}/${step.slug}`}
                  aria-current={active ? "step" : undefined}
                  className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "border-accent-700 text-accent-800"
                      : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800"
                  }`}
                >
                  {done && !active ? (
                    <span
                      aria-hidden="true"
                      className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"
                    >
                      <svg viewBox="0 0 12 12" className="h-2.5 w-2.5" fill="none"
                        stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
                        strokeLinejoin="round">
                        <path d="M2 6.5L4.5 9 10 3.5" />
                      </svg>
                    </span>
                  ) : (
                    <span
                      aria-hidden="true"
                      className={`flex h-4 w-4 items-center justify-center rounded-full text-xxs font-semibold ${
                        active ? "bg-accent-700 text-white" : "bg-slate-200 text-slate-600"
                      }`}
                    >
                      {index + 1}
                    </span>
                  )}
                  {step.label}
                  {done && <span className="sr-only">(has data)</span>}
                </Link>
              </li>
            );
          })}
        </ol>
      </nav>

      {children}
    </CmaContext.Provider>
  );
}
