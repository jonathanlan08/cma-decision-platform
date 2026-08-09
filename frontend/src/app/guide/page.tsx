import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How to use — CMA Decision Platform",
  description:
    "Step-by-step guide to building a transparent comparative market analysis: subject, comparables, adjustments, valuation, strategies, and the audit trail.",
};

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-20">
      <h2
        id={`${id}-h`}
        className="mb-3 border-b-2 border-accent-700 pb-1 text-lg font-bold text-slate-900"
      >
        {title}
      </h2>
      <div className="space-y-3 text-sm leading-6 text-slate-700">{children}</div>
    </section>
  );
}

function Term({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <dt className="text-sm font-semibold text-slate-900">{name}</dt>
      <dd className="mt-1 text-sm text-slate-600">{children}</dd>
    </div>
  );
}

const STEPS = [
  {
    title: "1 · Subject property",
    body: "Describe the home being valued. Only the address is required, but every field you add unlocks more of the analysis: coordinates enable real distances, square footage enables size scoring and $/sq ft, condition enables condition comparisons. Missing data is simply skipped — the tool never guesses.",
    tip: "Agent notes are private working notes; they never appear in the seller report.",
  },
  {
    title: "2 · Comparables",
    body: "Add recently sold, similar properties — upload a CSV (download the template from this screen) or type them in. Rows with problems are rejected individually with a message telling you the row and field; the rest import normally. Then press “Recalculate similarity”: every comp gets a 0–100 score, and clicking the score shows exactly how it was built, component by component.",
    tip: "Exclude weak comps rather than deleting them, and write a reason — the exclusion and reason go into the audit trail, which is exactly what you want to show a skeptical seller.",
  },
  {
    title: "3 · Adjustments",
    body: "The tool suggests dollar adjustments for measurable differences (size, time since sale, condition, pool…) using the assumption values shown at the top of the screen. The direction rule is the standard one: if the comp is worse than your subject, its price adjusts up; if it's better, down. Every suggested amount shows its arithmetic.",
    tip: "The default assumptions are demonstration samples. Set them from your market knowledge before relying on the result — that's the single most important step in the whole workflow.",
  },
  {
    title: "4 · Valuation",
    body: "Included comps are blended into a central estimate — each one weighted by its similarity score times your optional per-comp multiplier — plus a low–high range based on how much the adjusted values disagree. The influence table shows exactly what percentage of the answer came from each comp, and the sensitivity panel shows which assumptions actually move the number.",
    tip: "Read the warnings. “Only 2 comps”, “large adjustments”, or “possible outlier” are the tool telling you where the analysis is thin.",
  },
  {
    title: "5 · Strategies",
    body: "Three list-price scenarios — below market, at market, above market — with qualitative buyer-interest and price-reduction-risk labels derived from documented thresholds. Edit any price to model your own scenario; the labels update instantly.",
    tip: "These are conversation aids, not predictions. The platform deliberately makes no days-on-market or sale-probability claims.",
  },
  {
    title: "6 · Report",
    body: "Generates the seller-facing document: subject summary, methodology explanation, comparable sales, the full adjustment grids, reconciliation, strategy comparison, assumptions, and the limitations disclaimer. It opens print-ready — use your browser's Print → Save as PDF.",
    tip: "Each report records which methodology version produced it, so an old report can always be traced.",
  },
  {
    title: "7 · Audit trail",
    body: "A plain-language, append-only log of every action that could change a number: imports, inclusion decisions, weight and assumption changes, edits, overrides, recalculations, reports. When a seller asks “where did this number come from?”, this screen is the answer.",
    tip: null,
  },
];

