"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { CMADetail } from "@/lib/types";
import { Badge, ErrorBox, Spinner } from "@/components/ui";
import { CmaContext } from "./cma-context";

// Inline title editor: rename without leaving the workflow.
function TitleEditor({ cma, onRenamed }: { cma: CMADetail; onRenamed: () => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(cma.title);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    const title = draft.trim();
    if (!title || title === cma.title) {
      setEditing(false);
      setDraft(cma.title);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateCma(cma.id, { title });
      setEditing(false);
      onRenamed();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    return (
      <span className="flex items-center gap-2">
        <h1 className="text-lg font-bold text-slate-900">{cma.title}</h1>
        <button
          type="button"
          className="flex min-h-[32px] min-w-[32px] cursor-pointer items-center justify-center rounded text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label={`Rename analysis ${cma.title}`}
          onClick={() => {
            setDraft(cma.title);
            setEditing(true);
          }}
        >
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none" stroke="currentColor"
            strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M11.1 2.2a1.6 1.6 0 0 1 2.3 2.3L5 12.9l-3 .7.7-3z" />
          </svg>
        </button>
      </span>
    );
  }
  return (
    <span className="flex flex-wrap items-center gap-2">
      <label htmlFor="cma-title-editor" className="sr-only">Analysis title</label>
      <input
        id="cma-title-editor"
        type="text"
        className="field-input w-72 max-w-full text-base font-bold"
        value={draft}
        disabled={saving}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            save();
          }
          if (e.key === "Escape") {
            setEditing(false);
            setDraft(cma.title);
          }
        }}
      />
      <button type="button" className="btn-secondary" disabled={saving} onClick={save}>
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        className="btn-ghost"
        disabled={saving}
        onClick={() => {
          setEditing(false);
          setDraft(cma.title);
        }}
      >
        Cancel
      </button>
      {error && (
        <span role="alert" className="w-full text-xs font-medium text-red-700">{error}</span>
      )}
    </span>
  );
}

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
  const activeStepRef = useRef<HTMLLIElement | null>(null);
  const stepScrollerRef = useRef<HTMLDivElement | null>(null);

  const reload = useCallback(() => {
    setError(null);
    api
      .getCma(cmaId)
      .then(setCma)
      .catch((e: ApiError) => setError(e.message));
  }, [cmaId]);

  useEffect(reload, [reload]);

  // On narrow screens the stepper scrolls horizontally; keep the active step
  // in view so later steps are never silently hidden off-screen. Scroll ONLY
  // the stepper's own container: scrollIntoView would also pan scrollable
  // ancestors (the page itself on mobile).
  useEffect(() => {
    const el = activeStepRef.current;
    const scroller = stepScrollerRef.current;
    if (el && scroller && scroller.scrollWidth > scroller.clientWidth) {
      scroller.scrollLeft = Math.max(
        0, el.offsetLeft - (scroller.clientWidth - el.offsetWidth) / 2,
      );
    }
  }, [pathname, cma]);

  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!cma) return <Spinner label="Loading analysis…" />;

  const activeStep = STEPS.find((s) => pathname.includes(`/${s.slug}`))?.slug;

  return (
    <CmaContext.Provider value={{ cma, reload }}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <TitleEditor cma={cma} onRenamed={reload} />
          <Badge tone={STATUS_TONE[cma.status]}>{cma.status}</Badge>
        </div>
        {cma.latest_valuation?.central_estimate != null && (
          <p className="flex items-center gap-2 text-sm text-slate-600">
            Central estimate:{" "}
            <span className="font-semibold tabular-nums">
              {cma.latest_valuation.central_estimate.toLocaleString("en-US", {
                style: "currency",
                currency: "USD",
                maximumFractionDigits: 0,
              })}
            </span>
            {cma.latest_valuation.stale && (
              <Badge tone="amber">outdated: inputs changed</Badge>
            )}
          </p>
        )}
      </div>

      <nav aria-label="CMA workflow steps" className="relative mb-6">
        {/* Fade hints that more steps are reachable by scrolling (mobile). */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-gradient-to-l from-slate-50 to-transparent sm:hidden"
        />
        <div ref={stepScrollerRef} className="overflow-x-auto">
        <ol className="flex min-w-max gap-1 border-b border-slate-200">
          {STEPS.map((step, index) => {
            const active = step.slug === activeStep;
            const done = isStepDone(step.slug, cma);
            return (
              <li key={step.slug} ref={active ? activeStepRef : undefined}>
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
        </div>
      </nav>

      {children}
    </CmaContext.Provider>
  );
}
