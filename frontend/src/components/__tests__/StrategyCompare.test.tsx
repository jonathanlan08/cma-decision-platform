import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StrategyCompare } from "../StrategyCompare";
import { makeStrategy } from "./fixtures";

function threeStrategies() {
  return [
    makeStrategy({
      id: 1,
      key: "market_entry",
      name: "Market-Entry",
      list_price: 970000,
      derived: {
        ...makeStrategy().derived,
        pct_vs_value: -0.03,
        dollar_vs_value: -30000,
        buyer_interest: "High",
        price_reduction_risk: "Low",
      },
    }),
    makeStrategy({ id: 2 }),
    makeStrategy({
      id: 3,
      key: "aspirational",
      name: "Aspirational",
      list_price: 1050000,
      derived: {
        ...makeStrategy().derived,
        pct_vs_value: 0.05,
        dollar_vs_value: 50000,
        buyer_interest: "Low",
        price_reduction_risk: "Moderate",
      },
    }),
  ];
}

describe("StrategyCompare", () => {
  it("renders all three scenarios side by side with labels", () => {
    render(
      <StrategyCompare
        strategies={threeStrategies()}
        centralEstimate={1000000}
        onPriceChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("article", { name: /market-entry strategy/i })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: /competitive strategy/i })).toBeInTheDocument();
    expect(screen.getByRole("article", { name: /aspirational strategy/i })).toBeInTheDocument();
    expect(screen.getAllByText(/scenario estimate/i).length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("commits an edited price on blur", async () => {
    const user = userEvent.setup();
    const onPriceChange = vi.fn();
    const strategies = threeStrategies();
    render(
      <StrategyCompare
        strategies={strategies}
        centralEstimate={1000000}
        onPriceChange={onPriceChange}
      />,
    );

    const input = screen.getByLabelText(/proposed list price/i, {
      selector: "#price-3",
    });
    await user.clear(input);
    await user.type(input, "1100000");
    await user.tab();

    expect(onPriceChange).toHaveBeenCalledWith(strategies[2], 1100000);
  });

  it("ignores unchanged or invalid prices", async () => {
    const user = userEvent.setup();
    const onPriceChange = vi.fn();
    render(
      <StrategyCompare
        strategies={threeStrategies()}
        centralEstimate={1000000}
        onPriceChange={onPriceChange}
      />,
    );
    const input = screen.getByLabelText(/proposed list price/i, { selector: "#price-2" });
    await user.click(input);
    await user.tab(); // unchanged
    await user.clear(input); // empty -> invalid
    await user.tab();
    expect(onPriceChange).not.toHaveBeenCalled();
  });

  it("marks agent-set prices", () => {
    render(
      <StrategyCompare
        strategies={[makeStrategy({ is_user_modified: true })]}
        centralEstimate={1000000}
        onPriceChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/agent-set price/i)).toBeInTheDocument();
  });
});
