import { expect, test } from "@playwright/test";
import path from "path";

const SAMPLE_CSV = path.resolve(
  __dirname,
  "../../data/sample/comparables_sample.csv",
);

// The complete agent workflow: new CMA -> subject -> CSV import -> similarity
// -> adjustments -> valuation -> strategies -> report -> audit trail.
test("full CMA workflow with the bundled synthetic sample", async ({ page }) => {
  // 1. Start a new CMA from the dashboard
  await page.goto("/");
  await page.getByRole("button", { name: /create new cma/i }).click();
  await expect(page).toHaveURL(/\/cma\/\d+\/subject/);

  // 2. Enter the subject property
  await page.getByLabel(/street address/i).fill("777 E2E Test Lane");
  await page.getByLabel(/^city$/i).fill("Arcadia");
  await page.getByLabel(/bedrooms/i).fill("3");
  await page.getByLabel(/bathrooms/i).fill("2");
  await page.getByLabel(/living area/i).fill("1850");
  await page.getByLabel(/lot size/i).fill("7200");
  await page.getByLabel(/year built/i).fill("1958");
  await page.getByLabel(/condition/i).selectOption("good");
  await page.getByLabel(/latitude/i).fill("34.1340");
  await page.getByLabel(/longitude/i).fill("-118.0390");
  await page.getByRole("button", { name: /save subject property/i }).click();
  await expect(page).toHaveURL(/\/comparables/);

  // 3. Upload the provided sample CSV
  await page.locator("#csv-file").setInputFiles(SAMPLE_CSV);
  await expect(page.getByRole("status")).toContainText("Imported 20 comparable(s)", {
    timeout: 20_000,
  });

  // 4. Score similarity and exclude one comparable
  await page.getByRole("button", { name: /recalculate similarity/i }).click();
  const distantRow = page.getByRole("row", { name: /3675 Demo Rosemead Blvd/i });
  await expect(distantRow).toBeVisible();
  // Controlled checkbox: state flips only after the API round-trip, so click
  // and wait rather than uncheck() (which asserts an immediate flip).
  const includeBox = distantRow.getByRole("checkbox", {
    name: /include 3675 demo rosemead blvd/i,
  });
  await includeBox.click();
  await expect(includeBox).not.toBeChecked();
  await distantRow
    .getByLabel(/reason for excluding/i)
    .fill("Too far from the subject");
  await distantRow.getByLabel(/reason for excluding/i).blur();

  // 5. Generate and modify adjustments
  await page.getByRole("link", { name: /next: adjustments/i }).click();
  await page.getByRole("button", { name: /generate suggested adjustments/i }).click();
  await expect(
    page.getByText("1210 Demo Oak Ave").first(),
  ).toBeVisible({ timeout: 20_000 });
  const firstAmount = page.locator("input[id^='adj-']").first();
  await firstAmount.fill("42000");
  await firstAmount.blur();
  // The edited row is re-flagged as a manual override.
  await expect(page.getByText("manual").first()).toBeVisible();

  // 6. Generate the valuation range
  await page.getByRole("link", { name: /next: valuation/i }).click();
  await page.getByRole("button", { name: /calculate valuation/i }).click();
  await expect(page.getByText(/central estimate/i).first()).toBeVisible();
  await expect(page.getByText(/based on 19 included/i)).toBeVisible({
    timeout: 20_000,
  });

  // 7. Compare listing strategies and tweak a price
  await page.getByRole("link", { name: /next: listing strategies/i }).click();
  await page.getByRole("button", { name: /generate strategies/i }).click();
  await expect(
    page.getByRole("article", { name: /market-entry strategy/i }),
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    page.getByRole("article", { name: /competitive strategy/i }),
  ).toBeVisible();
  const aspirational = page.getByRole("article", { name: /aspirational strategy/i });
  await expect(aspirational).toBeVisible();
  await aspirational.getByLabel(/proposed list price/i).fill("1400000");
  await aspirational.getByLabel(/proposed list price/i).blur();
  await expect(aspirational.getByText(/agent-set price/i)).toBeVisible();

  // 8. Export the report (opens in a new tab)
  await page.getByRole("link", { name: /next: report/i }).click();
  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("button", { name: /generate report/i }).click();
  const report = await popupPromise;
  await report.waitForLoadState();
  await expect(
    report.getByRole("heading", { name: /777 E2E Test Lane/i }),
  ).toBeVisible({ timeout: 20_000 });
  await expect(report.getByText(/not an appraisal/i).first()).toBeVisible();
  await report.close();

  // 9. The audit trail recorded the whole story
  await page.getByRole("link", { name: /audit trail/i }).click();
  await expect(page.getByText(/entered subject property 777 e2e test lane/i)).toBeVisible();
  await expect(page.getByText(/imported 20 comparable/i)).toBeVisible();
  await expect(page.getByText(/too far from the subject/i)).toBeVisible();
  await expect(page.getByText(/recalculated the valuation/i).first()).toBeVisible();
  await expect(page.getByText(/generated the cma report/i).first()).toBeVisible();
});

test("csv row errors are reported without blocking valid rows", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /create new cma/i }).click();
  await page.getByLabel(/street address/i).fill("888 CSV Error Test");
  await page.getByRole("button", { name: /save subject property/i }).click();
  await expect(page).toHaveURL(/\/comparables/);

  const csv =
    "address,sale_price,sale_date,square_feet,bedrooms,bathrooms\n" +
    "1 Ok St,900000,2026-04-01,1500,3,2\n" +
    "2 Bad St,-100,2026-04-01,1500,3,2\n";
  await page.locator("#csv-file").setInputFiles({
    name: "mixed.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await expect(page.getByRole("status")).toContainText("Imported 1 comparable(s)");
  await expect(page.getByRole("status")).toContainText("1 row(s) had errors");
  await expect(page.getByRole("status")).toContainText("sale_price");
});
