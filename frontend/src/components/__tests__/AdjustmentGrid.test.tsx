import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AdjustmentGrid } from "../AdjustmentGrid";
import { makeAdjustment, makeComparable } from "./fixtures";

const handlers = () => ({
  onEditAmount: vi.fn(),
  onDeleteAdjustment: vi.fn(),
  onAddManual: vi.fn(),
});

describe("AdjustmentGrid", () => {
  it("shows the full adjustment audit columns", () => {
    const adjustment = makeAdjustment();
    render(
      <AdjustmentGrid
        comparable={makeComparable({ adjustments: [adjustment], adjusted_price: 1330000 })}
        {...handlers()}
      />,
    );
    expect(screen.getByText("Living Area")).toBeInTheDocument();
    expect(screen.getByText("300 sq ft × $150/sq ft")).toBeInTheDocument();
    expect(screen.getByText(/upward/)).toBeInTheDocument();
    expect(screen.getByText("suggested")).toBeInTheDocument();
    expect(screen.getByText("$1,330,000")).toBeInTheDocument();
  });

  it("commits an edited amount on blur", async () => {
    const user = userEvent.setup();
    const h = handlers();
    const adjustment = makeAdjustment();
    render(
      <AdjustmentGrid
        comparable={makeComparable({ adjustments: [adjustment] })}
        {...h}
      />,
    );

    const input = screen.getByLabelText(/living area adjustment amount/i);
    await user.clear(input);
    await user.type(input, "50000");
    await user.tab();

    expect(h.onEditAmount).toHaveBeenCalledWith(adjustment, 50000);
  });

  it("does not fire when the amount is unchanged", async () => {
    const user = userEvent.setup();
    const h = handlers();
    render(
      <AdjustmentGrid
        comparable={makeComparable({ adjustments: [makeAdjustment()] })}
        {...h}
      />,
    );
    await user.click(screen.getByLabelText(/living area adjustment amount/i));
    await user.tab();
    expect(h.onEditAmount).not.toHaveBeenCalled();
  });

  it("validates the manual adjustment form", async () => {
    const user = userEvent.setup();
    const h = handlers();
    render(<AdjustmentGrid comparable={makeComparable()} {...h} />);

    await user.click(screen.getByRole("button", { name: /^add$/i }));
    expect(h.onAddManual).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/category is required/i);

    await user.type(screen.getByLabelText(/add manual adjustment/i), "view");
    await user.type(screen.getByLabelText(/amount/i), "-10000");
    await user.type(screen.getByLabelText(/explanation/i), "Backs to busy street");
    await user.click(screen.getByRole("button", { name: /^add$/i }));

    expect(h.onAddManual).toHaveBeenCalledWith({
      category: "view",
      amount: -10000,
      explanation: "Backs to busy street",
    });
  });

  it("deletes an adjustment", async () => {
    const user = userEvent.setup();
    const h = handlers();
    const adjustment = makeAdjustment();
    render(
      <AdjustmentGrid
        comparable={makeComparable({ adjustments: [adjustment] })}
        {...h}
      />,
    );
    await user.click(screen.getByRole("button", { name: /delete/i }));
    expect(h.onDeleteAdjustment).toHaveBeenCalledWith(adjustment);
  });
});
