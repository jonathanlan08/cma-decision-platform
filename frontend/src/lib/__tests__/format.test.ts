import { describe, expect, it } from "vitest";
import { money, pct, shortDate, titleCase } from "../format";

describe("shortDate", () => {
  it("renders date-only strings in local time (no UTC day shift)", () => {
    // Regression: new Date("2026-06-15") is UTC midnight and rendered
    // "Jun 14" in timezones west of Greenwich.
    expect(shortDate("2026-06-15")).toBe("Jun 15, 2026");
    expect(shortDate("2026-01-01")).toBe("Jan 1, 2026");
    expect(shortDate("2026-12-31")).toBe("Dec 31, 2026");
  });

  it("handles null and garbage", () => {
    expect(shortDate(null)).toBe("—");
    expect(shortDate(undefined)).toBe("—");
    expect(shortDate("not-a-date")).toBe("not-a-date");
  });
});

describe("money / pct / titleCase", () => {
  it("formats money without cents", () => {
    expect(money(1235049)).toBe("$1,235,049");
    expect(money(null)).toBe("—");
  });
  it("formats signed percentages", () => {
    expect(pct(0.05)).toBe("+5.0%");
    expect(pct(-0.032)).toBe("-3.2%");
  });
  it("title-cases snake_case", () => {
    expect(titleCase("living_area")).toBe("Living Area");
  });
});
