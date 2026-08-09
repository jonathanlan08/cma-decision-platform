import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CMA Decision Platform",
  description:
    "Transparent comparative market analysis and listing strategy for residential agents. Educational demo — not an appraisal tool.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:shadow"
        >
          Skip to main content
        </a>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="flex items-baseline gap-2 no-underline">
              <span className="text-lg font-bold tracking-tight text-slate-900">
                CMA <span className="text-accent-700">Decision Platform</span>
              </span>
            </Link>
            <span className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xxs font-medium text-amber-800">
              Educational demo — not an appraisal
            </span>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white">
          <p className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
            Estimates are informational, produced from user-reviewed assumptions, and
            should be reviewed with a qualified real-estate professional. Open-source
            educational project; all demo data is synthetic.
          </p>
        </footer>
      </body>
    </html>
  );
}
