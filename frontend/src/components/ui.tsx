"use client";

// Small shared primitives: status/feedback states and form fields.

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-sm text-slate-500">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-accent-700"
      />
      {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="my-4 flex items-start justify-between gap-4 rounded-md border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <p>
        <span className="font-semibold">Error: </span>
        {message}
      </p>
      {onRetry && (
        <button type="button" className="btn-secondary shrink-0" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function WarningBox({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-2 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span>{children}</span>
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="my-8 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
      <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      {children && <div className="mx-auto mt-2 max-w-md text-sm text-slate-500">{children}</div>}
    </div>
  );
}

export function Card({
  title,
  actions,
  children,
  className = "",
}: {
  title?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
          {title && <h2 className="text-sm font-semibold text-slate-800">{title}</h2>}
          {actions}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Badge({
  tone,
  children,
}: {
  tone: "green" | "amber" | "red" | "slate" | "blue";
  children: React.ReactNode;
}) {
  const tones = {
    green: "bg-emerald-50 text-emerald-800 border-emerald-300",
    amber: "bg-amber-50 text-amber-800 border-amber-300",
    red: "bg-red-50 text-red-800 border-red-300",
    slate: "bg-slate-100 text-slate-700 border-slate-300",
    blue: "bg-accent-50 text-accent-800 border-accent-100",
  } as const;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xxs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function levelTone(level: string): "green" | "amber" | "red" | "slate" {
  if (level === "High") return "green";
  if (level === "Moderate") return "amber";
  if (level === "Low") return "red";
  return "slate";
}

export function riskTone(level: string): "green" | "amber" | "red" | "slate" {
  if (level === "Low") return "green";
  if (level === "Moderate") return "amber";
  if (level === "High") return "red";
  return "slate";
}

interface FieldProps {
  id: string;
  label: string;
  error?: string;
  required?: boolean;
  hint?: string;
  children: React.ReactNode;
}

export function Field({ id, label, error, required, hint, children }: FieldProps) {
  return (
    <div>
      <label htmlFor={id} className="field-label">
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-red-600">
            *
          </span>
        )}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1 text-xs font-medium text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
