import { expect, test } from "@playwright/test";
import { signIn, USERS } from "./support";

// pw-006 — responsive layout: single column, no horizontal scroll on a phone viewport.
test.describe("mobile 375x800", () => {
  test.use({ viewport: { width: 375, height: 800 } });

  test("hospital workspace stacks to one column without horizontal scroll", async ({ page }) => {
    await signIn(page, USERS.hospital);
    await expect(page.getByRole("heading", { name: "Hospital workspace" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    const eligibility = await page.getByRole("region", { name: "Eligibility check" }).boundingBox();
    const preauth = await page.getByRole("region", { name: "New pre-authorization" }).boundingBox();
    expect(eligibility && preauth && preauth.y > eligibility.y + eligibility.height - 1).toBeTruthy();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeVisible();
  });

  test("customer workspace has no horizontal scroll", async ({ page }) => {
    await signIn(page, USERS.customer);
    await expect(page.getByRole("heading", { name: "My coverage" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
});

test("desktop puts the hospital panels side by side", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await signIn(page, USERS.hospital);
  const eligibility = await page.getByRole("region", { name: "Eligibility check" }).boundingBox();
  const preauth = await page.getByRole("region", { name: "New pre-authorization" }).boundingBox();
  expect(eligibility && preauth && Math.abs(preauth.y - eligibility.y) < 5).toBeTruthy();
  // Structural baseline of the static form panels only (the case table holds data and would make it brittle).
  await expect(page.locator(".grid-2").first()).toMatchAriaSnapshot({ name: "hospital-workspace.aria.yml" });
});
