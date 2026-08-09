import Link from "next/link";
import type { CMADetail } from "@/lib/types";
import { WarningBox } from "./ui";

// Shown wherever derived numbers appear once the CMA's inputs have changed
// after the last valuation. The backend also refuses to generate a report in
// this state, so this banner is the early, visible version of that gate.
export function StaleBanner({ cma }: { cma: CMADetail }) {
  if (!cma.latest_valuation?.stale) return null;
  return (
    <WarningBox>
      Inputs have changed since the last valuation was calculated, so the numbers
      shown may be outdated.{" "}
      <Link href={`/cma/${cma.id}/valuation`} className="font-medium underline">
        Recalculate the valuation
      </Link>{" "}
      (and refresh strategies) before generating a report.
    </WarningBox>
  );
}
