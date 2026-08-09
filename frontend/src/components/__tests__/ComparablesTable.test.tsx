import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ComparablesTable } from "../ComparablesTable";
import { makeComparable } from "./fixtures";

const handlers = () => ({
  onToggleInclude: vi.fn(),
  onExclusionReason: vi.fn(),
  onMultiplierChange: vi.fn(),
  onDelete: vi.fn(),
});

describe("ComparablesTable", () => {
  it("toggles inclusion via the row checkbox", async () => {
    const user = userEvent.setup();
    const h = handlers();
    const comp = makeComparable();
    render(<ComparablesTable comparables={[comp]} {...h} />);

    const checkbox = screen.getByRole("checkbox", {
      name: /include 1210 demo oak ave/i,
    });
    expect(checkbox).toBeChecked();
    await user.click(checkbox);

    expect(h.onToggleInclude).toHaveBeenCalledWith(comp, false);
  });

  it("shows an exclusion-reason input only for excluded rows", () => {
    const h = handlers();
    const excluded = makeComparable({
      id: 2,
      address: "3675 Demo Rosemead Blvd",
      selection: {
        included: false,
        similarity_score: 40,
        similarity_breakdown: null,
        user_weight_multiplier: 1,
        exclusion_reason: null,
      },
    });
    render(<ComparablesTable comparables={[makeComparable(), excluded]} {...h} />);

    expect(
      screen.getByLabelText(/reason for excluding 3675 demo rosemead blvd/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText(/reason for excluding 1210 demo oak ave/i),
    ).not.toBeInTheDocument();
  });

  it("saves the weight multiplier on blur", async () => {
    const user = userEvent.setup();
    const h = handlers();
    const comp = makeComparable();
    render(<ComparablesTable comparables={[comp]} {...h} />);

    const input = screen.getByLabelText(/weight multiplier for 1210 demo oak ave/i);
    await user.clear(input);
    await user.type(input, "2.5");
    await user.tab();

    expect(h.onMultiplierChange).toHaveBeenCalledWith(comp, 2.5);
  });

  it("filters rows by address", async () => {
    const user = userEvent.setup();
    const h = handlers();
    render(
      <ComparablesTable
        comparables={[
          makeComparable(),
          makeComparable({ id: 2, address: "987 Fictional Elm St", city: "Temple City" }),
        ]}
        {...h}
      />,
    );

    await user.type(screen.getByLabelText(/filter comparables/i), "elm");
    // Address text also appears in the delete button's screen-reader label.
    expect(screen.getAllByText("987 Fictional Elm St").length).toBeGreaterThan(0);
    expect(screen.queryAllByText("1210 Demo Oak Ave")).toHaveLength(0);
  });

  it("hides excluded rows when 'Included only' is checked", async () => {
    const user = userEvent.setup();
    const h = handlers();
    const excluded = makeComparable({
      id: 2,
      address: "Excluded House",
      selection: {
        included: false,
        similarity_score: null,
        similarity_breakdown: null,
        user_weight_multiplier: 1,
        exclusion_reason: null,
      },
    });
    render(<ComparablesTable comparables={[makeComparable(), excluded]} {...h} />);

    await user.click(screen.getByRole("checkbox", { name: /included only/i }));
    expect(screen.queryByText("Excluded House")).not.toBeInTheDocument();
  });
});
