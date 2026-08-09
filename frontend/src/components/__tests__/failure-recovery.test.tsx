// Regression tests for the 2026-08 audit fixes: failed saves must not lose
// drafts, invalid weights must not be savable, and stale valuations must be
// visibly flagged.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { CMADetail } from "@/lib/types";
import { AdjustmentGrid } from "../AdjustmentGrid";
import { ComparableForm } from "../ComparableForm";
import { StaleBanner } from "../StaleBanner";
import { WeightsEditor } from "../WeightsEditor";
import { makeComparable } from "./fixtures";

function makeCma(overrides: Partial<CMADetail> = {}): CMADetail {
  return {
    id: 1,
    title: "Test CMA",
    status: "draft",
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
    subject_address: "12345 Demo Lane",
    comparable_count: 3,
    included_count: 3,
    strategy_count: 0,
    report_count: 0,
    latest_valuation: null,
    notes: null,
    subject: null,
    ...overrides,
  };
}

describe("ComparableForm failure recovery", () => {
  it("keeps the draft when the save rejects, clears it on success", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockRejectedValueOnce(new Error("server down"));
    render(<ComparableForm onSave={onSave} />);

    await user.type(screen.getByLabelText(/address/i), "1 Keep Me St");
    await user.type(screen.getByLabelText(/sale price/i), "900000");
    await user.type(screen.getByLabelText(/sale date/i), "2026-04-01");
    await user.type(screen.getByLabelText(/living area/i), "1500");
    await user.type(screen.getByLabelText(/bedrooms/i), "3");
    await user.type(screen.getByLabelText(/bathrooms/i), "2");

    await user.click(screen.getByRole("button", { name: /add comparable/i }));
    expect(onSave).toHaveBeenCalledTimes(1);
    // Failed save: everything the user typed is still there.
    expect(screen.getByLabelText(/address/i)).toHaveValue("1 Keep Me St");

    onSave.mockResolvedValueOnce(undefined);
    await user.click(screen.getByRole("button", { name: /add comparable/i }));
    expect(onSave).toHaveBeenCalledTimes(2);
    // Successful save: the form resets.
    expect(screen.getByLabelText(/address/i)).toHaveValue("");
  });
});

describe("AdjustmentGrid failure recovery", () => {
  it("keeps the manual-adjustment draft when the add rejects", async () => {
    const user = userEvent.setup();
    const onAddManual = vi.fn().mockRejectedValueOnce(new Error("nope"));
    render(
      <AdjustmentGrid
        comparable={makeComparable()}
        onEditAmount={vi.fn()}
        onDeleteAdjustment={vi.fn()}
        onAddManual={onAddManual}
      />,
    );
    await user.type(screen.getByLabelText(/add manual adjustment/i), "view");
    await user.type(screen.getByLabelText(/amount/i), "-10000");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(onAddManual).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText(/add manual adjustment/i)).toHaveValue("view");
    expect(screen.getByLabelText(/amount/i)).toHaveValue(-10000);
  });
});

describe("WeightsEditor validation", () => {
  const config = {
    weights: { proximity: 0.5, living_area: 0.5 },
    similarity_params: {},
    assumptions: {},
    reconciliation: {},
    updated_at: "2026-08-01T00:00:00Z",
    suggestions_outdated: false,
  };

  it("blocks saving when every weight is zero", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<WeightsEditor config={config} onSave={onSave} />);

    for (const name of ["Proximity", "Living Area"]) {
      const input = screen.getByLabelText(name);
      await user.clear(input);
      await user.type(input, "0");
    }
    const save = screen.getByRole("button", { name: /save weights/i });
    expect(save).toBeDisabled();
    expect(screen.getByText(/total must be greater than zero/i)).toBeInTheDocument();
    await user.click(save);
    expect(onSave).not.toHaveBeenCalled();
  });
});

describe("StaleBanner", () => {
  const staleValuation = {
    id: 1, calc_version: "calc-v1.1", created_at: "2026-08-01T00:00:00Z",
    central_estimate: 1_000_000, low_estimate: 950_000, high_estimate: 1_050_000,
    median_adjusted: 1_000_000, weighted_ppsf: 600, dispersion: 50_000, cov: 0.05,
    included_count: 3, effective_count: 3, warnings: [], per_comparable: [],
    stale: true,
  };

  it("warns when the latest valuation is stale", () => {
    render(<StaleBanner cma={makeCma({ latest_valuation: staleValuation })} />);
    expect(screen.getByText(/inputs have changed/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /recalculate the valuation/i }))
      .toHaveAttribute("href", "/cma/1/valuation");
  });

  it("renders nothing when the valuation is current", () => {
    const { container } = render(
      <StaleBanner
        cma={makeCma({ latest_valuation: { ...staleValuation, stale: false } })}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