export default function GuidePage() {
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-bold text-slate-900">How to use this platform</h1>
      <p className="mt-2 text-sm text-slate-600">
        A comparative market analysis (CMA) is the argument behind a list price:
        similar sold homes, adjusted for their differences, reconciled into a range.
        This tool makes every step of that argument visible and editable. It is an
        educational, open-source project — not an appraisal — and every default
        number in it is a sample assumption you are expected to review.
      </p>

      <nav aria-label="Guide sections" className="my-5 rounded-lg border border-slate-200 bg-white p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          On this page
        </p>
        <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
          {[
            ["workflow", "The workflow"],
            ["csv", "Preparing your CSV"],
            ["numbers", "Understanding the numbers"],
            ["faq", "FAQ"],
            ["data-rules", "Data rules"],
          ].map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="text-accent-700 underline-offset-2 hover:underline">
                {label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div className="space-y-8">
        <Section id="workflow" title="The workflow, step by step">
          <p>
            Start on the dashboard with <strong>Create new CMA</strong>, then work
            left to right through the steps. Green checks show which steps already
            contain data — you can revisit any step at any time.
          </p>
          <ol className="space-y-4">
            {STEPS.map((step) => (
              <li key={step.title} className="rounded-lg border border-slate-200 bg-white p-4">
                <h3 className="text-sm font-bold text-slate-900">{step.title}</h3>
                <p className="mt-1">{step.body}</p>
                {step.tip && (
                  <p className="mt-2 rounded bg-accent-50 px-3 py-2 text-xs text-accent-800">
                    <strong>Tip:</strong> {step.tip}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </Section>

        <Section id="csv" title="Preparing your CSV">
          <p>
            Download the template from the comparables screen (or{" "}
            <a
              href={`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/api/csv-template`}
              className="text-accent-700 underline-offset-2 hover:underline"
            >
              directly here
            </a>
            ). Six columns are required:
          </p>
          <p>
            <code className="rounded bg-slate-100 px-1">address</code>,{" "}
            <code className="rounded bg-slate-100 px-1">sale_price</code>,{" "}
            <code className="rounded bg-slate-100 px-1">sale_date</code> (YYYY-MM-DD),{" "}
            <code className="rounded bg-slate-100 px-1">square_feet</code>,{" "}
            <code className="rounded bg-slate-100 px-1">bedrooms</code>,{" "}
            <code className="rounded bg-slate-100 px-1">bathrooms</code>
          </p>
          <p>
            Everything else — city, ZIP, latitude/longitude, lot size, year built,
            condition (poor/fair/average/good/excellent), parking, pool (true/false),
            distance, notes, source — is optional and simply enriches the analysis.
            Dollar signs and commas in prices are fine. If some rows fail, the valid
            ones still import and you get a per-row list of what to fix.
          </p>
        </Section>

        <Section id="numbers" title="Understanding the numbers">
          <dl className="grid gap-3 sm:grid-cols-2">
            <Term name="Similarity score (0–100)">
              A weighted blend of nine comparisons — distance, size, type, sale
              recency, beds, baths, lot, age, condition. Click any score to see each
              component&apos;s inputs, weight, and contribution. Weights are settings you
              can change per analysis.
            </Term>
            <Term name="Adjustment">
              A dollar correction for one measurable difference between a comp and
              your subject. Positive = comp adjusted upward (it was inferior).
              Suggested rows show their arithmetic; anything you edit is re-flagged
              as your manual override.
            </Term>
            <Term name="Adjusted value">
              The comp&apos;s sale price plus all its adjustments — an estimate of what
              that comp would have sold for if it were your subject.
            </Term>
            <Term name="Influence %">
              How much each included comp contributed to the central estimate:
              similarity × your multiplier, normalized so all influences sum to 100%.
            </Term>
            <Term name="Central estimate & range">
              The weighted average of adjusted values, with a band of ± k standard
              deviations (k is the “range width” setting). It is an analytical
              estimate — not a statistical confidence interval, and not an appraisal.
            </Term>
            <Term name="Sensitivity">
              What happens to the central estimate when each assumption moves ±20%.
              Wide bars = the result leans on that assumption; verify those first.
            </Term>
          </dl>
        </Section>

        <Section id="faq" title="FAQ">
          <dl className="space-y-3">
            <Term name="Why is my range so wide?">
              The range reflects how much your adjusted comps disagree. Wide usually
              means comps that aren&apos;t truly similar, or adjustments that don&apos;t
              capture a real difference. Check the warnings and the outliers, and
              consider excluding the weakest comps.
            </Term>
            <Term name="Can I trust the suggested adjustment amounts?">
              They are computed honestly from the assumption values on the
              adjustments screen — but those defaults are demonstration samples.
              Replace them with values from your market before presenting anything.
            </Term>
            <Term name="A comp seems wrong — delete or exclude?">
              Exclude, with a reason. Deletion removes the record; exclusion keeps
              it visible and documents your judgment in the audit trail.
            </Term>
            <Term name="Where does the data come from?">
              Only from you: manual entry or your CSV upload. The platform never
              scrapes listing sites, and the bundled demo data is entirely
              synthetic.
            </Term>
            <Term name="Can I use real MLS data?">
              If you hold the license for it, yes — export it yourself and upload
              the CSV. Your data stays in your local database. Never commit real
              records to the public repository.
            </Term>
          </dl>
        </Section>

        <Section id="data-rules" title="Data rules & disclaimer">
          <p>
            This is an educational, open-source project. Its outputs are
            informational analytical estimates built from your inputs and
            user-reviewed assumptions — not appraisals, and not a substitute for a
            qualified professional&apos;s judgment. Do not upload confidential client
            records or data you are not licensed to use, and review every number
            before it reaches a client.
          </p>
          <p>
            <Link href="/" className="text-accent-700 underline-offset-2 hover:underline">
              ← Back to the dashboard
            </Link>
          </p>
        </Section>
      </div>
    </div>
  );
}
