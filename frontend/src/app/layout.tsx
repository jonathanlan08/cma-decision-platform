import type { Metadata } from "next";
import Link from "next/link";
import localFont from "next/font/local";
import "./globals.css";

// Self-hosted variable font (latin subset) so clean-clone builds stay offline.
const plexSans = localFont({
  src: "../fonts/ibm-plex-sans-latin-var.woff2",
  display: "swap",
  weight: "100 700",
  variable: "--font-plex-sans",
});

export const metadata: Metadata = {
  title: "CMA Decision Platform",
  description:
    "Transparent comparative market analysis and listing strategy for residential agents. Educational demo — not an appraisal tool.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={plexSans.variable}>
      <body className="flex min-h-screen flex-col font-sans">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:shadow"
        >
          Skip to main content
        </a>
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="group flex items-center gap-2.5 no-underline">
              <svg
                aria-hidden="true"
                viewBox="0 0 24 24"
                className="h-7 w-7 rounded-md bg-accent-700 p-1 text-white transition-colors group-hover:bg-accent-800"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {/* house outline over a rising bar baseline */}
                <path d="M4 20h16" />
                <path d="M6 20v-9l6-5 6 5v9" />
                <path d="M10 20v-5h4v5" />
              </svg>
              <span className="text-lg font-bold tracking-tight text-slate-900">
                CMA <span className="text-accent-700">Decision Platform</span>
              </span>
            </Link>
            <div className="flex items-center gap-3">
              <Link
                href="/guide"
                className="text-sm font-medium text-slate-600 underline-offset-2 hover:text-accent-700 hover:underline"
              >
                How to use
              </Link>
              <span className="rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xxs font-medium text-amber-800">
                Educational demo — not an appraisal
              </span>
            </div>
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
