import { expect, test } from "@playwright/test";

import { chatStreamFixture, overviewFixture, runFixture } from "../fixtures/console";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/metrics/overview", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(overviewFixture),
    });
  });

  await page.route("**/api/metrics/runs/run-risky", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(runFixture),
    });
  });

  await page.route("**/api/chat/stream?run_id=run-risky", async (route) => {
    await route.fulfill({
      contentType: "text/event-stream",
      body: chatStreamFixture,
    });
  });
});

test("renders the console shell with a selected run", async ({ page }) => {
  await page.goto("/?run_id=run-risky&view=timeline");

  await expect(page.getByText("Mirage Console")).toBeVisible();
  await expect(page.getByText("run-risky")).toBeVisible();
  await expect(page.getByText("Submit Bid")).toBeVisible();
  await expect(page.getByRole("button", { name: /suppress/i })).not.toBeVisible();
});
