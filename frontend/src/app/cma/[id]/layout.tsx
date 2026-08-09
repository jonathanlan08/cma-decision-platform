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
            return (
              <li key={step.slug}>
                <Link
                  href={`/cma/${cmaId}/${step.slug}`}
                  aria-current={active ? "step" : undefined}
                  className={`inline-block border-b-2 px-3 py-2 text-sm font-medium ${
                    active
                      ? "border-accent-700 text-accent-800"
                      : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800"
                  }`}
                >
                  <span className="mr-1 text-xs text-slate-400">{index + 1}</span>
                  {step.label}
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
