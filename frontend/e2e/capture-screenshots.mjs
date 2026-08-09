// Captures the screenshots referenced by the README from a seeded local stack.
// Usage: node e2e/capture-screenshots.mjs  (backend :8000 + frontend :3000 running,
// demo CMA seeded as id 1)
import { chromium } from "@playwright/test";
import { mkdirSync } from "fs";
import { fileURLToPath } from "url";

const OUT = fileURLToPath(new URL("../../screenshots/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const shots = [
  ["http://localhost:3000/", "dashboard.png"],
  ["http://localhost:3000/cma/1/comparables", "comparables.png"],
  ["http://localhost:3000/cma/1/adjustments", "adjustments.png"],
  ["http://localhost:3000/cma/1/valuation", "valuation.png"],
  ["http://localhost:3000/cma/1/strategies", "strategies.png"],
  ["http://localhost:3000/cma/1/audit", "audit-trail.png"],
];

for (const [url, file] of shots) {
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + file });
  console.log("captured", file);
}

// Report: generate one for the demo CMA, then render the download URL.
const response = await page.request.post("http://localhost:8000/api/cmas/1/report");
const { id: reportId } = await response.json();
await page.goto(`http://localhost:8000/api/reports/${reportId}/download`, {
  waitUntil: "networkidle",
});
await page.screenshot({ path: OUT + "report.png" });
console.log("captured report.png");

await browser.close();
